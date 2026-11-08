import {timingSafeEqual} from 'node:crypto';

type Story = {id:string;title:string;summary:string;background:string;url:string;source:string;published_at:string;score:number;references?:{title:string;url:string}[]};
export type Snapshot = {version:1;generated_at:string;collected_at:string;window_start:string;items:Story[]};
const DAY=86400000;
const headers={'Cache-Control':'no-store'};
const esc=(v:string)=>v.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const time=(v:string)=>new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(v)).replaceAll('/','.')+' CST';
export function validateSnapshot(value:unknown,now:number):Snapshot {
  if(!value||typeof value!=='object')throw Error('invalid snapshot');
  const v=value as Snapshot;
  const end=Date.parse(v.generated_at),collected=Date.parse(v.collected_at);
  if(v.version!==1||!Number.isFinite(end)||end>now+60000||end<now-30*60000||!Number.isFinite(collected)||collected>end||collected<end-DAY||Date.parse(v.window_start)!==end-DAY||!Array.isArray(v.items)||v.items.length>14)throw Error('invalid window');
  const seen=new Set<string>();
  const items=v.items.map(s=>{
    const stamp=Date.parse(s.published_at);
    if(!/^[a-f0-9]{32}$/.test(s.id)||seen.has(s.id)||!Number.isFinite(stamp)||stamp<end-DAY||stamp>=end||typeof s.score!=='number'||s.score<7||s.score>10)throw Error('invalid story');
    seen.add(s.id);
    for(const key of ['title','summary','background','source'] as const)if(typeof s[key]!=='string'||s[key].length>20000)throw Error('invalid text');
    if(!s.title.trim()||!s.summary.trim())throw Error('missing text');
    const url=new URL(s.url);if(!['https:','http:'].includes(url.protocol)||url.username||url.password)throw Error('invalid source');
    const references=(s.references||[]).slice(0,20).filter(r=>{
      try{const u=new URL(r.url);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password&&typeof r.title==='string'&&r.title.length<1000;}catch{return false;}
    }).map(r=>({title:r.title,url:r.url}));
    // Explicit whitelist: publisher metadata and unknown fields are discarded.
    return {id:s.id,title:s.title,summary:s.summary,background:s.background,url:url.href,source:s.source,published_at:new Date(stamp).toISOString(),score:s.score,references};
  });
  items.sort((a,b)=>Date.parse(b.published_at)-Date.parse(a.published_at));
  return {version:1,generated_at:new Date(end).toISOString(),collected_at:new Date(collected).toISOString(),window_start:new Date(end-DAY).toISOString(),items};
}
export function currentSnapshot(v:Snapshot,now:number):Snapshot {
  return {...v,window_start:new Date(now-DAY).toISOString(),items:v.items.filter(s=>Date.parse(s.published_at)>=now-DAY&&Date.parse(s.published_at)<now)};
}
const paragraphs=(text:string)=>text.split(/\n\s*\n/).filter(Boolean).map(p=>'<p>'+esc(p).replaceAll('\n','<br>')+'</p>').join('');
export function storyHtml(s:Story):string {
  return `<article class="digest-item core-story" id="story-${s.id}" data-story-id="${s.id}"><div class="story-meta"><span>精选资讯</span><time datetime="${esc(s.published_at)}">${esc(time(s.published_at))}</time></div><h2>${esc(s.title)}</h2><div class="story-body">${s.background?'<aside class="story-background"><span>背景</span>'+paragraphs(s.background)+'</aside>':''}<div class="story-summary-body">${paragraphs(s.summary)}</div>${s.references?.length?'<details class="references"><summary>参考资料</summary><ul>'+s.references.map(r=>'<li><a href="'+esc(r.url)+'" target="_blank" rel="noopener noreferrer">'+esc(r.title||r.url)+'</a></li>').join('')+'</ul></details>':''}<p class="source-line"><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.source||'原始来源')}</a></p><div class="story-actions"><a href="/story/${s.id}/">固定链接</a><button class="copy-link" type="button" data-copy="/story/${s.id}/" hidden>复制链接</button></div></div></article>`;
}
export function feedHtml(v:Snapshot,now:number):string {
  const current=currentSnapshot(v,now),stale=now-Date.parse(v.collected_at)>30*60000;
  return `<div class="stream-toolbar" data-live-revision="${esc(v.generated_at)}"><strong>最近 24 小时</strong><span class="stream-status">${stale?'采集延迟 · ':''}采集 ${esc(time(v.collected_at))} · 精选 ${esc(time(v.generated_at))}</span></div>${stale?'<p class="edition-notice">采集暂有延迟，以下仅保留仍在最近 24 小时内的精选。</p>':''}<section class="daily-day" data-live-stream>${current.items.map(storyHtml).join('')||'<p class="empty-state">最近 24 小时暂无达到精选标准的资讯。</p>'}</section>`;
}
export async function liveRoute(request:Request,env:Env):Promise<Response|null>{
  const path=new URL(request.url).pathname,story=/^\/story\/([a-f0-9]{32})\/$/.exec(path);
  if(path!=='/api/live.json'&&!story)return null;
  const gate=env.RECOVERY_GATE.getByName('rolling-news');
  if(path==='/api/live.json'&&request.method==='POST'){
    const provided=new TextEncoder().encode(request.headers.get('Authorization')||''),expected=new TextEncoder().encode('Bearer '+env.RECOVERY_CHECK_TOKEN);
    if(!env.RECOVERY_CHECK_TOKEN||provided.length!==expected.length||!timingSafeEqual(provided,expected))return Response.json({error:'unauthorized'},{status:401,headers});
    // Bound streamed input even when Content-Length is omitted or dishonest.
    const reader=request.body?.getReader();let size=0;const chunks:Uint8Array[]=[];
    if(!reader)return Response.json({error:'invalid_snapshot'},{status:400,headers});
    for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>500000){await reader.cancel();return new Response(null,{status:413,headers});}chunks.push(value);}
    try{
      const bytes=new Uint8Array(size);let pos=0;for(const chunk of chunks){bytes.set(chunk,pos);pos+=chunk.length;}
      const v=validateSnapshot(JSON.parse(new TextDecoder().decode(bytes)),Date.now());
      const accepted=await gate.feedPublish(JSON.stringify(v));
      return Response.json({accepted},{status:accepted?200:409,headers});
    }catch{return Response.json({error:'invalid_snapshot'},{status:400,headers});}
  }
  if(!['GET','HEAD'].includes(request.method))return new Response(null,{status:405,headers:{...headers,Allow:'GET, HEAD'}});
  const saved=await gate.feedRead(story?'story:'+story[1]:'snapshot');
  if(!saved)return Response.json({error:'not_available'},{status:503,headers});
  if(story){
    const s=JSON.parse(saved) as Story;
    return new Response(request.method==='HEAD'?null:`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(s.title)} · xiyu.news</title><link rel="stylesheet" href="/assets/css/core.css"><body class="core-site dense-site"><main class="reader"><p><a href="/">← 返回信息流</a></p>${storyHtml(s)}</main><script src="/assets/js/core.js" defer></script></body></html>`,{headers:{...headers,'Content-Type':'text/html;charset=utf-8'}});
  }
  const v=JSON.parse(saved) as Snapshot;
  return new Response(request.method==='HEAD'?null:JSON.stringify({...currentSnapshot(v,Date.now()),stale:Date.now()-Date.parse(v.collected_at)>30*60000}),{headers:{...headers,'Content-Type':'application/json'}});
}
export async function liveHome(response:Response,env:Env):Promise<Response>{
  if(!response.ok||!response.headers.get('Content-Type')?.includes('text/html'))return response;
  const raw=await env.RECOVERY_GATE.getByName('rolling-news').feedRead('snapshot');
  const result=new HTMLRewriter().on('[data-live-home]',{element(element){
    if(raw)element.setInnerContent(feedHtml(JSON.parse(raw),Date.now()),{html:true});
    else element.prepend('<p class="edition-notice">实时精选尚未就绪，以下为已归档日报。</p>',{html:true});
  }}).transform(response);
  const h=new Headers(result.headers);h.set('Cache-Control','no-store');h.delete('ETag');h.delete('Content-Length');
  return new Response(result.body,{status:result.status,headers:h});
}
