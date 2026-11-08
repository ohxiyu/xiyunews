"""Content enrichment using AI (second-pass analysis).

For items that pass the score threshold, this module:
1. Searches the web for relevant context (via DuckDuckGo)
2. Feeds search results + item content to AI to generate grounded background knowledge
"""

import asyncio
import re
import sys
import os
import time
from typing import List, Optional
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
from ddgs import DDGS

from .client import AIClient
from .prompts import (
    CONCEPT_EXTRACTION_SYSTEM, CONCEPT_EXTRACTION_USER,
    CONTENT_ENRICHMENT_SYSTEM, CONTENT_ENRICHMENT_USER,
    CORE_ENRICHMENT_SYSTEM, CORE_ENRICHMENT_USER,
)
from .utils import parse_json_response
from .result_cache import ENRICHMENT_PREFIXES
from ..models import ContentItem


class ContentEnricher:
    """Enriches high-scoring content items with background knowledge."""

    def __init__(self, ai_client: AIClient, *, languages=None):
        self.languages = tuple(languages or ("en", "zh"))
        self.client = ai_client
        self._search_tasks: dict[str, asyncio.Task[list]] = {}

    def _get_concurrency(self) -> int:
        """Return the configured enrichment concurrency, clamped to 1 or above."""
        config = getattr(self.client, "config", None)
        concurrency = getattr(config, "enrichment_concurrency", 1)
        return max(concurrency, 1)

    async def enrich_batch(self, items: List[ContentItem]) -> None:
        """Enrich items in-place with background knowledge.

        Args:
            items: Content items to enrich (modified in-place)
        """
        concurrency = self._get_concurrency()
        semaphore = asyncio.Semaphore(concurrency)
        processed_count = 0
        started = time.perf_counter()

        async def _process(item: ContentItem, progress_task) -> None:
            nonlocal processed_count
            async with semaphore:
                self._clear_generated(item)
                try:
                    await self._enrich_item(item)
                    item.metadata["enrichment_status"] = "complete"
                except Exception as exc:
                    cause = exc.last_attempt.exception() if isinstance(exc, RetryError) else exc
                    print(
                        f"Error enriching item {item.id}: {type(cause).__name__}, "
                        "falling back to translation", flush=True,
                    )
                    self._clear_generated(item)
                    await self._translate_item(item)
                    item.metadata["enrichment_status"] = "translation_only"
            processed_count += 1
            if processed_count % 5 == 0 or processed_count == len(items):
                progress.console.print(
                    f"AI enrichment processed: {processed_count}/{len(items)}, "
                    f"elapsed={time.perf_counter() - started:.1f}s"
                )
            progress.advance(progress_task)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Enriching", total=len(items))
            coros = [
                _process(item, task) for item in items
            ]
            await asyncio.gather(*coros)

    @staticmethod
    def _clear_generated(item):
        for key in list(item.metadata):
            if key in {"sources", "editorial_tags", "enrichment_status"} or key.startswith(ENRICHMENT_PREFIXES):
                item.metadata.pop(key, None)

    @staticmethod
    def _source_headline(item, language, proposed):
        """Keep original editorial wording in its source language."""
        is_chinese = bool(re.search(r"[\u3400-\u9fff]", item.title))
        if (language == "zh" and is_chinese) or (language == "en" and not is_chinese):
            return item.title
        return proposed


    async def _web_search(self, query: str, max_results: int = 3) -> list:
        """Search the web for context via DuckDuckGo.

        Returns:
            List of dicts with keys: title, url, body
        """
        try:
            # Suppress primp "Impersonate ... does not exist" stderr warning
            stderr = sys.stderr
            sys.stderr = open(os.devnull, "w")
            try:
                ddgs = DDGS()
                results = await asyncio.to_thread(ddgs.text, query, max_results=max_results)
            finally:
                sys.stderr.close()
                sys.stderr = stderr
        except Exception:
            return []

        return [
            {"title": r.get("title", ""), "url": r.get("href", ""), "body": r.get("body", "")}
            for r in (results or [])
        ]

    async def _cached_web_search(self, query: str, max_results: int = 3) -> list:
        """Share identical searches across stories within the same edition."""
        key = " ".join(query.lower().split())
        task = self._search_tasks.get(key)
        if task is None:
            task = asyncio.create_task(self._web_search(query, max_results))
            self._search_tasks[key] = task
        return await task

    @staticmethod
    def _parse_json_response(response: str) -> Optional[dict]:
        """Try multiple strategies to extract a JSON object from an AI response.

        Returns the parsed dict, or None if all strategies fail.
        """
        return parse_json_response(response)

    async def _extract_concepts(self, item: ContentItem, content_text: str) -> List[str]:
        """Ask AI to identify concepts that need explanation.

        Args:
            item: Content item
            content_text: Extracted content text

        Returns:
            List of search queries for concepts that need explanation
        """
        user_prompt = CONCEPT_EXTRACTION_USER.format(
            title=item.title,
            published_at=item.published_at.isoformat(),
            summary=item.ai_summary or item.title,
            tags=", ".join(item.ai_tags) if item.ai_tags else "",
            content=content_text[:1000],
        )

        try:
            response = await self.client.complete(
                system=CONCEPT_EXTRACTION_SYSTEM,
                user=user_prompt,
            )
            result = self._parse_json_response(response)
            if result is None:
                return []
            queries = result.get("queries", [])
            if not isinstance(queries, list):
                return []
            cleaned = []
            seen = set()
            for query in queries:
                if not isinstance(query, str):
                    continue
                query = " ".join(query.split())[:240]
                if query and query.casefold() not in seen:
                    cleaned.append(query)
                    seen.add(query.casefold())
                if len(cleaned) == 3:
                    break
            return cleaned
        except Exception:
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=10),
    )
    async def _enrich_item(self, item: ContentItem) -> None:
        """Enrich a single item with background knowledge.

        Steps:
        1. Ask AI which concepts in the news need explanation
        2. Search the web for those concepts
        3. Ask AI to generate background based on search results

        Args:
            item: Content item to enrich (modified in-place via metadata)
        """
        self._clear_generated(item)
        # Extract content text and comments separately
        content_text = ""
        comments_text = ""
        if item.content:
            if "--- Top Comments ---" in item.content:
                main, comments_part = item.content.split("--- Top Comments ---", 1)
                content_text = main.strip()[:4000]
                comments_text = comments_part.strip()[:2000]
            else:
                content_text = item.content[:4000]

        # Step 1: AI identifies concepts to explain
        queries = await self._extract_concepts(item, content_text)
        if not queries:
            # Familiar actors or a failed concept response must not silently
            # disable grounding. Reuse the existing search path and limit;
            # this fallback adds no model call or unsupported premise.
            title_query = " ".join(item.title.split())[:200]
            queries = [f"{title_query} background context"]

        # Step 2: Search web for each concept
        all_results = []
        web_sections = []
        search_results = await asyncio.gather(
            *(self._cached_web_search(query) for query in queries)
        )
        for query, results in zip(queries, search_results):
            all_results.extend(results)
            if results:
                lines = [f"- [{r['title']}]({r['url']}): {r['body']}" for r in results]
                web_sections.append(f"**{query}:**\n" + "\n".join(lines))
        web_context = "\n\n".join(web_sections) if web_sections else ""

        # Index of available URLs for citation validation
        available_urls = {r["url"]: r["title"] for r in all_results if r.get("url")}

        # Step 3: AI generates background grounded in search results
        chinese_only = self.languages == ("zh",)
        template = CORE_ENRICHMENT_USER if chinese_only else CONTENT_ENRICHMENT_USER
        user_prompt = template.format(
            title=item.title,
            published_at=item.published_at.isoformat(),
            url=str(item.url),
            summary=item.ai_summary or item.title,
            score=item.ai_score or 0,
            reason=item.ai_reason or "",
            tags=", ".join(item.ai_tags) if item.ai_tags else "",
            content=content_text,
            comments_section=f"\n**Community Comments:**\n{comments_text}" if comments_text else "",
            web_context=web_context or "No web search results available.",
        )

        response = await self.client.complete(
            system=CORE_ENRICHMENT_SYSTEM if chinese_only else CONTENT_ENRICHMENT_SYSTEM,
            user=user_prompt,
        )

        # Parse JSON response with robust fallback
        result = self._parse_json_response(response)
        if result is None:
            # Gracefully degrade: fall back to a lightweight translation
            # instead of dropping the item untranslated.
            print(f"Warning: could not parse enrichment response for {item.id}, falling back to translation")
            raise ValueError("invalid_generation")
        required = tuple(f"whats_new_{lang}" for lang in self.languages)
        translated_title = "title_zh" if chinese_only else ("title_en" if re.search(r"[\u3400-\u9fff]", item.title) else "title_zh")
        if any(not isinstance(result.get(key), str) or not result[key].strip()
               for key in (*required, translated_title)):
            raise ValueError("invalid_generation")

        # Supported context must not disappear from one language. Both empty
        # remains valid when the evidence cannot support useful background.
        backgrounds = [result.get(f"background_{lang}", "") for lang in self.languages]
        if any(not isinstance(value, str) for value in backgrounds):
            raise ValueError("invalid_background")
        if len(backgrounds) == 2 and bool(backgrounds[0].strip()) != bool(backgrounds[1].strip()):
            raise ValueError("incomplete_bilingual_background")
        for lang, value in zip(self.languages, backgrounds):
            result[f"background_{lang}"] = value.strip()
        # A publication timestamp or model memory cannot substantiate a
        # historical year. This narrow evidence check rejects invented years;
        # it neither rewrites them nor certifies the rest of the generated text.
        search_evidence = "\n".join(
            str(result.get(field, ""))
            for result in all_results for field in ("title", "url", "body")
        )
        evidence = "\n".join((item.title, item.ai_summary or "", content_text, search_evidence))
        year_pattern = r"(?<!\d)(?:19|20)\d{2}(?!\d)"
        supported_years = set(re.findall(year_pattern, evidence))
        generated_years = set(re.findall(year_pattern, "\n".join(backgrounds)))
        if generated_years - supported_years:
            raise ValueError("unsupported_background_year")

        if not comments_text:
            result.pop("community_discussion_en", None)
            result.pop("community_discussion_zh", None)

        # Combine structured sub-fields into per-language detailed_summary
        for lang in self.languages:
            if result.get(f"title_{lang}"):
                val = result[f"title_{lang}"]
                item.metadata[f"title_{lang}"] = val.get("text") or str(val) if isinstance(val, dict) else str(val)
            item.metadata[f"title_{lang}"] = self._source_headline(
                item, lang, item.metadata.get(f"title_{lang}"))

            parts = []
            for field in ("whats_new", "why_it_matters", "key_details"):
                text = result.get(f"{field}_{lang}", "").strip()
                if text:
                    parts.append(text)
            if parts:
                # Preserve the model's semantic sections as paragraphs.  The
                # web feed and share-card renderer use these boundaries while
                # older one-line summaries receive a deterministic fallback.
                item.metadata[f"detailed_summary_{lang}"] = "\n\n".join(parts)

            if result.get(f"background_{lang}"):
                val = result[f"background_{lang}"]
                item.metadata[f"background_{lang}"] = val.get("text") or str(val) if isinstance(val, dict) else str(val)

            if result.get(f"community_discussion_{lang}"):
                val = result[f"community_discussion_{lang}"]
                item.metadata[f"community_discussion_{lang}"] = val.get("text") or str(val) if isinstance(val, dict) else str(val)

            if result.get(f"market_impact_{lang}"):
                val = result[f"market_impact_{lang}"]
                item.metadata[f"market_impact_{lang}"] = val.get("text") or str(val) if isinstance(val, dict) else str(val)

        # Store citation sources — only URLs that actually came from our search results
        if result.get("sources") and available_urls:
            valid = [
                {"url": u, "title": available_urls[u]}
                for u in result["sources"]
                if u in available_urls
            ]
            if valid:
                item.metadata["sources"] = valid

        tags = result.get("tags")
        if isinstance(tags, list):
            item.metadata["editorial_tags"] = [tag.strip().lstrip("#") for tag in tags
                                              if isinstance(tag, str) and tag.strip()][:6]
            item.ai_tags = list(item.metadata["editorial_tags"])

        # Backward-compatible fallback fields (English as default)
        item.metadata["detailed_summary"] = item.metadata.get("detailed_summary_en", "")
        item.metadata["background"] = item.metadata.get("background_en", "")
        item.metadata["community_discussion"] = item.metadata.get("community_discussion_en", "")

    async def _translate_item(self, item: ContentItem) -> None:
        """Keep the baseline translation-only fallback when expansion fails."""
        try:
            response = await self.client.complete(
                system="You are a translator. Translate to Simplified Chinese. Return only valid JSON, no other text.",
                user=(
                    f'Title: {item.title}\n'
                    f'Summary: {item.ai_summary or item.title}\n\n'
                    'Return JSON:\n'
                    '{"title_zh": "<中文标题>", "summary_zh": "<用中文写1-2句摘要>"}'
                ),
            )
            result = self._parse_json_response(response)
            if result:
                if result.get("title_zh"):
                    item.metadata["title_zh"] = result["title_zh"]
                if result.get("summary_zh"):
                    item.metadata["detailed_summary_zh"] = result["summary_zh"]
        except Exception:
            pass
