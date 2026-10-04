import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../docs/_worker.js',import.meta.url),'utf8');
const worker=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const env={ADMIN_ACCESS_ISSUER:'https://example.cloudflareaccess.com',ADMIN_ACCESS_AUD:'app-aud',
 ADMIN_ALLOWED_EMAIL:'owner@example.com',ADMIN_GITHUB_TOKEN:'server-only-test',
 ASSETS:{fetch:async()=>new Response('admin html')}};
const keys=await crypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['sign','verify']);
const jwk={...await crypto.subtle.exportKey('jwk',keys.publicKey),kid:'test'};
async function token(changes={},header={alg:'RS256',kid:'test'}) {
 const b64=value=>Buffer.from(JSON.stringify(value)).toString('base64url');
 const data=b64(header)+'.'+b64({iss:env.ADMIN_ACCESS_ISSUER,aud:[env.ADMIN_ACCESS_AUD],email:env.ADMIN_ALLOWED_EMAIL,iat:Math.floor(Date.now()/1000),exp:Math.floor(Date.now()/1000)+300,...changes});
 return data+'.'+Buffer.from(await crypto.subtle.sign('RSASSA-PKCS1-v1_5',keys.privateKey,new TextEncoder().encode(data))).toString('base64url');
}
let registry,sha,writes,dispatches;
const original=globalThis.fetch;

test('upstream redirects are rejected without a second credential-bearing request',async()=>{
 const previous=globalThis.fetch;
 for(const status of [301,302,303,307,308]) {
  let calls=0;
  globalThis.fetch=async(url,init)=>{
   assert.equal(init.redirect,'manual');
   if(url.endsWith('/cdn-cgi/access/certs')) return previous(url,init);
   calls++;
   return new Response('redirect',{status,headers:{Location:'https://untrusted.example/'}});
  };
  const response=await request('/api/admin/state');
  assert.equal(response.status,502);
  assert.equal((await response.json()).error.code,'upstream_redirect');
  assert.equal(calls,1);
 }
 globalThis.fetch=previous;
});

test('encoded management paths cannot fall through to public assets',async()=>{
 for(const path of ['/%73/','/s%2findex.html','/%61dmin/config.yml','/api/%61dmin/state']){
  assert.equal((await worker.handleRequest(new Request('https://xiyu.news'+path),env)).status,401);
 }
});
test('private source config uses authenticated same-origin API without writes',async()=>{
 const response=await request('/api/admin/source-config');
 assert.equal(response.status,200);
 assert.deepEqual(await response.json(),registry);
 assert.equal(writes,0);assert.equal(dispatches,0);
 const denied=await worker.handleRequest(new Request('https://xiyu.news/api/admin/source-config'),env);
 assert.equal(denied.status,401);
});
test('legacy editing keeps additional metadata and validates required fields',async()=>{
 const entry={type:'sponsored',enabled:true,url:'https://example.com/promo',title_zh:'广告',starts:'2026-09-10',expires:'2026-09-11',position:4,tags:[],sources:[]};
 let r=await request('/api/admin/legacy',{sha,index:0,entry});assert.equal(r.status,200);
 assert.equal(registry.items[0].extra,'preserved');assert.equal(registry.items[0].title_zh,'广告');
 r=await request('/api/admin/legacy',{sha,index:-1,entry:{...entry,expires:'2026-09-01'}});assert.equal(r.status,400);
 r=await request('/api/admin/legacy',{sha,index:-1,entry:{...entry,url:'javascript:alert(1)'}});assert.equal(r.status,400);
 r=await request('/api/admin/legacy',{sha,index:-1,entry:{...entry,type:'suppress',title_zh:''}});assert.equal(r.status,200);
});
test('valid content-addressed upload and identical retry, invalid MIME and size',async()=>{
 const previous=globalThis.fetch;let saved;
 globalThis.fetch=async(url,init)=>{
  if(url.includes('/contents/docs/assets/uploads/')){
   if(init.method==='PUT'){
    if(saved)return Response.json({},{status:422});
    saved=JSON.parse(init.body);assert.equal(saved.branch,'main');
    assert.match(url,/quick-[a-f0-9]{64}\.png$/);
    return Response.json({content:{sha:'a'},commit:{sha:'b'}});
   }
   return Response.json({content:saved.content});
  }
  return previous(url,init);
 };
 const input={mime:'image/png',data:'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6kZAAAAAASUVORK5CYII='};
 let r=await request('/api/admin/image',input);assert.equal(r.status,200);
 assert.match((await r.json()).path,/^\/assets\/uploads\/quick-/);
 assert.equal((await request('/api/admin/image',input)).status,200);
 for(const data of [{mime:'image/svg+xml',data:input.data},{mime:'image/jpeg',data:input.data},{mime:'image/png',data:'A'},{mime:'image/png',data:Buffer.alloc(1024*1024+1).toString('base64')}]) {
  assert.equal((await request('/api/admin/image',data)).status,400);
 }
});
test.beforeEach(()=>{
 registry={_readme:'keep',items:[{type:'sponsored',title_zh:'old',enabled:false,extra:'preserved'}]};sha='a'.repeat(40);writes=0;dispatches=0;
 globalThis.fetch=async(url,init={})=>{
  assert.equal(init.redirect,'manual', 'workerd requires manual redirect handling');
  if(url===env.ADMIN_ACCESS_ISSUER+'/cdn-cgi/access/certs')return Response.json({keys:[jwk]});
  assert.ok(url.startsWith('https://api.github.com/repos/ohxiyu/xiyunews/'));
  assert.equal(init.headers.Authorization,'Bearer server-only-test');
  if(url.includes('dispatches')){dispatches++;return new Response(null,{status:204});}
  if(init.method==='PUT'){
   const body=JSON.parse(init.body);assert.equal(body.branch,'main');assert.equal(body.sha,sha);
   registry=JSON.parse(Buffer.from(body.content,'base64').toString());writes++;sha=String(writes).repeat(40);
   return Response.json({content:{sha},commit:{sha:'f'.repeat(40)}});
  }
  return Response.json({sha,content:Buffer.from(JSON.stringify(registry)).toString('base64')});
 };
});
test.afterEach(()=>{globalThis.fetch=original;delete globalThis.caches;
 delete env.QUICK_POST_AI_ENABLED;delete env.QUICK_POST_AI_API_KEY;delete env.STATE;
 env.ASSETS={fetch:async()=>new Response('admin html')};});
async function request(path='/api/admin/state',body,overrides={}) {
 const headers={'Cf-Access-Jwt-Assertion':await token(),...(body?{'Origin':'https://xiyu.news','X-BMT-Admin':'1','Content-Type':'application/json'}:{}),...overrides};
 return worker.handleRequest(new Request('https://xiyu.news'+path,{method:body?'POST':'GET',headers,body:body?JSON.stringify(body):undefined}),env);
}
function post(changes={}){return {id:'12345678-1234-1234-1234-123456789abc',body:'正文 🚀\n\n第二段',date:'2026-09-10',category:'',url:'',image:'',enabled:true,pin:false,breaking:false,sha,...changes};}
test('fail closed before asset or cache reads including alternate admin URLs',async()=>{
 globalThis.caches={default:{match:()=>{throw Error('cache must not run');}}};
 for(const path of ['/s','/s/','/s/admin.js','/s/sources/','/admin/config.yml','/api/admin/state']){
  const r=await worker.handleRequest(new Request('https://xiyu.news'+path),env);
  assert.equal(r.status,401);assert.match(r.headers.get('Cache-Control'),/no-store/);assert.equal(r.headers.get('Access-Control-Allow-Origin'),null);
 }
 assert.equal((await worker.handleRequest(new Request('https://xiyu.news/s/'),{})).status,503);
});
test('JWT rejects wrong email, audience, issuer, expiry, future iat and algorithm',async()=>{
 for(const claim of [{email:'attacker@example.com'},{aud:['other']},{iss:'https://evil.example'},{exp:0},{iat:Date.now()/1000+1000}]){
  const r=await request('/api/admin/state',undefined,{'Cf-Access-Jwt-Assertion':await token(claim)});assert.equal(r.status,401);
 }
 const r=await request('/api/admin/state',undefined,{'Cf-Access-Jwt-Assertion':await token({}, {alg:'none',kid:'test'})});assert.equal(r.status,401);
});
test('JWT rejects tampering, header spoofing and direct pages.dev bypass',async()=>{
 const jwt=await token();const parts=jwt.split('.');parts[1]=Buffer.from(JSON.stringify({email:'owner@example.com'})).toString('base64url');
 assert.equal((await request('/api/admin/state',undefined,{'Cf-Access-Jwt-Assertion':parts.join('.')})).status,401);
 assert.equal((await worker.handleRequest(new Request('https://xiyu.news/s/',{headers:{'Cf-Access-Authenticated-User-Email':'owner@example.com'}}),env)).status,401);
 assert.equal((await worker.handleRequest(new Request('https://bmtnews.pages.dev/s/',{headers:{'Cf-Access-Jwt-Assertion':jwt}}),env)).status,403);
});
test('authenticated state and assets are private and old CMS redirects',async()=>{
 const r=await request();assert.equal(r.status,200);assert.equal((await r.json()).items[0].extra,'preserved');assert.match(r.headers.get('Cache-Control'),/private/);
 const asset=await request('/s/');assert.equal(await asset.text(),'admin html');assert.match(asset.headers.get('Content-Security-Policy'),/frame-ancestors 'none'/);
 const legacy=await request('/admin/');assert.equal(legacy.headers.get('Location'),'/s/');
 assert.equal((await request('/admin/config.yml')).status,404);
});
test('body-only post saves without mutating legacy data; same retry is idempotent',async()=>{
 const input=post();let r=await request('/api/admin/posts',input);assert.equal(r.status,200);
 assert.equal(registry._readme,'keep');assert.equal(registry.items[0].extra,'preserved');
 assert.equal(registry.items[1].body,input.body);assert.equal(registry.items[1].url,'');
 assert.equal((await request('/api/admin/posts',input)).status,200);assert.equal(writes,1);
});
test('stale revision never overwrites, including a changed same-ID retry',async()=>{
 const input=post();await request('/api/admin/posts',input);
 const r=await request('/api/admin/posts',{...input,body:'changed'});assert.equal(r.status,409);assert.equal(writes,1);
});
test('CSRF and non-JSON writes rejected',async()=>{
 for(const headers of [{'Origin':'https://evil.example'},{'X-BMT-Admin':''},{'Content-Type':'text/plain'}]){
  assert.equal((await request('/api/admin/posts',post(),headers)).status,403);
 }
 assert.equal(writes,0);
});
test('invalid post, dates, script URL and image path rejected',async()=>{
 for(const changes of [{body:''},{body:'x'.repeat(10001)},{date:'2026-02-30'},{url:'javascript:alert(1)'},{url:'https://user:pass@example.com'},{image:'/private'},{pin:'true'},{category:'bad'}]){
  assert.equal((await request('/api/admin/posts',post(changes))).status,400);
 }
 assert.equal(writes,0);
});
test('draft and enable state preserve all unrelated fields',async()=>{
 await request('/api/admin/posts',post({enabled:false}));
 assert.equal(registry.items[1].enabled,false);
 const r=await request('/api/admin/entry-state',{sha,index:1,enabled:true});
 assert.equal(r.status,200);assert.equal(registry.items[1].enabled,true);assert.equal(registry.items[0].extra,'preserved');
});
test('source request uses only fixed existing workflow and no production config write',async()=>{
 const r=await request('/api/admin/sources',{operation:'pause',source_type:'rss',source_key:'rss|https://example.com/',reason:'test',enabled:'false',category:'unchanged'});
 assert.equal(r.status,202);assert.equal(dispatches,1);assert.equal(writes,0);
});
test('bounded request rejects oversized bodies and invalid JSON',async()=>{
 assert.equal((await request('/api/admin/posts',{body:'x'.repeat(110000)})).status,413);
});
test('unknown admin API and missing writer token are explicit failures',async()=>{
 assert.equal((await request('/api/admin/nope',{})).status,404);
 const r=await worker.handleRequest(new Request('https://xiyu.news/api/admin/state',{headers:{'Cf-Access-Jwt-Assertion':await token()}}),{...env,ADMIN_GITHUB_TOKEN:''});
 assert.equal(r.status,503);
});

test('live public stream sees publish edit disable immediately without assets or cache', async()=>{
 const date=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 globalThis.caches={default:{match:()=>{throw Error('must bypass cache');}}};
 const live=async()=>{
  const response=await worker.handleRequest(new Request('https://xiyu.news/api/quick-posts.json'),env);
  assert.equal(response.status,200);assert.equal(response.headers.get('Cache-Control'),'no-store');
  return response.json();
 };
 await request('/api/admin/posts',post({date,position:2}));
 let payload=await live();assert.equal(payload.items[0].position,2);assert.equal(payload.revision,sha);
 assert.equal(payload.items[0].request_hash,undefined);assert.equal(payload.items[0].enabled,undefined);
 await request('/api/admin/posts',post({date,position:1,body:'edited'}));
 payload=await live();assert.equal(payload.items[0].body,'edited');assert.equal(payload.items[0].position,1);
 await request('/api/admin/entry-state',{sha,index:1,enabled:false});
 assert.deepEqual((await live()).items,[]);
});

test('explicit history dates are supported but future and drafts never become public', async()=>{
 registry.items=[post({type:'quick_post',date:'2020-01-01',position:0}),post({type:'quick_post',id:'b'.repeat(36),date:'2099-01-01'}),post({type:'quick_post',id:'c'.repeat(36),enabled:false,date:'2020-01-01'})];
 const response=await worker.handleRequest(new Request('https://xiyu.news/api/quick-posts.json?date=2020-01-01&date=2099-01-01'),env);
 assert.equal((await response.json()).items.length,1);
 assert.equal((await worker.handleRequest(new Request('https://xiyu.news/api/quick-posts.json?date=2026-02-30'),env)).status,400);
});

test('live read errors fail explicitly instead of returning stale generated data', async()=>{
 globalThis.fetch=async()=>new Response(null,{status:403});
 const response=await worker.handleRequest(new Request('https://xiyu.news/api/quick-posts.json'),env);
 assert.equal(response.status,503);assert.equal(response.headers.get('Cache-Control'),'no-store');
 assert.equal((await response.json()).error.code,'quick_posts_unavailable');
});

test('positions reject negative fractional oversized and non-number values', async()=>{
 for(const position of [-1,1.5,1001,'2',true])assert.equal((await request('/api/admin/posts',post({position}))).status,400);
 for(const position of [null,0,1,1000])assert.equal((await request('/api/admin/posts',post({position}))).status,200);
});

test('uploaded image is readable immediately and content hash is verified', async()=>{
 const bytes=Buffer.from([137,80,78,71,13,10,26,10]);
 const hash=Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex');
 globalThis.fetch=async(url,init)=>{assert.equal(init.cache,'no-store');return Response.json({content:bytes.toString('base64')});};
 const response=await worker.handleRequest(new Request('https://xiyu.news/assets/uploads/quick-'+hash+'.png'),env);
 assert.equal(response.status,200);assert.equal(response.headers.get('Content-Type'),'image/png');
 assert.deepEqual(Buffer.from(await response.arrayBuffer()),bytes);
 assert.equal((await worker.handleRequest(new Request('https://xiyu.news/assets/uploads/quick-'+'a'.repeat(64)+'.png'),env)).status,503);
});
function batchInput(changes={}) {
 return {...post(),body:undefined,raw:'第一条原始材料。\n---\n第二条原始材料。',reviewed:true,anchor_id:null,
  items:['b','c'].map((char,index)=>({id:char.repeat(36),title:'新闻'+index,body:'正文\n\n第二段',category:'crypto-markets',
  background:'背景',market_impact:'可能影响',tags:['crypto'],sources:[]})),...changes};
}
function mockAI(raw, {status=200,finish='stop',content,model='deepseek-flash',wait}={}) {
 const previous=globalThis.fetch;let calls=0;const requests=[];const cache=new Map();
 env.QUICK_POST_AI_ENABLED='true';env.QUICK_POST_AI_API_KEY='fake-test-key';
 env.STATE={get:async key=>cache.get(key),put:async(key,value)=>cache.set(key,JSON.parse(value))};
 globalThis.fetch=async(url,init)=>{
  if(url.endsWith('/contents/data/config.github.json?ref=main'))return Response.json({content:Buffer.from(JSON.stringify({ai:{provider:'deepseek',base_url:'https://api.deepseek.com',model}})).toString('base64')});
  if(url==='https://api.deepseek.com/chat/completions'){
   calls++;assert.equal(init.redirect,'manual');assert.equal(init.headers.Authorization,'Bearer fake-test-key');
   requests.push(JSON.parse(init.body));if(wait)await wait;
   return Response.json({choices:[{finish_reason:finish,message:{content:content??JSON.stringify({items:raw.split(/\n---\n/).map(source=>({source_text:source,title:'新闻标题',body:source,category:'crypto-markets',background:'',market_impact:'',tags:['crypto'],sources:[{title:'AI invented',url:'https://invented.example/'}]}))})}}],usage:{prompt_tokens:100,completion_tokens:40,total_tokens:140}}, {status});
  }
  return previous(url,init);
 };
 return {requests,cache,calls:()=>calls};
}
test('AI missing configuration fails closed without model or registry writes',async()=>{
 const r=await request('/api/admin/generate',{raw:'配置缺失'});
 assert.equal(r.status,503);assert.equal((await r.json()).error.code,'ai_not_configured');
 assert.equal(writes,0);assert.equal(dispatches,0);
});
test('AI only sees new input; exact-input cache and grounded input links',async()=>{
 const raw='材料 https://example.com/source\n---\n另一条材料。';
 const ai=mockAI(raw);
 let r=await request('/api/admin/generate',{raw});assert.equal(r.status,200);
 const first=await r.json();assert.equal(first.items.length,2);assert.equal(first.cache_hit,false);
 assert.deepEqual(first.items[0].sources,[{title:'原文 1',url:'https://example.com/source'}]);
 assert.deepEqual(first.items[1].sources,[]);
 assert.deepEqual(JSON.parse(ai.requests[0].messages[1].content),{raw});
 assert.equal(ai.requests[0].thinking.type,'disabled');
 assert.equal(ai.requests[0].model,'deepseek-flash');
 assert.equal(ai.requests[0].response_format.type,'json_object');
 assert.equal(ai.calls(),1);assert.equal(writes,0);assert.equal(dispatches,0);
 r=await request('/api/admin/generate',{raw});const second=await r.json();
 assert.equal(second.cache_hit,true);assert.equal(ai.calls(),1);assert.equal(second.expires_at,undefined);
 const changed=raw+' 新进展';mockAI(changed);assert.equal((await request('/api/admin/generate',{raw:changed})).status,200);
 assert.equal(ai.calls(),1);
});
test('AI refuses omission, reordering, malformed JSON, truncation, errors and redirects without retries',async()=>{
 for(const [n,options] of [
  [0,{content:'not JSON'}],[1,{finish:'length'}],[2,{status:429}],[3,{status:503}],[4,{status:302}],
  [5,{content:JSON.stringify({items:[{source_text:'遗漏第一条。',title:'x',body:'x',category:'',tags:[]}]})}],
  [6,{content:JSON.stringify({items:[{source_text:'第一条6',title:'x',body:'x',category:'not-real',tags:[],sources:[]}]})}],
 ]) {
  const raw='第一条'+n+'\n---\n第二条'+n;const ai=mockAI(raw,options);
  const r=await request('/api/admin/generate',{raw});assert.equal(r.status,502);
  assert.doesNotMatch(await r.text(),/fake-test-key|not JSON|AI invented/);
  assert.equal(ai.calls(),1);assert.equal(writes,0);assert.equal(ai.cache.size,0);
 }
 assert.throws(()=>worker.validateQuickGeneration({items:[]},'材料'));
 assert.throws(()=>worker.validateQuickGeneration({items:[{source_text:'第二条'}]},'第一条\n---\n第二条'));
});
test('concurrent identical generation shares one provider call',async()=>{
 let release;const raw='并行材料';const ai=mockAI(raw,{wait:new Promise(resolve=>release=resolve)});
 const a=request('/api/admin/generate',{raw}),b=request('/api/admin/generate',{raw});
 while(!ai.calls())await new Promise(resolve=>setTimeout(resolve,1));
 release();const results=await Promise.all([a,b]);
 assert.ok(results.every(r=>r.status===200));assert.equal(ai.calls(),1);
});
test('provider timeout is sanitized and two distinct in-flight previews bound concurrency',async()=>{
 let release;const pending=new Promise(resolve=>release=resolve);
 const ai=mockAI('并发限额一',{wait:pending});
 const a=request('/api/admin/generate',{raw:'并发限额一'});
 const b=request('/api/admin/generate',{raw:'并发限额二'});
 while(ai.calls()<2)await new Promise(resolve=>setTimeout(resolve,1));
 assert.equal((await request('/api/admin/generate',{raw:'并发限额三'})).status,429);
 release();await Promise.all([a,b]);assert.equal(ai.calls(),2);
 const previous=globalThis.fetch;let attempts=0;
 globalThis.fetch=async(url,init)=>{if(url==='https://api.deepseek.com/chat/completions'){attempts++;throw new DOMException('secret fake-test-key upstream','TimeoutError');}return previous(url,init);};
 const timeout=await request('/api/admin/generate',{raw:'真实超时模拟材料'});
 assert.equal(timeout.status,502);assert.doesNotMatch(await timeout.text(),/fake-test-key|secret/);assert.equal(attempts,1);
});
test('batch saves once, retains legacy records, provenance and idempotent retry',async()=>{
 const raw='整组材料';const ai=mockAI(raw);const preview=await (await request('/api/admin/generate',{raw})).json();
 const input=batchInput({raw,items:preview.items,...{model:preview.model,prompt_version:preview.prompt_version,input_hash:preview.input_hash}});
 let r=await request('/api/admin/batches',input);assert.equal(r.status,200);
 assert.equal(writes,1);assert.equal(dispatches,0);assert.equal(ai.calls(),1);
 assert.equal(registry.items[0].extra,'preserved');assert.equal(registry.items[1].generation.edited,false);
 r=await request('/api/admin/batches',input);assert.equal(r.status,200);assert.equal(writes,1);
 r=await request('/api/admin/batches',{...input,items:input.items.map(row=>({...row,body:'改了'}))});
 assert.equal(r.status,409);assert.equal(writes,1);
});
test('batch requires review, valid unique IDs, unchanged revision and existing stable anchor',async()=>{
 const input=batchInput();
 for(const changes of [{reviewed:false},{anchor_id:'<bad>'},{items:[]},{items:[input.items[0],input.items[0]]},
  {items:[{...input.items[0],id:input.id}]},{items:[{...input.items[0],sources:[{title:'bad',url:'javascript:bad'}]}]}]){
  assert.equal((await request('/api/admin/batches',{...input,...changes})).status,400);
 }
 env.ASSETS={fetch:async()=>Response.json({items:[{id:'story-42'}]})};
 assert.equal((await request('/api/admin/batches',{...input,anchor_id:'missing'})).status,409);
 assert.equal((await request('/api/admin/batches',{...input,anchor_id:'story-42'})).status,200);
 assert.equal(registry.items[1].anchor_id,'story-42');assert.equal(writes,1);assert.equal(dispatches,0);
 assert.equal((await request('/api/admin/entry-state',{sha,index:1,enabled:true})).status,400);
 assert.equal((await request('/api/admin/entry-state',{sha,index:1,enabled:false})).status,200);
 assert.equal(registry.items[1].enabled,false);
});
test('root or child ID collision never overwrites another batch or single',async()=>{
 const input=batchInput();assert.equal((await request('/api/admin/batches',input)).status,200);
 assert.equal((await request('/api/admin/batches',batchInput({id:'d'.repeat(36),items:input.items}))).status,409);
 assert.equal(writes,1);
 assert.equal((await request('/api/admin/posts',post({id:'e'.repeat(36)}))).status,200);
 assert.equal((await request('/api/admin/batches',batchInput({id:'e'.repeat(36),items:[{...input.items[0],id:'f'.repeat(36)}]}))).status,409);
});
test('raw-only batch draft is supported; public output is ordered whitelist and excludes invalid groups',()=>{
 const input=batchInput({type:'quick_batch',date:'2026-09-10',created_at:'time',updated_at:'update',note:'private',generation:{model:'private'}});
 const rows=worker.publicQuickPosts({items:[input]},'2026-09-10');
 assert.deepEqual(rows.map(row=>row.batch_index),[0,1]);assert.equal(rows[0].anchor_id,null);
 assert.equal(rows[0].title,'新闻0');assert.equal(rows[0].batch_size,2);
 for(const key of ['raw','note','generation','request_hash','enabled','score'])assert.equal(rows[0][key],undefined);
 for(const changes of [{enabled:false},{date:'2026-09-11'},{items:[{...input.items[0],title:''}]}]){
  assert.deepEqual(worker.publicQuickPosts({items:[{...input,...changes}]},'2026-09-10'),[]);
 }
 assert.equal(worker.validateQuickBatch({...input,enabled:false,items:[]}).items.length,0);
});
test('AI prompt cache changes with model and invalid cache is rejected',async()=>{
 const raw='模型切换的独立材料';const ai=mockAI(raw);
 await request('/api/admin/generate',{raw});assert.equal(ai.calls(),1);
 const second=mockAI(raw,{model:'deepseek-other'});
 const r=await request('/api/admin/generate',{raw});assert.equal((await r.json()).model,'deepseek-other');
 assert.equal(second.calls(),1);
 const badRaw='缓存损坏的独立材料';const third=mockAI(badRaw);
 const good=await (await request('/api/admin/generate',{raw:badRaw})).json();
 third.cache.set('quickpost-preview:'+good.input_hash,{...good,items:[{title:'invalid'}]});
 // A cached malformed payload must never become a preview.
 const retry=await (await request('/api/admin/generate',{raw:badRaw})).json();
 assert.equal(retry.items[0].body,badRaw);assert.equal(third.calls(),2);
});
