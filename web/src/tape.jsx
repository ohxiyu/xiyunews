import React from 'react';
import {createRoot} from 'react-dom/client';
import {mainBody,marketLine} from './event-copy.js';
import {Badge} from '@/components/ui/badge';
const names={binance_spot:'Binance 现货',binance_futures:'Binance 合约（历史）',binance:'Binance',okx:'OKX',hyperliquid:'Hyperliquid'};
const states={pending:'待发送',sending:'发送中',sent:'API 已确认',unknown:'送达未知',failed:'发送失败',expired:'已过期',not_queued:'仅网页预警',baseline:'历史基线',archived:'仅展示'};
const stamp=t=>new Date(t*1000).toLocaleString('zh-CN',{hour12:false});
function official(url){try{const u=new URL(url);return u.protocol==='https:'&&['www.binance.com','binance.com','www.okx.com','okx.com','t.me'].includes(u.hostname)?u.href:null;}catch{return null;}}
let root;
export function renderTable(rows,kind,view){root??=createRoot(document.getElementById('feed'));root.render(rows.length?<ol className="timeline">{rows.map(e=>{const s=e.signal;const market=e.kind==='market';const url=official(e.url);return <li key={e.id} className={'timeline-item '+(market?'market-item':'announcement-item')}><div className="event-meta"><time dateTime={new Date(e.detected*1000).toISOString()}>{stamp(e.detected)}</time><Badge variant="outline">{market?'异动':'公告'}</Badge><span>{names[e.source]||e.source}</span><span className="delivery">{states[s?e.notification_status:e.status]||e.status}</span></div>{market?<p className={'market-copy '+(marketLine(e).includes('上涨')?'up':'down')}>{marketLine(e)}</p>:<article className="announcement-copy"><h3>{url?<a href={url} target="_blank" rel="noopener noreferrer">{e.title}</a>:e.title}</h3><p>{mainBody(e.body||e.brief)||(e.status==='baseline'?'历史基线 · 正文未补采':e.content_state==='translation_pending'?'中文正文待翻译':'正文尚未就绪')}</p></article>}</li>})}</ol>:<div className="empty">{kind==='announcement'&&view==='live'?'暂无匹配公告，正在实时采集。':'暂无匹配记录，正在实时采集。'}</div>);}
