"""Source collection and raw staging; no reader publication or delivery."""
from __future__ import annotations
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional
from .models import ContentItem
from .daily_feed import item_identity, local_date_for
from .edition import DEFAULT_STAGING_PATH, load_staging_state, merge_staged_items, save_staging_state
from .run_report import RunReport
from .ai.tokens import reset_usage
import httpx
from .scrapers.github import GitHubScraper
from .scrapers.hackernews import HackerNewsScraper
from .scrapers.rss import RSSScraper
from .scrapers.telegram import TelegramScraper
from .scrapers.google_news import GoogleNewsScraper

@dataclass
class SourceFetchOutcome:
    """Result of fetching one configured source."""
    source_name: str
    status: Literal['success', 'empty', 'failure', 'partial_failure']
    items: List[ContentItem] = field(default_factory=list)
    subsource_counts: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
    channels: List[Dict[str, object]] = field(default_factory=list)
    feeds: List[Dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        result: Dict[str, object] = {'source': self.source_name, 'status': self.status, 'item_count': len(self.items), 'subsource_counts': dict(self.subsource_counts)}
        if self.error is not None:
            result['error'] = self.error
        if self.channels:
            result['channels'] = [dict(row) for row in self.channels]
        if self.feeds:
            result['feeds'] = [dict(row) for row in self.feeds]
        return result

@dataclass
class FetchReport:
    """Aggregate diagnostics for one fetch across configured sources."""
    outcomes: List[SourceFetchOutcome] = field(default_factory=list)

    @property
    def status(self) -> Literal['not_attempted', 'success', 'partial_failure', 'failure']:
        if not self.outcomes:
            return 'not_attempted'
        if self.failed_count == len(self.outcomes):
            return 'failure'
        if self.failed_count or any((outcome.status == 'partial_failure' for outcome in self.outcomes)):
            return 'partial_failure'
        return 'success'

    @property
    def failed_count(self) -> int:
        return sum((outcome.status == 'failure' for outcome in self.outcomes))

    @property
    def all_failed(self) -> bool:
        return bool(self.outcomes) and self.failed_count == len(self.outcomes)

    def failure_message(self) -> str:
        failures = '; '.join((f"{outcome.source_name}: {outcome.error or 'unknown error'}" for outcome in self.outcomes if outcome.status == 'failure'))
        return f'All {len(self.outcomes)} attempted sources failed ({failures})'

    def to_dict(self) -> Dict[str, object]:
        return {'status': self.status, 'attempted': len(self.outcomes), 'successful': len(self.outcomes) - self.failed_count, 'empty': sum((outcome.status == 'empty' for outcome in self.outcomes)), 'failed': self.failed_count, 'item_count': sum((len(outcome.items) for outcome in self.outcomes)), 'sources': [outcome.to_dict() for outcome in self.outcomes]}

class CollectionPipeline:

    async def fetch_to_staging(self, force_hours: int | None=None, *, staging_path: Path=DEFAULT_STAGING_PATH, now: datetime | None=None) -> None:
        """Fetch raw candidates to staging; scoring is a separate background stage."""
        timezone_name = self.config.filtering.daily_timezone
        run_started_at = now or datetime.now(timezone.utc)
        if run_started_at.tzinfo is None:
            run_started_at = run_started_at.replace(tzinfo=timezone.utc)
        run_report = RunReport.start(date=local_date_for(run_started_at, timezone_name), timezone_name=timezone_name, started_at=run_started_at, kind='staging_fetch')
        reset_usage()
        self.last_run_report = run_report
        self.console.print('[bold cyan]📥 xiyu.news - Collecting items for the daily edition...[/bold cyan]\n')
        try:
            await self._stage_sources(run_report, run_started_at, force_hours=force_hours, staging_path=staging_path)
        except Exception as exc:
            run_report.fail(exc)
            self.console.print(f'[bold red]❌ Collection failed: {exc}[/bold red]')
            raise
        finally:
            self._finish_run_report(run_report)

    async def _stage_sources(self, run_report, run_started_at, *, force_hours=None, staging_path=DEFAULT_STAGING_PATH):
        hours = force_hours or self.config.filtering.time_window_hours
        since = run_started_at - timedelta(hours=hours)
        all_items = await self.fetch_all_sources(since)
        run_report.set_metric('fetched_raw', len(all_items))
        run_report.attach_fetch_report(self.last_fetch_report.to_dict() if self.last_fetch_report is not None else None)
        if self.last_fetch_report and self.last_fetch_report.all_failed:
            raise RuntimeError(self.last_fetch_report.failure_message())
        merged_items = self.merge_cross_source_duplicates(all_items)
        run_report.set_metric('unique_after_url_dedup', len(merged_items))
        staging_state = load_staging_state(staging_path)
        existing_identities = {item_identity(item) for item in staging_state.items}
        staged_items = merge_staged_items(staging_state.items, merged_items, now=run_started_at)
        staged_identities = {item_identity(item) for item in staged_items}
        added_identities = staged_identities - existing_identities
        staged_added = len(added_identities)
        run_report.set_metric('staged_added', staged_added)
        run_report.set_metric('staged_total', len(staged_items))
        save_staging_state(staged_items, staging_path, updated_at=run_started_at)
        self.console.print(f'✅ Added {staged_added} new unique items; {len(staged_items)} retained in {staging_path}')
        return staged_items

    def _determine_time_window(self, force_hours: int=None) -> datetime:
        if force_hours:
            since = datetime.now(timezone.utc) - timedelta(hours=force_hours)
        else:
            hours = self.config.filtering.time_window_hours
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
        return since

    async def fetch_all_sources(self, since: datetime) -> List[ContentItem]:
        """Fetch content from all configured sources.

        This is a stable stage entry point for integrations such as MCP.

        Args:
            since: Fetch items published after this time

        Returns:
            List[ContentItem]: All fetched items
        """
        self.last_fetch_report = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            if self.config.sources.github:
                github_scraper = GitHubScraper(self.config.sources.github, client)
                tasks.append(self._fetch_with_progress('GitHub', github_scraper, since))
            if self.config.sources.hackernews.enabled:
                hn_scraper = HackerNewsScraper(self.config.sources.hackernews, client)
                tasks.append(self._fetch_with_progress('Hacker News', hn_scraper, since))
            if self.config.sources.rss:
                from .extractors import ExtractorRegistry
                rss_scraper = RSSScraper(self.config.sources.rss, client, ExtractorRegistry(self.config.extractors))
                tasks.append(self._fetch_with_progress('RSS Feeds', rss_scraper, since))
            if self.config.sources.telegram.enabled:
                telegram_scraper = TelegramScraper(self.config.sources.telegram, client)
                tasks.append(self._fetch_with_progress('Telegram', telegram_scraper, since))
            if self.config.sources.google_news and self.config.sources.google_news.enabled:
                gn_scraper = GoogleNewsScraper(self.config.sources.google_news, client)
                tasks.append(self._fetch_with_progress('Google News', gn_scraper, since))
            outcomes = await asyncio.gather(*tasks)
            self.last_fetch_report = FetchReport(outcomes=list(outcomes))
            all_items: List[ContentItem] = []
            for outcome in outcomes:
                all_items.extend(outcome.items)
            return all_items

    async def _fetch_with_progress(self, name: str, scraper, since: datetime) -> SourceFetchOutcome:
        """Fetch from a scraper with progress indication.

        Args:
            name: Source name for display
            scraper: Scraper instance
            since: Fetch items after this time

        Returns:
            SourceFetchOutcome: Named fetch result and diagnostics
        """
        self.console.print(f'🔍 Fetching from {name}...')
        try:
            items = await scraper.fetch(since)
        except Exception as exc:
            error = f'{type(exc).__name__}: {exc}'
            self.console.print(f'[red]   Failed to fetch {name}: {error}[/red]')
            return SourceFetchOutcome(source_name=name, status='failure', error=error)
        self.console.print(f'   Found {len(items)} items from {name}')
        feed_results = getattr(scraper, 'feed_results', [])
        failed_feeds = [row for row in feed_results if row['status'] in {'failure', 'degraded'}]
        source_status = 'success' if items else 'empty'
        source_error = None
        if failed_feeds:
            source_status = 'failure' if not items and len(failed_feeds) == len(feed_results) else 'partial_failure'
            source_error = '; '.join((f"{row['name']}: {row['error']}" for row in failed_feeds))
        sub_counts: Dict[str, int] = defaultdict(int)
        for item in items:
            sub_counts[self._sub_source_label(item)] += 1
        if len(sub_counts) > 1:
            for sub, count in sorted(sub_counts.items()):
                self.console.print(f'      • {sub}: {count}')
        channels = list(getattr(scraper, 'channel_reports', []) or [])
        for row in channels:
            tag = f"@{row['channel']}{(' [probe]' if row.get('probe') else '')}"
            if row.get('status') == 'ok':
                self.console.print(f"      · {tag}: title={row.get('title')!r} subscribers={row.get('subscribers')} seen={row.get('messages_seen')} in_window={row.get('in_window')} kept={row.get('kept')} pages={row.get('pages', 1)} newest={row.get('newest')}")
            else:
                self.console.print(f"      · {tag}: failed ({row.get('error')})")
        return SourceFetchOutcome(source_name=name, status=source_status, error=source_error, items=items, subsource_counts=dict(sorted(sub_counts.items())), channels=channels, feeds=list(feed_results))
