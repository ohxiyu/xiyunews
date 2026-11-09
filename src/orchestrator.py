"""One fixed Chinese daily edition, coordinating four bounded pipeline stages."""
from __future__ import annotations
import time
from collections import defaultdict
from datetime import date as date_type, datetime, timedelta, timezone
from pathlib import Path
from rich.console import Console
from .models import Config, SourceType
from .storage.manager import StorageManager
from .collection import CollectionPipeline, FetchReport, SourceFetchOutcome
from .selection import SelectionPipeline, BalancedDigestResult, FilteringPipelineResult, _deduplication_url_key
from .enrichment import EnrichmentPipeline
from .publication import PublicationPipeline
from .x_distribution import XDistributionPipeline
from .daily_feed import item_identity, analyzed_item_key, load_daily_feed_state, save_daily_feed_state
from .edition import DEFAULT_STAGING_PATH, edition_window_for, edition_window_for_date, items_in_edition_window, items_in_supplemental_window, load_staging_state, merge_staged_items, save_staging_state
from .edition_fallback import save_selection
from .ai.errors import ProviderAccountError
from .ai.chinese import chinese_ready, brief
from .ai.tokens import get_usage_snapshot, reset_usage, task_usage_snapshot
from .run_report import RunReport, save_run_report
from .services.x_delivery import XEditionPublisher


class BMTNewsOrchestrator(CollectionPipeline, SelectionPipeline, EnrichmentPipeline, PublicationPipeline, XDistributionPipeline):
    def __init__(self, config: Config, storage: StorageManager):
        self.config=config
        self.storage=storage
        self.console=Console()
        self.x_publisher=(XEditionPublisher(config.x_delivery,console=self.console)
                          if config.x_delivery and config.x_delivery.enabled else None)
        self.last_fetch_report=None
        self.last_run_report=None
        self._analysis_cache=None

    def _set_timing(self, name: str, started: float) -> None:
        if self.last_run_report is not None:
            self.last_run_report.add_timing(name, time.perf_counter() - started)

    def _finish_run_report(self, report: RunReport) -> Path:
        usage = get_usage_snapshot()
        report.set_metric("ai_input_tokens", usage.total_input_tokens)
        report.set_metric("ai_output_tokens", usage.total_output_tokens)
        report.set_metric("ai_total_tokens", usage.total_tokens)
        report.ai_usage = task_usage_snapshot()
        cache = getattr(self, "_analysis_cache", None)
        if cache is not None:
            cache.save()
            report.set_metric("comparison_cache_hits", cache.comparison_hits)
            report.set_metric("comparison_cache_misses", cache.comparison_misses)
            report.set_metric("event_relation_cache_hits", cache.relation_hits)
            report.set_metric("event_relation_cache_misses", cache.relation_misses)
        report.finish()
        from .operations import record_cost
        report.ai_cost = record_cost(report.to_dict())
        from .publication_state import active_store
        backend = active_store()
        if backend is not None:
            backend.save_report(report.to_dict())
        return save_run_report(report)

    async def run_daily_edition(self, force_hours: int | None=None, *, staging_path: Path=DEFAULT_STAGING_PATH, cutoff_hour: int=7, edition_date: date_type | None=None, now: datetime | None=None, force_publish: bool=False) -> None:
        """Build one edition from the latest completed fixed cutoff window."""
        reset_usage()
        timezone_name = self.config.filtering.daily_timezone
        run_started_at = now or datetime.now(timezone.utc)
        if run_started_at.tzinfo is None:
            run_started_at = run_started_at.replace(tzinfo=timezone.utc)
        window = edition_window_for_date(edition_date, timezone_name, cutoff_hour) if edition_date is not None else edition_window_for(run_started_at, timezone_name, cutoff_hour)
        if edition_date is not None and window.end.astimezone(timezone.utc) > run_started_at.astimezone(timezone.utc):
            raise ValueError('edition_date cutoff has not completed in the configured timezone')
        run_report = RunReport.start(date=window.date, timezone_name=timezone_name, started_at=run_started_at, kind='daily_publish', window_start=window.start, window_end=window.end)
        cutoff_lag_minutes = max(0, int((run_started_at.astimezone(timezone.utc) - window.end.astimezone(timezone.utc)).total_seconds() // 60))
        run_report.set_metric('cutoff_lag_minutes', cutoff_lag_minutes)
        if cutoff_lag_minutes > 60:
            run_report.add_alert('warning', 'edition_started_late', f'日报在固定截止时间后 {cutoff_lag_minutes} 分钟才开始运行。')
        reset_usage()
        self.last_run_report = run_report
        self.console.print('[bold cyan]🗞️ xiyu.news - Building the daily edition...[/bold cyan]\n')
        self.console.print(f'🕗 Edition window: {window.start.isoformat()} → {window.end.isoformat()} (end exclusive)\n')
        allow_cached_fallback = False
        try:
            daily_state = load_daily_feed_state(window.date, timezone_name)
            already_published = daily_state.items and daily_state.updated_at.astimezone(timezone.utc) >= window.end.astimezone(timezone.utc)
            if already_published:
                recovered_nodes = 0
                run_report.set_metric('displayed_today', len(daily_state.items))
                run_report.add_alert('info', 'edition_already_published', '本期选稿已保存；跳过重复采集与 AI 分析，仅在产物缺失时恢复静态页面。')
                self.console.print('[green]Reusing the saved edition; no duplicate collection, AI or channel delivery.[/green]')
                languages = ['zh']
                required = [Path('docs/editions') / window.date / 'edition.json']
                for language in languages:
                    required += [Path('docs/_posts') / f'{window.date}-summary-{language}.md', Path('docs/editions') / window.date / f'{language}.html']
                if recovered_nodes or not all((path.is_file() for path in required)):
                    from .publication_state import active_store
                    store = active_store()
                    metrics = store.latest_edition_metrics(window.date) if store else {}
                    for key in ('edition_candidates', 'analyzed_today', 'high_priority'):
                        if key in metrics:
                            run_report.set_metric(key, metrics[key])
                    save_daily_feed_state(daily_state)
                    await self._publish_outputs(daily_state.items, date=window.date, total_candidates=metrics.get('edition_candidates', 0), timezone_name=timezone_name, run_report=run_report, window_start=window.start, window_end=window.end, static_only=True)
                    self._publish_archive_artifacts(daily_state.items, date=window.date, run_report=run_report, window_start=window.start, window_end=window.end)
                    if not all((path.is_file() for path in required)):
                        raise RuntimeError('Static edition recovery did not produce every required artifact')
                    run_report.add_alert('warning', 'edition_static_recovered', '从已保存选稿恢复缺失页面，未调用信源/AI/渠道；未保存的行情与今日脉络不重新生成。')
                return
            allow_cached_fallback = True
            staging_exists = staging_path.exists()
            staging_state = load_staging_state(staging_path)
            run_report.set_metric('staging_items_before', len(staging_state.items))
            if not staging_exists:
                run_report.add_alert('warning', 'staging_cache_missing', '未找到日内暂存缓存，日报将只使用最终补采结果。')
            else:
                staging_age_minutes = max(0, int((run_started_at.astimezone(timezone.utc) - staging_state.updated_at.astimezone(timezone.utc)).total_seconds() // 60))
                run_report.set_metric('staging_age_minutes', staging_age_minutes)
                if staging_age_minutes > 14 * 60:
                    run_report.add_alert('warning', 'staging_cache_stale', f'日内暂存缓存已 {staging_age_minutes} 分钟未更新。')
            filtering_config = self.config.filtering
            hours = force_hours or filtering_config.time_window_hours
            fallback_hours = filtering_config.fallback_window_hours
            fetch_hours = max(hours, fallback_hours or hours)
            fallback_start = window.end.astimezone(timezone.utc) - timedelta(hours=fallback_hours) if fallback_hours is not None else window.start.astimezone(timezone.utc)
            since = min(run_started_at - timedelta(hours=fetch_hours), fallback_start)
            fetch_started = time.perf_counter()
            fresh_items = await self.fetch_all_sources(since)
            run_report.set_timing('fetch', time.perf_counter() - fetch_started)
            run_report.set_metric('fetched_raw', len(fresh_items))
            run_report.attach_fetch_report(self.last_fetch_report.to_dict() if self.last_fetch_report is not None else None)
            fresh_items = self.merge_cross_source_duplicates(fresh_items)
            fresh_identities = {item_identity(item) for item in fresh_items}
            run_report.set_metric('unique_after_url_dedup', len(fresh_items))
            staged_items = merge_staged_items(staging_state.items, fresh_items, now=run_started_at)
            save_staging_state(staged_items, staging_path, updated_at=run_started_at)
            run_report.set_metric('staged_total', len(staged_items))
            suppressed_keys = set()
            candidates = self.merge_cross_source_duplicates(items_in_edition_window(staged_items, window))
            if suppressed_keys:
                before_suppress = len(candidates)
                candidates = [item for item in candidates if _deduplication_url_key(str(item.url)) not in suppressed_keys]
                if before_suppress != len(candidates):
                    run_report.set_metric('suppressed_manual', before_suppress - len(candidates))
            run_report.set_metric('staging_only_candidates', sum((item_identity(item) not in fresh_identities for item in candidates)))
            run_report.set_metric('edition_candidates', len(candidates))
            run_report.set_metric('current_day_items', len(candidates))
            candidate_source_counts: dict[str, int] = defaultdict(int)
            for item in candidates:
                source_key = f'{item.source_type.value}/{self._sub_source_label(item)}'
                candidate_source_counts[source_key] += 1
            run_report.set_breakdown('candidate_sources', dict(sorted(candidate_source_counts.items())))
            run_report.set_breakdown('candidate_groups', self._group_breakdown(candidates))
            minimum_candidates = filtering_config.minimum_candidate_items
            if minimum_candidates is not None and len(candidates) < minimum_candidates:
                run_report.add_alert('warning', 'candidate_shortage', f'固定 24 小时候选只有 {len(candidates)}/{minimum_candidates} 条，已记录来源供给不足。')
            self.console.print(f'📚 {len(candidates)} unique candidates fall inside this edition\n')
            supplemental_candidates = self.merge_cross_source_duplicates(items_in_supplemental_window(staged_items, window, fallback_hours)) if fallback_hours is not None else []
            if suppressed_keys:
                supplemental_candidates = [item for item in supplemental_candidates if _deduplication_url_key(str(item.url)) not in suppressed_keys]
            final_fetch_failed = bool(self.last_fetch_report and self.last_fetch_report.all_failed)
            if final_fetch_failed and (not candidates) and (not supplemental_candidates):
                if daily_state.items:
                    run_report.add_alert('warning', 'edition_retry_preserved', '最终采集失败且无可用候选，保留已发布的本期内容。')
                    self.console.print('[yellow]No recoverable candidates; preserving the already-published edition.[/yellow]')
                    return
                raise RuntimeError(self.last_fetch_report.failure_message())
            if final_fetch_failed:
                run_report.add_alert('warning', 'final_fetch_failed_using_staging', '最终采集全部失败，已使用当日早前暂存内容继续出刊。')
            if not candidates and (not supplemental_candidates) and daily_state.items:
                run_report.add_alert('info', 'edition_retry_preserved', '本次没有恢复到候选内容，保留已发布的本期内容。')
                self.console.print('[yellow]No candidates recovered; preserving the already-published edition.[/yellow]')
                return
            published_identities = {item_identity(item) for item in daily_state.dedup_history}
            before_history_filter = len(candidates)
            candidates = [item for item in candidates if item_identity(item) not in published_identities]
            run_report.set_metric('skipped_published_history', before_history_filter - len(candidates))
            total_candidates_considered = before_history_filter
            analyzed_items = await self._analyze_content(candidates, edition_window=window) if candidates else []
            filtering_result = await self.filter_items(analyzed_items, apply_balance=False, dedup_context=daily_state.dedup_history)
            qualified_items = self._distinct_daily_events(await self.merge_topic_duplicates(filtering_result.items, daily_events=True))
            threshold_count = filtering_result.threshold_count
            topic_duplicates_removed = filtering_result.topic_dedup_removed
            balanced_result = self.apply_balanced_digest(qualified_items, log=False)
            qualified_items, balanced_result = await self._audit_daily_ranking(qualified_items, balanced_result)
            audited_selection = tuple((id(item) for item in balanced_result.items))
            minimum_display = filtering_config.minimum_display_items
            if minimum_display is not None and len(balanced_result.items) < minimum_display:
                balanced_result = self.apply_balanced_digest(qualified_items, allow_primary_borrowing=True)
            fallback_used = bool(fallback_hours is not None and minimum_display is not None and (len(balanced_result.items) < minimum_display))
            if fallback_used:
                total_candidates_considered += len(supplemental_candidates)
                run_report.set_metric('fallback_candidates', len(supplemental_candidates))
                fallback_source_counts: dict[str, int] = defaultdict(int)
                for item in supplemental_candidates:
                    source_key = f'{item.source_type.value}/{self._sub_source_label(item)}'
                    fallback_source_counts[source_key] += 1
                run_report.set_breakdown('fallback_candidate_sources', dict(sorted(fallback_source_counts.items())))
                run_report.set_breakdown('fallback_candidate_groups', self._group_breakdown(supplemental_candidates))
                normal_identities = {item_identity(item) for item in candidates}
                fallback_before_history = len(supplemental_candidates)
                supplemental_candidates = [item for item in supplemental_candidates if item_identity(item) not in published_identities and item_identity(item) not in normal_identities]
                run_report.set_metric('skipped_published_history', run_report.metrics.get('skipped_published_history', 0) + fallback_before_history - len(supplemental_candidates))
                fallback_analyzed = await self._analyze_content(supplemental_candidates, edition_window=window) if supplemental_candidates else []
                analyzed_items.extend(fallback_analyzed)
                run_report.set_metric('fallback_analyzed', len(fallback_analyzed))
                fallback_filtering = await self.filter_items(fallback_analyzed, apply_balance=False, dedup_context=[*daily_state.dedup_history, *qualified_items])
                threshold_count += fallback_filtering.threshold_count
                topic_duplicates_removed += fallback_filtering.topic_dedup_removed
                fallback_qualified = fallback_filtering.items
                qualified_items = self._distinct_daily_events(await self.merge_topic_duplicates([*qualified_items, *fallback_qualified], daily_events=True))
                balanced_result = self.apply_balanced_digest(qualified_items, allow_primary_borrowing=True, fill_to_minimum=True)
                run_report.add_alert('info', 'fallback_window_used', f'固定窗口内容不足，已启用 {fallback_hours} 小时未发布内容保底；评分阈值和历史去重保持不变。')
            elif minimum_display is not None and len(balanced_result.items) < minimum_display:
                balanced_result = self.apply_balanced_digest(qualified_items, allow_primary_borrowing=True, fill_to_minimum=True)
            if tuple((id(item) for item in balanced_result.items)) != audited_selection:
                qualified_items, balanced_result = await self._audit_daily_ranking(qualified_items, balanced_result)
            important_items = balanced_result.items
            low_signal_minimum = filtering_config.low_signal_minimum_items
            if not important_items and analyzed_items and (threshold_count == 0) and (low_signal_minimum is not None):
                important_items = self._rescue_low_signal_items(analyzed_items, limit=low_signal_minimum)
                rescue = await self.filter_items(important_items, threshold=0, apply_balance=False, dedup_context=daily_state.dedup_history)
                _, balanced_result = await self._audit_daily_ranking(rescue.items, self.apply_balanced_digest(rescue.items, log=False))
                important_items = balanced_result.items
                if important_items:
                    run_report.set_metric('low_signal_rescued', len(important_items))
                    run_report.add_alert('warning', 'low_signal_edition', f'没有内容达到 {filtering_config.ai_score_threshold:g} 分阈值；已按分数保底选取 {len(important_items)} 条发布，避免出空刊。')
                    self.console.print(f'[yellow]⚠️  Low-signal day: publishing the {len(important_items)} highest-scored items instead of an empty edition.[/yellow]')
            run_report.set_metric('analyzed_this_run', len(analyzed_items))
            run_report.set_metric('analyzed_today', len(analyzed_items))
            run_report.set_metric('above_threshold', threshold_count)
            run_report.set_metric('below_threshold', len(analyzed_items) - threshold_count)
            run_report.set_metric('topic_duplicates_removed', topic_duplicates_removed)
            run_report.set_metric('qualified_after_topic_dedup', len(qualified_items))
            run_report.set_metric('category_reclassified', sum((item.metadata.get('source_category') != item.metadata.get('category') for item in analyzed_items if 'source_category' in item.metadata)))
            run_report.set_metric('quota_borrowed', balanced_result.borrowed_count)
            run_report.set_metric('category_limit_deferred', balanced_result.category_limit_deferred)
            run_report.set_metric('source_limit_deferred', balanced_result.source_limit_deferred)
            run_report.set_metric('minimum_fill_added', balanced_result.minimum_fill_count)
            run_report.set_metric('balanced_digest_removed', max(0, len(qualified_items) - len(important_items)))
            minimum_qualified = filtering_config.minimum_qualified_items
            if minimum_qualified is not None and len(qualified_items) < minimum_qualified:
                run_report.add_alert('warning', 'qualified_content_shortage', f'达到 {filtering_config.ai_score_threshold:g} 分且去重后的内容只有 {len(qualified_items)}/{minimum_qualified} 条；低信号保底另行标注。')
            if minimum_display is not None and len(important_items) < minimum_display:
                run_report.add_alert('warning', 'short_edition', f'本期最终只有 {len(important_items)}/{minimum_display} 条；已发布短版，未复用历史内容；低信号保底另行标注。')
            group_labels = {key: group.name or key for key, group in self.config.filtering.category_groups.items()}
            selected_groups = {group_labels.get(key, key): count for key, count in balanced_result.group_counts.items()}
            group_limits = {group_labels.get(key, key): limit for key, limit in balanced_result.group_limits.items() if limit is not None}
            run_report.set_breakdown('selected_groups', selected_groups)
            run_report.set_breakdown('group_limits', group_limits)
            run_report.set_breakdown('qualified_groups', self._group_breakdown(qualified_items))
            primary_groups = set(self.config.filtering.primary_groups)
            primary_selected = sum((balanced_result.group_counts.get(group, 0) for group in primary_groups))
            primary_required = self.config.filtering.primary_group_min_items or 0
            run_report.set_metric('primary_selected', primary_selected)
            run_report.set_metric('primary_required', primary_required)
            if primary_selected < primary_required:
                run_report.add_alert('warning', 'primary_quota_shortfall', f'Crypto 主轨只有 {primary_selected}/{primary_required} 条合格内容；未用低分内容强行补足。')
            selected_source_counts: dict[str, int] = defaultdict(int)
            for item in important_items:
                source_key = f'{item.source_type.value}/{self._sub_source_label(item)}'
                selected_source_counts[source_key] += 1
            run_report.set_breakdown('selected_sources', dict(sorted(selected_source_counts.items())))
            run_report.set_breakdown('qualified_sources', self._source_breakdown(qualified_items))
            if not important_items:
                allow_cached_fallback = False
                if await self._publish_cached_brief(window, run_report, run_started_at):
                    return
                raise RuntimeError('No qualified scored Chinese content; edition not published')
            save_selection(important_items, self.config, window, now=run_started_at)
            await self._enrich_important_items(important_items)
            important_items = [item for item in important_items if chinese_ready(item) and (not item.metadata.get('chinese_invalid'))]
            if not important_items:
                raise RuntimeError('No valid Chinese content after enrichment; edition not published')
            degraded = sum((item.metadata.get('enrichment_status') in {'translation_only', 'brief'} for item in important_items))
            run_report.set_metric('enrichment_degraded', degraded)
            if degraded:
                run_report.set_metric('edition_degraded', 1)
                for item in important_items:
                    brief(item)
                run_report.add_alert('warning', 'enrichment_degraded', f'{degraded} 条内容扩写失败，仅保留已评分的中文摘要。')
            important_items = self._distinct_daily_events(important_items)
            important_items = [*[item for item in important_items if item.source_type == SourceType.EDITORIAL], *sorted((item for item in important_items if item.source_type != SourceType.EDITORIAL), key=lambda item: item.ai_score or 0, reverse=True)]
            run_report.set_breakdown('final_selected_groups', self._group_breakdown(important_items))
            run_report.set_breakdown('final_selected_sources', self._source_breakdown(important_items))
            final_primary = sum((self._group_breakdown(important_items).get(group_labels.get(group, group), 0) for group in primary_groups))
            run_report.set_metric('final_primary_selected', final_primary)
            if minimum_display is not None and len(important_items) < minimum_display:
                run_report.add_alert('warning', 'short_edition', f'最终仅有 {len(important_items)}/{minimum_display} 条，未降低质量标准补足。')
            existing_display_identities = {item_identity(item) for item in daily_state.items}
            allow_cached_fallback = False
            daily_state.items = important_items
            daily_state.updated_at = run_started_at
            daily_state.analyzed_keys = sorted((analyzed_item_key(item) for item in analyzed_items))
            state_path = save_daily_feed_state(daily_state)
            self.console.print(f'🧩 Saved {len(important_items)} selected items to {state_path}\n')
            displayed_identities = {item_identity(item) for item in important_items}
            run_report.set_metric('newly_displayed', len(displayed_identities - existing_display_identities))
            run_report.set_metric('displayed_today', len(important_items))
            run_report.set_metric('high_priority', sum(((item.ai_score or 0) >= 9 for item in important_items)))
            published = await self._publish_outputs(important_items, date=window.date, total_candidates=total_candidates_considered, timezone_name=timezone_name, run_report=run_report, window_start=window.start, window_end=window.end, x_posted_languages=daily_state.x_posted_languages, skip_telegram=bool(already_published and force_publish))
            newly_posted = published.get('x_posted') or []
            if newly_posted:
                daily_state.x_posted_languages = sorted({*daily_state.x_posted_languages, *newly_posted})
                save_daily_feed_state(daily_state)
            archive_started = time.perf_counter()
            self._publish_archive_artifacts(important_items, date=window.date, run_report=run_report, window_start=window.start, window_end=window.end, market=published.get('market'), overviews=published.get('overviews'))
            run_report.set_timing('archive_artifacts', time.perf_counter() - archive_started)
            self.console.print('[bold green]✅ Daily edition completed successfully![/bold green]')
        except Exception as exc:
            if allow_cached_fallback:
                if isinstance(exc, ProviderAccountError):
                    run_report.set_metric('provider_account_http_status', exc.status_code)
                    run_report.add_alert('warning', 'ai_account_blocked', f'AI账户不可用（HTTP {exc.status_code}），停止调用并检查合格缓存。')
                if await self._publish_cached_brief(window, run_report, run_started_at):
                    return
            run_report.fail(exc)
            self.console.print(f'[bold red]❌ Edition failed: {exc}[/bold red]')
            raise
        finally:
            usage = get_usage_snapshot()
            run_report.set_metric('ai_input_tokens', usage.total_input_tokens)
            run_report.set_metric('ai_output_tokens', usage.total_output_tokens)
            run_report.set_metric('ai_total_tokens', usage.total_tokens)
            cache = self._result_cache()
            if cache is not None:
                cache.save()
                run_report.set_metric('analysis_cache_entries', len(cache.entries))
            self._finish_run_report(run_report)
