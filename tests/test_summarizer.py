import asyncio
from datetime import datetime,timezone
import pytest
from src.ai.summarizer import DailySummarizer
from src.models import ContentItem,SourceType


def test_chinese_backup_retains_complete_body_and_escapes_source_text():
    item=ContentItem(id='a',title='原始标题',url='https://example.com/a',source_type=SourceType.RSS,
        published_at=datetime.now(timezone.utc),ai_summary='原始事实。',metadata={
            'title_zh':'<script>中文标题</script>','detailed_summary_zh':'第一段。\n\n第二段。',
            'background_zh':'<img src=x>背景。'})
    text=asyncio.run(DailySummarizer().generate_summary([item],'2026-11-09',1))
    assert '第一段。\n\n第二段。' in text and '原始来源' in text
    assert '<script>' not in text and '<img' not in text
    assert '&lt;script&gt;' in text and '背景。' in text
    with pytest.raises(ValueError):asyncio.run(DailySummarizer().generate_summary([item],'2026-11-09',1,language='en'))
