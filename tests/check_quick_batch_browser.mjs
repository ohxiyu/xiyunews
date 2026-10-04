// Browser simulations: no production writes, real authentication or AI calls.
import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const browser=await chromium.launch({headless:true});
const origin='https://xiyu.news';
const publicScript=await readFile(new URL('../docs/assets/js/quick-posts.js',import.meta.url),'utf8');
const publicCss=await readFile(new URL('../docs/assets/css/editorial-ui.css',import.meta.url),'utf8');
for(const width of [390,1280])for(const scheme of ['light','dark']) {
 const context=await browser.newContext({viewport:{width,height:width===390?844:900},colorScheme:scheme});
 let items=[],sha='a'.repeat(40),calls=0,writes=0,failAI=false,failSave=false,hidePublic=false;
 const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const sample=char=>({id:char.repeat(36),title:'新内容 '+char,body:'第一段事实。<script>安全文本</script>\n\n第二段保留关键时间、地点、人物。',
  category:'crypto-markets',tags:['crypto'],background:'背景内容',market_impact:'可能通过预期影响市场。',sources:[{title:'原文',url:'https://example.com/'+char}]});
 await context.route(origin+'/**',async route=>{
  const url=new URL(route.request().url());
  if(url.pathname==='/api/admin/state')return route.fulfill({json:{sha,items}});
  if(url.pathname==='/api/admin/generate'){
   calls++;if(failAI)return route.fulfill({status:502,json:{error:{message:'AI整理失败，原始输入保留，不自动重试。'}}});
   return route.fulfill({json:{model:'deepseek-flash',prompt_version:'quick-batch-v1',input_hash:'testhash',items:[sample('b'),sample('c')]}});
  }
  if(url.pathname==='/api/admin/batches'){
   if(failSave)return route.fulfill({status:409,json:{error:{message:'版本冲突，预览保留'}}});
   const body=route.request().postDataJSON();assert.equal(route.request().headers()['x-bmt-admin'],'1');writes++;
   const row={...body,type:'quick_batch',updated_at:'time-'+writes};items=items.filter(item=>item.id!==row.id).concat(row);
   sha=String(writes).repeat(40);return route.fulfill({json:{sha}});
  }
  if(url.pathname==='/api/admin/entry-state'){
   const data=route.request().postDataJSON();items[data.index].enabled=data.enabled;return route.fulfill({json:{sha}});
  }
  if(url.pathname==='/api/quick-posts.json')return route.fulfill({json:{revision:sha,items:hidePublic?[]:items.filter(row=>row.enabled).flatMap(row=>row.items.map((item,index)=>({...item,batch_id:row.id,batch_index:index,batch_size:row.items.length,date:row.date,anchor_id:row.anchor_id,updated_at:row.updated_at,image:'',url:item.sources[0]?.url||''})))}});
  if(url.pathname.startsWith('/editions/'))return route.fulfill({json:{items:[{id:'story-A',url:'https://example.com/original',title:{zh:'原有新闻 A'}},{id:'story-B',url:'https://example.com/second',title:{zh:'原有新闻 B'}}]}});
  if(url.pathname==='/test-stream')return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="zh"><meta charset="utf-8"><style>'+publicCss+'body{font:16px system-ui;margin:16px;background:'+(scheme==='dark'?'#171717;color:#eee':'#faf9f6;color:#222')+'}.daily-story-stream{max-width:720px;margin:auto}</style><div data-quick-post-status></div><div data-quick-post-unplaced></div><div class="day-stream"><section class="daily-day" data-date="'+day+'"><div class="daily-story-stream"><article class="digest-item" id="a" data-story-id="story-A"><h2><a href="https://example.com/original">原有新闻 A</a></h2><span data-score="9">9.0</span></article><article class="digest-item" id="b" data-story-id="story-B"><h2>原有新闻 B</h2></article></div></section></div><script>'+publicScript+'</script></html>'});
  const path=url.pathname==='/s/'?'s/index.html':url.pathname.slice(1);
  try{const content=(await readFile(new URL('../docs/'+path,import.meta.url),'utf8')).replace(/^---\n[\s\S]*?\n---\n/,'');return route.fulfill({body:content,contentType:path.endsWith('.js')?'application/javascript':path.endsWith('.css')?'text/css':'text/html'});}
  catch{return route.fulfill({status:404,body:''});}
 });
 const page=await context.newPage();const errors=[];page.on('pageerror',error=>errors.push(error.message));page.on('dialog',dialog=>dialog.accept());
 await page.goto(origin+'/s/');await page.waitForFunction(()=>!document.getElementById('generate').disabled);
 await page.locator('#body').fill('第一条材料\n---\n第二条材料');
 await page.locator('#save-draft').click();await page.waitForFunction(()=>document.getElementById('status').textContent.includes('草稿已保存'));
 assert.equal(calls,0);assert.equal(writes,1);
 await page.locator('#generate').click();await page.locator('#preview-1-title').waitFor();
 assert.equal(calls,1);assert.equal(await page.locator('#publish').isDisabled(),true);
 await page.locator('#preview-0-title').fill('人工修改的标题');
 await page.locator('#post-settings').evaluate(node=>node.open=true);
 await page.locator('#position').selectOption('story-A');
 await page.reload();await page.waitForFunction(()=>!document.getElementById('generate').disabled);
 await page.waitForFunction(()=>document.getElementById('position').value==='story-A');
 assert.equal(await page.locator('#preview-0-title').inputValue(),'人工修改的标题');assert.equal(calls,1);
 assert.equal(await page.locator('#reviewed').isChecked(),false);
 await page.locator('#reviewed').check();failSave=true;
 await page.locator('#publish').click();await page.waitForFunction(()=>document.getElementById('status').textContent.includes('版本冲突'));
 assert.equal(await page.locator('#preview-0-title').inputValue(),'人工修改的标题');
 failSave=false;await page.locator('#publish').click();await page.waitForFunction(()=>document.getElementById('status').textContent.includes('整组已上线'));
 assert.equal(calls,1);assert.equal(writes,2);
 assert.equal(items[0].anchor_id,'story-A');assert.equal(items[0].items.length,2);
 await page.locator('#preview-0-title').fill('再修改预览');await page.locator('#reviewed').check();hidePublic=true;
 await page.locator('#publish').click();await page.waitForFunction(()=>document.getElementById('status').textContent.includes('仍待核实'));
 hidePublic=false;
 await page.locator('#body').fill('原始材料修改');await page.locator('#reviewed').check();assert.equal(await page.locator('#publish').isDisabled(),true);
 failAI=true;await page.locator('#generate').click();await page.waitForFunction(()=>document.getElementById('generation-status').textContent.includes('AI整理失败'));
 assert.equal(await page.locator('#body').inputValue(),'原始材料修改');assert.equal(calls,2);
 if(process.env.BROWSER_EVIDENCE_DIR){await mkdir(process.env.BROWSER_EVIDENCE_DIR,{recursive:true});await page.screenshot({path:process.env.BROWSER_EVIDENCE_DIR+'/batch-admin-'+width+'-'+scheme+'.png',fullPage:true});}
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 // Frontend group is contiguous, does not change scores/ranks, has safe fields.
 await page.goto(origin+'/test-stream');await page.waitForFunction(()=>document.querySelectorAll('[data-quick-post]').length===2);
 assert.deepEqual(await page.locator('.daily-story-stream > *').evaluateAll(nodes=>nodes.map(node=>node.id||node.dataset.quickPost)),['a',items[0].items[0].id,items[0].items[1].id,'b']);
 assert.equal(await page.locator('[data-score]').innerText(),'9.0');assert.equal(await page.locator('[data-quick-post] script').count(),0);
 await page.locator('.quick-post-details').first().evaluate(node=>node.open=true);
 if(process.env.BROWSER_EVIDENCE_DIR)await page.screenshot({path:process.env.BROWSER_EVIDENCE_DIR+'/batch-stream-'+width+'-'+scheme+'.png',fullPage:true});
 // Loss of the anchor is explicit and the whole group goes last.
 await page.evaluate(()=>document.getElementById('a').remove());await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await page.waitForFunction(()=>document.querySelector('[data-quick-post] small')?.textContent.includes('暂置末尾'));
 assert.deepEqual(await page.locator('.daily-story-stream > *').evaluateAll(nodes=>nodes.map(node=>node.id||node.dataset.quickPost)),['b',items[0].items[0].id,items[0].items[1].id]);
 // Rebuilding the same date automatically re-reads; stable anchor follows story not rank.
 await page.evaluate(()=>{document.querySelector('.daily-story-stream').innerHTML='<article class="digest-item" id="b" data-story-id="story-B"><h2>B</h2></article><article class="digest-item" id="a" data-story-id="story-A"><h2>A</h2></article>';});
 await page.waitForFunction(()=>document.querySelectorAll('[data-quick-post]').length===2);
 assert.deepEqual(await page.locator('.daily-story-stream > *').evaluateAll(nodes=>nodes.map(node=>node.id||node.dataset.quickPost)),['b','a',items[0].items[0].id,items[0].items[1].id]);
 assert.deepEqual(errors,[]);console.log('PASS batch desk and stream',width,scheme);await context.close();
}
await browser.close();
