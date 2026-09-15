import React from 'react';
import {createRoot} from 'react-dom/client';
import {mainBody,marketLine} from './event-copy.js';
import {Table,TableHeader,TableBody,TableRow,TableHead,TableCell} from '@/components/ui/table';
const states={pending:'待发送',sending:'发送中',sent:'API已确认',unknown:'送达未知',failed:'失败',expired:'过期',not_queued:'未入队',baseline:'历史基线',archived:'仅归档'};
const stamp=t=>t?new Date(t*1000).toLocaleString('sv-SE',{hour12:false}):'—';
function official(url){try{const u=new URL(url);return u.protocol==='https:'&&['www.binance.com','binance.com','www.okx.com','okx.com','t.me'].includes(u.hostname)?u.href:null;}catch{return null;}}
let root;
export function renderTable(rows){root??=createRoot(document.getElementById('feed'));root.render(rows.length?<Table className="tape database-table"><TableHeader><TableRow>{['发现时间','类型','来源','币种','标题 / 正文','交付状态','原链接','ID'].map(x=><TableHead key={x}>{x}</TableHead>)}</TableRow></TableHeader><TableBody>{rows.map(e=>{const url=official(e.url);return <TableRow key={e.id}><TableCell>{stamp(e.detected)}</TableCell><TableCell>{e.kind==='market'?'异动':'公告'}</TableCell><TableCell>{e.source}</TableCell><TableCell>{e.symbol||'—'}</TableCell><TableCell className="subject"><details><summary>{e.kind==='market'?marketLine(e):e.title}</summary><div className="detail"><p>{mainBody(e.body)||'正文未就绪'}</p><p>发布时间：{stamp(e.published)} · 正文状态：{e.content_state||'—'}</p></div></details></TableCell><TableCell>{states[e.kind==='market'?e.notification_status||e.status:e.status]||e.status}</TableCell><TableCell>{url?<a href={url} target="_blank" rel="noopener noreferrer">原文 ↗</a>:'—'}</TableCell><TableCell title={e.id}>{e.id.slice(0,8)}</TableCell></TableRow>})}</TableBody></Table>:<div className="empty">暂无匹配记录</div>);}
