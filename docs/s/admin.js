(() => {
'use strict';
const $ = id => document.getElementById(id);
const fields = ['body','url','date','category','breaking','pin'];
const key = 'bmt-quick-post-draft-v1';
let sha = '', items = [], id = crypto.randomUUID(), image = '', dirty = false, busy = false;
let previewItems = [], generation = {}, generatedRaw = '', legacyPost = false;
let liveIds = new Set();
let legacyIndex = -1;
const legacyLabels = {type:'操作类型（editorial / sponsored / suppress）',url:'原文链接',title_zh:'中文标题',title_en:'英文标题',summary_zh:'中文正文',summary_en:'英文正文',date:'刊期日期',starts:'开始日期',expires:'结束日期（广告必填）',position:'广告位置（1–20）',label:'来源名称',category:'分类',background_zh:'背景',background_en:'Background',market_impact_zh:'市场影响',market_impact_en:'Market impact',community_discussion_zh:'讨论',community_discussion_en:'Discussion',note:'内部备注',tags:'标签（每行一个）',sources:'参考链接（每行：标题 | URL）'};
for (const [name,title] of Object.entries(legacyLabels)) {
 const label=document.createElement('label');label.textContent=title;
 const field=document.createElement(/summary|background|impact|discussion|sources|tags/.test(name)?'textarea':'input');
 field.id='legacy-'+name;field.maxLength=10000;label.append(field);$('legacy-fields').append(label);
}
for(const name of ['enabled','official']) {
 const label=document.createElement('label');const field=document.createElement('input');field.type='checkbox';field.id='legacy-'+name;
 label.append(field,document.createTextNode(name==='enabled'?'启用':'官方或第一手来源'));$('legacy-fields').append(label);
}
function fillLegacy(entry={},index=-1) {
 legacyIndex=index;
 for(const name of Object.keys(legacyLabels)) {
  $('legacy-'+name).value=name==='tags'?(entry.tags||[]).join('\n'):name==='sources'?(entry.sources||[]).map(s=>(s.title||'')+' | '+s.url).join('\n'):entry[name]??(name==='type'?'editorial':'');
 }
 $('legacy-enabled').checked=entry.enabled!==false;$('legacy-official').checked=!!entry.official;
}
function today() { return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()); }
function value(enabled) {
 const shared={id,date:$('date').value,breaking:$('breaking').checked,pin:$('pin').checked,image,enabled,sha};
 return legacyPost?{...shared,type:'quick_post',body:$('body').value,url:$('url').value,category:$('category').value,position:$('position').value===''?null:Number($('position').value)}:
  {...shared,type:'quick_batch',raw:$('body').value,anchor_id:$('position').value||null,items:previewItems,
   ...generation,reviewed:$('reviewed').checked};
}
function remember() { dirty=true;try{sessionStorage.setItem(key,JSON.stringify({...value(false),generatedRaw}));}catch{} }
function fill(post) {
 legacyPost=post.type==='quick_post'||(!post.type&&typeof post.body==='string');
 id=post.id||crypto.randomUUID();image=post.image||'';
 fields.forEach(f=>{if(['breaking','pin'].includes(f))$(f).checked=!!post[f];else $(f).value=(f==='body'&&!legacyPost?post.raw:post[f])||(f==='date'?today():'');});
 previewItems=Array.isArray(post.items)?structuredClone(post.items):[];generation=post.generation||{};
 generatedRaw=post.generatedRaw||(previewItems.length?$('body').value:'');
 for(const name of ['model','prompt_version','input_hash'])if(post[name])generation[name]=post[name];
 $('reviewed').checked=false;$('legacy-post-fields').hidden=!legacyPost;
 $('image').value='';$('image-state').textContent=image?'已选择配图':'';$('remove-image').hidden=!image;
 renderPreview();loadPositions(legacyPost?post.position??null:post.anchor_id||null);
 $('generation-status').textContent=legacyPost?'旧单条模式：直接编辑保存，或新建一组使用AI整理。':'生成只做预览，核对后再整组发布。';
}
function renderPreview() {
 $('preview-section').hidden=legacyPost||!previewItems.length;$('preview-items').replaceChildren();
 previewItems.forEach((item,index)=>{
  const article=document.createElement('article');article.className='preview-item';
  const controls=document.createElement('div');controls.className='actions';
  const heading=document.createElement('h3');heading.textContent='内容 '+(index+1);controls.append(heading);
  const remove=document.createElement('button');remove.type='button';remove.textContent='移除';remove.onclick=()=>{if(busy)return;previewItems.splice(index,1);$('reviewed').checked=false;renderPreview();remember();lock(false);};controls.append(remove);
  if(index){const merge=document.createElement('button');merge.type='button';merge.textContent='合并到上一条';merge.onclick=()=>{if(busy)return;const previous=previewItems[index-1];previous.body+='\n\n'+item.body;previous.background=[previous.background,item.background].filter(Boolean).join('\n\n');previous.market_impact=[previous.market_impact,item.market_impact].filter(Boolean).join('\n\n');previous.tags=[...new Set([...previous.tags,...item.tags])].slice(0,10);previous.sources=[...previous.sources,...item.sources].slice(0,10);previewItems.splice(index,1);$('reviewed').checked=false;renderPreview();remember();lock(false);};controls.append(merge);}
  article.append(controls);
  const extra=document.createElement('details');const summary=document.createElement('summary');summary.textContent='分类、标签、背景、影响与来源';extra.append(summary);
  const labels={title:'标题',body:'正文',category:'分类',tags:'标签（逗号分隔）',background:'背景',market_impact:'影响分析',sources:'参考链接（每行：标题 | URL）'};
  for(const [field,labelText]of Object.entries(labels)){
   const label=document.createElement('label');label.textContent=labelText;
   const fieldNode=document.createElement(field==='category'?'select':['body','background','market_impact','sources'].includes(field)?'textarea':'input');fieldNode.dataset.field=field;fieldNode.id='preview-'+index+'-'+field;
   if(field==='category')for(const option of $('category').options)fieldNode.append(option.cloneNode(true));
   fieldNode.value=field==='tags'?(item.tags||[]).join(', '):field==='sources'?(item.sources||[]).map(row=>row.title+' | '+row.url).join('\n'):item[field]||'';
   fieldNode.required=['title','body'].includes(field);fieldNode.maxLength=field==='title'?200:['background','market_impact'].includes(field)?2000:10000;
   if(fieldNode.tagName==='TEXTAREA')fieldNode.rows=field==='body'?5:3;
   fieldNode.oninput=()=>{item[field]=field==='tags'?fieldNode.value.split(/[,，]/).map(value=>value.trim()).filter(Boolean):field==='sources'?fieldNode.value.split('\n').filter(value=>value.trim()).map(value=>{const at=value.lastIndexOf('|');return{title:at<0?'原文':value.slice(0,at).trim(),url:(at<0?value:value.slice(at+1)).trim()};}):fieldNode.value;$('reviewed').checked=false;remember();lock(false);};
   label.append(fieldNode);(['title','body'].includes(field)?article:extra).append(label);
  }
  article.append(extra);$('preview-items').append(article);
 });
}
let positionRequest=0;
async function loadPositions(selected=null) {
 if(legacyPost&&selected===0)selected=null;
 const run=++positionRequest, day=$('date').value;
 const option=(value,text)=>{const node=document.createElement('option');node.value=value;node.textContent=text;return node;};
 $('position').replaceChildren(option('','刊期正文最前'));
 // Preserve an existing position even when the edition request fails.
 if(selected!==null){$('position').append(option(String(selected),legacyPost?'第 '+selected+' 条之后':'原新闻位置（待核验）'));$('position').value=String(selected);}
 $('position-state').textContent='正在加载刊期位置…';
 try {
  const response=await fetch('/editions/'+encodeURIComponent(day)+'/edition.json',{cache:'no-store'});
  if(!response.ok)throw Error('unavailable');
  const edition=await response.json();if(!Array.isArray(edition.items))throw Error('invalid');
  if(run!==positionRequest)return;
  const options=[option('','刊期正文最前')];
  edition.items.forEach((item,index)=>{if(legacyPost||item.id)options.push(option(legacyPost?String(index+1):item.id,'第 '+(index+1)+' 条之后 · '+(item.title?.zh||item.title?.en||'新闻').slice(0,50)));});
  if(selected!==null&&!options.some(node=>node.value===String(selected)))options.push(option(String(selected),'原锚点已变更，请重新选择'));
  $('position').replaceChildren(...options);$('position').value=selected===null?'':String(selected);
  $('position-state').textContent='整组绑定所选新闻，组内不排序；锚点消失时不冒充原位置。';
 }catch{if(run===positionRequest)$('position-state').textContent='刊期位置暂不可用；保留原位置。新内容可放在最前，刷新后重试。';}
}
function status(message) { $('status').textContent=message; }
function lock(on) {
 busy=on;
 document.querySelectorAll('form input, form textarea, form select, form button').forEach(field=>{field.disabled=on||!sha;});
 $('publish').disabled=on||!sha||(!legacyPost&&(!previewItems.length||!$('reviewed').checked||(generatedRaw&&generatedRaw!==$('body').value)));
 $('generate').disabled=on||!sha||legacyPost;
}
async function api(path, data) {
 const response=await fetch('/api/admin/'+path,{method:data?'POST':'GET',credentials:'same-origin',cache:'no-store',
   headers:data?{'Content-Type':'application/json','X-BMT-Admin':'1'}:{},body:data?JSON.stringify(data):undefined});
 if(!response.headers.get('content-type')?.includes('application/json')) throw Error('登录已过期，请重新打开 /s/ 完成邮箱验证；当前标签页草稿仍保留。');
 const result=await response.json(); if(!response.ok) throw Error(result.error?.message||'操作失败，请稍后重试。'); return result;
}
async function refresh() {
 const state=await api('state'); sha=state.sha; items=state.items;
 let published=[];
 let verified=false;
 try { const dates=[...new Set(items.filter(e=>['quick_post','quick_batch'].includes(e.type)).map(e=>e.date))];
  for(let offset=0;offset<dates.length;offset+=10){const query=dates.slice(offset,offset+10).map(day=>'date='+encodeURIComponent(day)).join('&');const r=await fetch('/api/quick-posts.json?'+query,{cache:'no-store'});if(!r.ok)throw Error('unavailable');const payload=await r.json();if(!payload.revision||!Array.isArray(payload.items))throw Error('unverified');published.push(...payload.items);}
  verified=true;
 } catch {published=[];}
 $('entries').replaceChildren();
 liveIds = new Set();
 items.slice().reverse().forEach((entry, reversed)=>{
   const index=items.length-1-reversed, node=document.createElement('article'); node.className='entry';
   const meta=document.createElement('small');
   const live=entry.type==='quick_batch'?entry.items?.length>0&&entry.items.every(row=>published.some(p=>p.batch_id===entry.id&&p.id===row.id&&p.updated_at===entry.updated_at)):entry.type==='quick_post'&&published.some(p=>p.id===entry.id&&p.updated_at===entry.updated_at);
   if(live&&entry.enabled!==false)liveIds.add(entry.id);
   meta.textContent=[entry.type==='quick_batch'?'一组 · '+entry.items.length+'条':entry.type==='quick_post'?'旧单条':entry.type,entry.date||entry.starts||'未指定日期',
     entry.enabled===false?'草稿 / 停用':live?'已上线':entry.date>today()?'待刊期到达':verified?'已保存（未出现在公开流）':'已保存（待核实上线）'].join(' · ');
   const content=document.createElement('p');content.textContent=entry.type==='quick_batch'?entry.items.map((row,index)=>(index+1)+'. '+row.title).join('\n')||entry.raw:entry.body||entry.title_zh||entry.url||'编辑记录';
   const actions=document.createElement('div');actions.className='actions';
   if(['quick_post','quick_batch'].includes(entry.type)) { const edit=document.createElement('button'); edit.textContent=entry.type==='quick_batch'?'编辑整组':'编辑';edit.onclick=()=>{if(busy)return;if(dirty&&!confirm('替换当前未提交草稿？'))return;fill(entry);remember();lock(false);$('body').focus();};actions.append(edit); }
   else { const edit=document.createElement('button');edit.textContent='编辑';edit.onclick=()=>{if(busy)return;fillLegacy(entry,index);$('legacy-panel').open=true;$('legacy-panel').scrollIntoView({behavior:'smooth'});};actions.append(edit); }
   const toggle=document.createElement('button');toggle.textContent=entry.enabled===false?'启用':'停用';
   if(entry.type==='quick_batch'&&entry.enabled===false){toggle.textContent='核对并发布';toggle.onclick=()=>{if(busy)return;fill(entry);remember();lock(false);$('preview-section').scrollIntoView({behavior:'smooth'});};}
   else
   toggle.onclick=async()=>{if(busy||!confirm(toggle.textContent+'这条记录？'))return;lock(true);try{await api('entry-state',{sha,index,enabled:entry.enabled===false});await refresh();status(entry.type==='quick_post'?'状态已保存，实时核验结果见列表。':'已保存状态，等待自动发布。');}catch(e){status(e.message);}finally{lock(false);}};
   actions.append(toggle);node.append(meta,content,actions);$('entries').append(node);
 });
 $('body').disabled=false;lock(false);
}
async function save(enabled) {
 if(busy)return;
 if(!$('post-form').reportValidity())return;
 lock(true);remember();status('正在保存…');
 if(!legacyPost&&enabled&&(!previewItems.length||!$('reviewed').checked)){status('请先核对预览并勾选确认。');lock(false);return;}
 try {const result=await api(legacyPost?'posts':'batches',value(enabled));sha=result.sha;dirty=false;try{sessionStorage.removeItem(key);}catch{}await refresh();const live=enabled&&liveIds.has(id);status(!enabled?'草稿已保存，未发布。':live?'已核对公开内容，整组已上线。':'已保存，公开内容仍待核实；不要重复发布。');}
 catch(e){status(e.message);}finally{lock(false);}
}
$('date').value=today();
loadPositions();
$('date').addEventListener('change',()=>{loadPositions();remember();});
$('position').addEventListener('change',remember);
fillLegacy();
$('legacy-new').onclick=()=>{if(!busy)fillLegacy();};
$('legacy-form').onsubmit=async e=>{
 e.preventDefault();if(busy)return;lock(true);
 try {
  const entry=Object.fromEntries(Object.keys(legacyLabels).map(name=>[name,$('legacy-'+name).value]));
  entry.enabled=$('legacy-enabled').checked;entry.official=$('legacy-official').checked;
  entry.position=entry.position?Number(entry.position):null;
  entry.tags=entry.tags.split('\n').map(s=>s.trim()).filter(Boolean);
  entry.sources=entry.sources.split('\n').filter(s=>s.trim()).map(s=>{const i=s.lastIndexOf('|');return{title:i<0?'':s.slice(0,i).trim(),url:(i<0?s:s.slice(i+1)).trim()};});
  const result=await api('legacy',{sha,index:legacyIndex,entry});status(result.message);await refresh();
 }catch(error){status(error.message);}finally{lock(false);}
};
try{const saved=JSON.parse(sessionStorage.getItem(key)||'null');if(saved){fill(saved);dirty=true;}}catch{}
fields.forEach(f=>$(f).addEventListener('input',remember));
 $('body').addEventListener('input',()=>{$('reviewed').checked=false;if(generatedRaw&&generatedRaw!==$('body').value)$('generation-status').textContent='原始输入已改变，请重新生成预览；旧预览不会自动发布。';remember();lock(false);});
 $('reviewed').addEventListener('change',()=>lock(false));
 $('generate').onclick=async()=>{
  if(busy||legacyPost)return;const raw=$('body').value;if(!raw.trim()){status('请先粘贴内容。');return;}
  if(previewItems.length&&!confirm('重新生成会替换当前预览中的手动修改，继续？'))return;
  lock(true);remember();$('generation-status').textContent='正在整理，仅处理这组新内容…';
  try{const result=await api('generate',{raw});previewItems=result.items.map(row=>({...row,id:crypto.randomUUID()}));generation={model:result.model,prompt_version:result.prompt_version,input_hash:result.input_hash};generatedRaw=raw;$('reviewed').checked=false;renderPreview();remember();$('generation-status').textContent=(result.cache_hit?'已复用生成结果':'已生成预览')+' · '+previewItems.length+'条 · '+result.model+'。请核对事实后发布。';}
  catch(error){$('generation-status').textContent=error.message;}finally{lock(false);}
 };
 $('add-item').onclick=()=>{if(busy||previewItems.length>=8)return;previewItems.push({id:crypto.randomUUID(),title:'',body:'',background:'',market_impact:'',category:'',tags:[],sources:[]});$('reviewed').checked=false;renderPreview();remember();lock(false);};
$('post-form').onsubmit=e=>{e.preventDefault();save(true);};
$('save-draft').onclick=()=>save(false);
$('new-post').onclick=()=>{if(busy||(dirty&&!confirm('放弃当前未提交草稿，开始新建？')))return;fill({});lock(false);dirty=false;try{sessionStorage.removeItem(key);}catch{} status('新建内容');$('body').focus();};
$('refresh').onclick=()=>{if(busy)return;refresh().then(()=>status('列表已刷新；当前输入未改变。')).catch(e=>status(e.message));};
$('remove-image').onclick=()=>{if(busy)return;image='';$('image').value='';$('image-state').textContent='';$('remove-image').hidden=true;remember();};
$('image').onchange=async()=>{
 const file=$('image').files[0];if(!file)return;
 if(file.size>1024*1024||!['image/png','image/jpeg','image/webp'].includes(file.type)){status('请选择不超过 1 MB 的 PNG、JPEG 或 WebP 图片。');$('image').value='';return;}
 lock(true);status('上传图片…');
 try {const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);});
 const result=await api('image',{mime:file.type,data});image=result.path;$('image-state').textContent='配图已保存，可立即读取';$('remove-image').hidden=false;remember();status('配图已保存，请继续保存正文。');}
 catch(e){status(e.message);}finally{lock(false);}
};
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
refresh().then(()=>status(dirty?'已恢复当前标签页的草稿。':'可以开始写了。')).catch(e=>status(e.message));
})();
