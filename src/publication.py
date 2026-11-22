"""Deterministic Chinese edition artifacts; X distribution runs after deployment."""
from __future__ import annotations
import time
from datetime import date as date_type
from pathlib import Path
from ._file_utils import _atomic_write_text
from .daily_feed import load_daily_feed_state, save_daily_feed_state
from .edition_fallback import cached_selection
from .archive import build_records, load_recent_archive, save_edition_records
from .api_output import build_edition_payload, write_edition_api, write_editions_index
from .core_site import render_core_feed
from .ai.summarizer import DailySummarizer
from .web_feed import _top_level_category


class PublicationPipeline:
    async def _publish_outputs(self, items, *, date, total_candidates, timezone_name,
                               run_report, window_start=None, window_end=None,
                               x_posted_languages=None, static_only=False):
        """Write the single Chinese page and fragment, with no AI or network calls."""
        started=time.perf_counter()
        summary=await DailySummarizer(display_timezone=timezone_name).generate_summary(
            items,date,total_candidates,language='zh')
        self.storage.save_daily_summary(date,summary,language='zh')
        run_report.record_summary('zh')
        window=(f'window_start: "{window_start.isoformat()}"\nwindow_end: "{window_end.isoformat()}"\n'
                if window_start is not None and window_end is not None else '')
        front=('---\nlayout: default\n'+f'title: "xiyu.news: {date}"\ndate: {date}\nlang: zh\n'
               +f'fetched_count: {total_candidates}\nselected_count: {len(items)}\n'
               +f'fragment_url: "/editions/{date}/zh.html"\n'+window+'---\n\n')
        body=render_core_feed(items,date=date,display_timezone=timezone_name)
        post=Path('docs/_posts')/f'{date}-summary-zh.md'
        fragment=Path('docs/editions')/date/'zh.html'
        post.parent.mkdir(parents=True,exist_ok=True);fragment.parent.mkdir(parents=True,exist_ok=True)
        # Static recovery fills absent files; existing published text stays intact.
        if not static_only or not post.is_file():_atomic_write_text(post,front+body)
        if not static_only or not fragment.is_file():
            _atomic_write_text(fragment,f'<div class="daily-feed-content" data-feed-fragment="2" data-language="zh" data-date="{date}">{body}</div>\n')
        run_report.set_timing('publish_outputs',time.perf_counter()-started)
        return {'x_posted':[]}

    def _publish_archive_artifacts(self,items,*,date,run_report,window_start=None,window_end=None,**_):
        """Persist dated JSON and archive without generating retired products."""
        records=build_records(items,date=date,top_category_of=_top_level_category)
        save_edition_records(records,date=date)
        payload=build_edition_payload(records,date=date,stats={
            'candidates':run_report.metrics.get('edition_candidates',0),
            'analyzed':run_report.metrics.get('analyzed_today',0),
            'displayed':run_report.metrics.get('displayed_today',0),
            'high_priority':run_report.metrics.get('high_priority',0)},
            window_start=window_start,window_end=window_end)
        write_edition_api(payload,date=date)
        write_editions_index(load_recent_archive(120,today=date_type.fromisoformat(date)))
        run_report.set_metric('archive_records',len(records))

    async def _publish_cached_brief(self,window,report,started_at):
        items=cached_selection(self.config,window)
        if not items:
            report.add_alert('failure','no_qualified_cache','没有本刊期已打分、去重且中文合格的缓存，不出刊。')
            return False
        state=load_daily_feed_state(window.date,self.config.filtering.daily_timezone)
        if state.items and state.updated_at>=window.end:
            report.add_alert('warning','existing_edition_preserved','保留已保存期刊，不覆盖或补发。')
            return True
        state.items=items;state.updated_at=started_at
        save_daily_feed_state(state)
        report.add_alert('warning','brief_edition','AI不可用，使用此前已打分、去重的中文缓存发布简版。')
        report.set_metric('edition_degraded',1);report.set_metric('displayed_today',len(items))
        report.set_metric('edition_candidates',len(items))
        try:
            await self._publish_outputs(items,date=window.date,total_candidates=len(items),timezone_name=self.config.filtering.daily_timezone,run_report=report,window_start=window.start,window_end=window.end)
            self._publish_archive_artifacts(items,date=window.date,run_report=report,window_start=window.start,window_end=window.end)
        except Exception as exc:
            report.fail(exc)
            raise
        return True
