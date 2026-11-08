"""Enrichment output tags must never replace its input cache identity."""
import asyncio
from pathlib import Path
from test_core_site import story
from src.models import Config
from src.orchestrator import BMTNewsOrchestrator
from src.storage.manager import StorageManager
from src.ai.result_cache import AnalysisResultCache


def test_repeat_enrichment_reuses_original_analysis_tags_and_invalidates_changed_input(tmp_path,monkeypatch):
    runner=BMTNewsOrchestrator(Config.model_validate_json(Path("data/config.github.json").read_text()),StorageManager(data_dir=str(tmp_path/'storage')))
    runner._analysis_cache=AnalysisResultCache(tmp_path/'cache.json',model='same-model')
    calls=[]
    async def enrich(_self,items):
        calls.append(len(items))
        for item in items:
            item.ai_tags=['rewritten-output-tag']
            item.metadata.update({'background_zh':'背景事实。','detailed_summary_zh':'完整事实。','editorial_tags':['rewritten-output-tag']})
    monkeypatch.setattr('src.orchestrator.create_ai_client',lambda config:object())
    monkeypatch.setattr('src.orchestrator.ContentEnricher.enrich_batch',enrich)
    first=story();first.ai_tags=['original-analysis-tag']
    original=first.model_copy(deep=True)
    asyncio.run(runner._enrich_important_items([first]))
    # Reload the on-disk cache to prove reuse across processes/runs.
    runner._analysis_cache=AnalysisResultCache(tmp_path/'cache.json',model='same-model')
    repeat=original.model_copy(deep=True)
    asyncio.run(runner._enrich_important_items([repeat]))
    assert calls==[1]
    assert repeat.metadata['background_zh']=='背景事实。'
    assert repeat.ai_tags==['rewritten-output-tag']
    changed=original.model_copy(deep=True);changed.ai_tags=['new-analysis-tag']
    asyncio.run(runner._enrich_important_items([changed]))
    assert calls==[1,1]
