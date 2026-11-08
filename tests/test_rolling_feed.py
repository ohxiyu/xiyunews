from datetime import datetime,timedelta,timezone
from src.rolling_feed import active_items,snapshot
from test_core_site import story

def test_rolling_window_uses_source_time_and_excludes_future_and_expired():
 now=datetime(2026,11,8,12,tzinfo=timezone.utc)
 items=[]
 for index,offset in enumerate([-24,-24.001,-1,0,1]):
  item=story(index);item.published_at=now+timedelta(hours=offset);items.append(item)
 assert [i.id for i in active_items(items,now)]==['2','0']
 value=snapshot(items,now=now,collected_at=now-timedelta(minutes=1))
 assert len(value['items'])==2
 assert value['items'][0]['published_at']==items[2].published_at.isoformat()
 assert value['collected_at']!=value['items'][0]['published_at']

def test_stable_permalink_survives_reranking_and_same_source_identity():
 now=datetime(2026,11,8,12,tzinfo=timezone.utc);a=story(1);b=story(2)
 first=snapshot([a,b],now=now,collected_at=now)
 a.ai_score=8;a.metadata['detailed_summary_zh']='完整更新正文。'
 second=snapshot([b,a],now=now+timedelta(minutes=5),collected_at=now)
 assert {i['url']:i['id'] for i in first['items']}=={i['url']:i['id'] for i in second['items']}
 assert '完整更新正文。' in str(second)
