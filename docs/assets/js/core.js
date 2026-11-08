(() => {
  'use strict';
  const button = document.querySelector('.theme-toggle');
  const dark = () => document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme:dark)').matches;
  const label = () => {if(button) button.setAttribute('aria-label', dark() ? '切换浅色模式' : '切换深色模式');};
  if(button){button.hidden=false;label();button.addEventListener('click',()=>{const theme=dark()?'light':'dark';document.documentElement.dataset.theme=theme;try{localStorage.setItem('xiyu-core-theme',theme);}catch(_){}label();});}
  document.querySelectorAll('[data-copy]').forEach(button=>{button.hidden=false;button.addEventListener('click',async()=>{const target=new URL(location.href);target.hash=button.dataset.copy;const status=document.querySelector('.copy-status');try{await navigator.clipboard.writeText(target.href);status.textContent='链接已复制';}catch(_){status.textContent='复制失败，请复制地址栏链接';}setTimeout(()=>status.textContent='',2500);});});
  function reveal(){if(!location.hash)return;let id;try{id=decodeURIComponent(location.hash.slice(1));}catch(_){return;}const target=document.getElementById(id);if(!target)return;target.querySelector(':scope > details')?.setAttribute('open','');for(let node=target.parentElement;node;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;requestAnimationFrame(()=>target.scrollIntoView());}
  reveal();addEventListener('hashchange',reveal);
  const notice=document.querySelector('[data-edition-notice]');if(notice){const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());if(today>notice.dataset.edition){notice.textContent='当前展示 '+notice.dataset.edition+' 日报，新一期尚未发布。';notice.hidden=false;}}
  // Retire only this site's old reader worker/caches; leave user preferences intact.
  if('serviceWorker'in navigator)navigator.serviceWorker.getRegistrations().then(rows=>Promise.all(rows.filter(r=>{try{return new URL(r.active?.scriptURL||r.waiting?.scriptURL||r.installing?.scriptURL).pathname==='/service-worker.js';}catch(_){return false;}}).map(r=>r.unregister()))).catch(()=>{});
  if('caches'in window)caches.keys().then(keys=>Promise.all(keys.filter(k=>k==='bmt-reader-pages-v1'||k==='bmt-reader-assets-v2-xiyu').map(k=>caches.delete(k)))).catch(()=>{});
})();
