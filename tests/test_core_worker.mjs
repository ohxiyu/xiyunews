import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../docs/core-worker.js';
const run=(path,method='GET')=>worker.fetch(new Request('https://xiyu.news'+path,{method}),{ASSETS:{fetch:async()=>new Response('fresh',{headers:{'Cache-Control':'public, max-age=999'}})}});
test('retired mutations cannot reach any asset or legacy Git handler',async()=>{for(const path of ['/s','/s/','/admin/','/api/admin/posts','/api/quick-posts','/api/quick-posts.json','/oauth/auth','/developers/','/feed-zh.xml','/weekly/','/en/weekly/']){let calls=0;const response=await worker.fetch(new Request('https://xiyu.news'+path,{method:'POST'}),{ASSETS:{fetch:()=>{calls++;throw Error('must not reach assets')}}});assert.ok([410,405].includes(response.status),path);assert.equal(calls,0);}});
test('English dated, event and fragment bookmarks go to the Chinese equivalent',async()=>{for(const [before,after] of [['/en/','/'],['/en/events/abc/','/'],['/2026/11/08/summary-en.html','/2026/11/08/summary-zh.html'],['/2026/11/08/summary-en/','/2026/11/08/summary-zh/'],['/editions/2026-11-08/en.html','/editions/2026-11-08/zh.html']]){const r=await run(before+'?source=friend');assert.equal(r.status,308);assert.equal(r.headers.get('Location'),'https://xiyu.news'+after+'?source=friend');}});
test('ordinary HTML and API reads always revalidate, no persistent Worker cache',async()=>{for(const path of ['/','/api/latest.json','/2026/11/08/summary-zh']){const r=await run(path);assert.equal(await r.text(),'fresh');assert.match(r.headers.get('Cache-Control'),/must-revalidate/);}});
test('old offline worker becomes a cleanup worker and does not intercept reads',async()=>{const r=await run('/service-worker.js');const js=await r.text();assert.match(js,/unregister/);assert.doesNotMatch(js,/addEventListener\('fetch'/);assert.equal(r.headers.get('Cache-Control'),'no-store');});

test("retired content URLs point to the current edition",async()=>{for(const path of ["/events/old/","/threads/old/","/entity/bitcoin/","/weekly/2026-11-01/","/en/threads/old/"]){const r=await run(path);assert.equal(r.status,308);assert.equal(new URL(r.headers.get("location")).pathname,"/");}});

test('one RSS feed remains public and retired feed APIs retain read redirects',async()=>{
 const reads=[];
 const env={ASSETS:{fetch:async req=>{reads.push(new URL(req.url).pathname);return new Response('<rss/>')}}};
 assert.equal((await worker.fetch(new Request('https://xiyu.news/feed.xml'),env)).status,200);
 assert.deepEqual(reads,['/feed.xml']);
 for(const path of ['/feed-en.xml','/feed-zh.xml']){
  const response=await worker.fetch(new Request('https://xiyu.news'+path),env);
  assert.equal(response.status,308);assert.equal(response.headers.get('location'),'https://xiyu.news/feed.xml');
 }
 const response=await worker.fetch(new Request('https://xiyu.news/api/events.json'),env);
 assert.equal(response.headers.get('location'),'https://xiyu.news/api/latest.json');
});

test('retired history returns 410',async()=>{for(const route of ['/history','/history/','/history.html','/en/history/'])assert.equal((await run(route)).status,410);});
