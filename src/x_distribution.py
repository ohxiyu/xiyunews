"""Durable X planning and one-shot delivery, independent of site generation."""
from __future__ import annotations
import json
from datetime import date as date_type, datetime, timezone
from pathlib import Path
from .models import ContentItem
from .daily_feed import item_identity, local_date_for, load_daily_feed_state, load_published_daily_feed_state
from .run_report import RunReport
from .ai.client import create_ai_client
from .ai.tokens import reset_usage



class XDistributionPipeline:
    async def run_x_slot(
        self,
        *,
        edition_date: date_type | None = None,
        kickoff_only: bool = False,
        now: datetime | None = None,
        state_path: Path | None = None,
        queue_dir: Path | None = None,
    ) -> None:
        """Plan today's X posts once, then send at most one that is due.

        Planning and sending are separate steps (see :mod:`src.x_queue`). The
        text of every post is persisted before anything is sent, each request
        is preceded by a ``pending`` checkpoint, and an outcome that cannot be
        proven is recorded as ``unknown`` for a person to resolve instead of
        being retried. Only today's edition is ever posted.

        ``queue_dir`` is a checkout of the ``x-queue`` branch; when given,
        every state change is committed and pushed there (no force), and a
        rejected push stops the run before any request. ``kickoff_only`` is
        kept for compatibility: a post-publication kickoff is an ordinary run.
        """
        from .services.x_delivery import (
            build_story_post,
            compose_story_post,
            post_source_fields,
            unsupported_figures,
        )
        from . import x_queue

        del kickoff_only  # Every run plans, advances and sends the same way.
        config = self.config.x_delivery
        timezone_name = self.config.filtering.daily_timezone
        run_started_at = now or datetime.now(timezone.utc)
        if run_started_at.tzinfo is None:
            run_started_at = run_started_at.replace(tzinfo=timezone.utc)
        today = local_date_for(run_started_at, timezone_name)
        run_report = RunReport.start(
            date=today,
            timezone_name=timezone_name,
            started_at=run_started_at,
            kind="x_slot",
        )
        reset_usage()
        self.last_run_report = run_report
        if queue_dir is not None:
            path = queue_dir / x_queue.QUEUE_RELATIVE_PATH
        else:
            path = state_path or x_queue.DEFAULT_STATE_PATH

        try:
            publisher = getattr(self, "x_publisher", None)
            if not publisher or not config or not config.enabled:
                run_report.add_alert(
                    "info",
                    "x_slot_disabled",
                    "X 分发未启用，本次不发布。",
                )
                self.console.print("[yellow]X delivery is disabled.[/yellow]")
                return
            if config.mode != "drip":
                run_report.add_alert(
                    "info",
                    "x_slot_not_drip",
                    "X 分发处于 digest 模式，分时发布任务不执行。",
                )
                return
            if edition_date is not None and edition_date.isoformat() != today:
                run_report.add_alert(
                    "info",
                    "x_slot_not_today",
                    f"只推送当天日报；{edition_date.isoformat()} 不是今天（{today}）。",
                )

            settings = x_queue.Settings.from_mapping(
                config.model_dump(), timezone_name
            )
            state = x_queue.load(path, run_started_at)
            attention_before = self._x_attention_jobs(state)

            def persist() -> None:
                if queue_dir is not None:
                    x_queue.git_checkpoint(queue_dir, state)
                else:
                    x_queue.save(state, path)

            # Preserve recovered local receipts in the audit branch before
            # normal planning prunes entries beyond the history window.
            if queue_dir is not None and x_queue.needs_checkpoint(path, state):
                persist()
            changed = x_queue.recover_pending(state) > 0
            daily_state = (load_published_daily_feed_state(today, timezone_name)
                           if queue_dir is not None else load_daily_feed_state(today, timezone_name))
            if daily_state.items:
                changed |= await self._plan_x_edition(
                    state,
                    daily_state=daily_state,
                    today=today,
                    now=run_started_at,
                    settings=settings,
                    run_report=run_report,
                    helpers=(
                        build_story_post,
                        compose_story_post,
                        post_source_fields,
                        unsupported_figures,
                    ),
                )
            else:
                run_report.add_alert(
                    "info",
                    "x_slot_no_edition",
                    f"{today} 尚无已发布日报。",
                )
            changed |= x_queue.advance(state, run_started_at, settings)
            if changed:
                persist()

            job = x_queue.next_due(state, run_started_at, today)
            not_ready = publisher.not_ready_reason() if job else ""
            if job and not_ready:
                run_report.add_alert("info", "x_slot_skipped", not_ready)
            elif job:
                await self._send_x_job(
                    job, publisher, persist, now=run_started_at, run_report=run_report
                )

            for status, count in x_queue.counts(state, today).items():
                run_report.set_metric(f"x_jobs_{status}", count)
            new_attention = sorted(
                self._x_attention_jobs(state) - attention_before
            )
            if new_attention:
                labels = ", ".join(
                    f"{day} {language} #{slot} {status}"
                    for day, language, slot, status in new_attention
                )
                raise RuntimeError(
                    "X delivery needs a person to check the account: " + labels
                )
        except Exception as exc:
            run_report.fail(exc)
            self.console.print(f"[bold red]❌ X slot failed: {exc}[/bold red]")
            raise
        finally:
            self._finish_run_report(run_report)

    @staticmethod
    def _x_attention_jobs(state: dict) -> set[tuple[str, str, int, str]]:
        from .x_queue import ATTENTION_STATUSES

        return {
            (day, job["language"], job["slot"], job["status"])
            for day, edition in state["editions"].items()
            for job in edition["jobs"]
            if job["status"] in ATTENTION_STATUSES
        }

    async def _plan_x_edition(
        self,
        state: dict,
        *,
        daily_state,
        today: str,
        now: datetime,
        settings,
        run_report: "RunReport",
        helpers,
    ) -> bool:
        """Turn the published edition into planned X posts (text included)."""
        from . import x_queue

        build_story_post, compose_story_post, post_source_fields, figures = helpers
        config = self.config.x_delivery
        ai_client = None

        def template(item: ContentItem, language: str) -> str:
            return build_story_post(
                item,
                language=language,
                site_url=config.site_url,
                link_target=config.link_target,
                limit=config.max_post_chars,
                edition_date=today,
            )

        async def compose(item: ContentItem, language: str) -> tuple[str, str, str]:
            nonlocal ai_client
            if config.compose != "ai":
                return template(item, language), "template", ""
            text = None
            try:
                if ai_client is None:
                    ai_client = create_ai_client(self.config.ai)
                text = await compose_story_post(
                    ai_client, item, language=language, limit=config.max_post_chars
                )
            except Exception as exc:  # noqa: BLE001 - fall back to the template
                self.console.print(f"[yellow]⚠️  X composer unavailable: {exc}[/yellow]")
            if text is None:
                return template(item, language), "template", "compose_failed"
            sources = post_source_fields(item, language).values()
            if figures(text, sources):
                # A figure the published page does not carry is a fact risk,
                # not a style issue: use the assembled post instead.
                return template(item, language), "template", "unsupported_figures"
            return text, "ai", ""

        candidates: dict[str, list[x_queue.Candidate]] = {}
        for language in config.languages:
            entries = []
            for rank, item in enumerate(daily_state.items, start=1):
                if item.metadata.get("edition_mode") == "brief":
                    continue
                fields = post_source_fields(item, language)
                source = json.dumps(
                    {
                        "fields": fields,
                        "compose": config.compose,
                        "link_target": config.link_target,
                        "max_post_chars": config.max_post_chars,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                entries.append(
                    x_queue.Candidate(
                        key=x_queue.story_key_for_identity(item_identity(item)),
                        rank=rank,
                        title=fields["title"],
                        source_sha256=x_queue.text_digest(source),
                        item=item,
                    )
                )
            candidates[language] = entries

        summary = await x_queue.plan_edition(
            state,
            day=today,
            now=now,
            published_at=daily_state.updated_at,
            state_updated_at=x_queue.normalize_stamp(daily_state.updated_at),
            candidates=candidates,
            compose=compose,
            settings=settings,
        )
        if summary["late"]:
            run_report.add_alert(
                "warning",
                "x_edition_late",
                f"{today} 日报发布晚于计划时间超过 "
                f"{settings.max_publish_delay_minutes} 分钟，本期不推送 X。",
            )
        if summary["fallbacks"]:
            run_report.add_alert(
                "info",
                "x_compose_fallback",
                "X 文案回落到模板拼装：" + ", ".join(summary["fallbacks"]),
            )
        run_report.set_metric("x_posts_composed", summary["composed"])
        return bool(summary["changed"])

    async def _send_x_job(
        self,
        job: dict,
        publisher,
        persist,
        *,
        now: datetime,
        run_report: "RunReport",
    ) -> None:
        """Checkpoint, send exactly the stored text, record what it proved."""
        from .x_queue import text_digest

        if text_digest(job["text"]) != job["text_sha256"]:
            job["status"] = "failed"
            job["detail"] = "stored_text_mismatch"
            persist()
            return
        job["status"] = "pending"
        job["attempted_at"] = now.isoformat()
        job["detail"] = ""
        # If this checkpoint cannot be pushed, the exception stops the run
        # here, before the request: nothing is sent that is not recorded.
        persist()

        outcome = await publisher.publish_post(job["text"])
        label = f"{job['language']} #{job['slot']}"
        job["detail"] = outcome.detail
        if outcome.kind == "sent":
            job["status"] = "sent"
            job["tweet_id"] = outcome.tweet_id
            run_report.set_metric("x_posts_sent", 1)
            self.console.print(f"🐦 Posted {label} to X")
        elif outcome.kind in {"not_sent", "rate_limited"}:
            # X provably created nothing: try again on a later run, same text,
            # until the job's deadline.
            job["status"] = "planned"
            job["attempted_at"] = None
            run_report.add_alert(
                "warning", f"x_slot_{outcome.kind}", f"{label}: {outcome.detail}"
            )
        elif outcome.kind == "failed":
            job["status"] = "failed"
            run_report.add_alert(
                "failure",
                "x_slot_failed",
                f"{label}: {outcome.detail} 该语言今天停止推送，需人工处理。",
            )
        else:
            job["status"] = "unknown"
            run_report.add_alert(
                "failure",
                "x_slot_unknown",
                f"{label}: {outcome.detail} 不会自动重发，请人工核对账号后处理。",
            )
        persist()
