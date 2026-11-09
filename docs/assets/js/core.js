(() => {
  'use strict';
  const button = document.querySelector('.theme-toggle');
  const dark = () => document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme:dark)').matches;
  const label = () => {if(button){button.setAttribute('aria-label', dark() ? '切换浅色模式' : '切换深色模式');button.setAttribute('aria-pressed',String(dark()));}};
  if(button){button.hidden=false;label();button.addEventListener('click',()=>{const theme=dark()?'light':'dark';document.documentElement.dataset.theme=theme;try{localStorage.setItem('xiyu-core-theme',theme);}catch(_){}label();});}
  const enableCopy=()=>document.querySelectorAll('[data-copy]').forEach(b=>b.hidden=false);
  enableCopy();
  document.addEventListener('click',async event=>{const copy=event.target.closest('[data-copy]');if(!copy)return;const status=document.querySelector('.copy-status');try{await navigator.clipboard.writeText(new URL(copy.dataset.copy,location.href).href);if(status)status.textContent='链接已复制';}catch(_){if(status)status.textContent='复制失败，请复制地址栏链接';}setTimeout(()=>{if(status)status.textContent='';},2500);});
  function reveal(){if(!location.hash)return;let id;try{id=decodeURIComponent(location.hash.slice(1));}catch(_){return;}const target=document.getElementById(id);if(!target)return;target.querySelector(':scope > details')?.setAttribute('open','');for(let node=target.parentElement;node;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;requestAnimationFrame(()=>target.scrollIntoView());}
  reveal();addEventListener('hashchange',reveal);
  // Retire only this site's old reader worker/caches; leave user preferences intact.
  if('serviceWorker'in navigator)navigator.serviceWorker.getRegistrations().then(rows=>Promise.all(rows.filter(r=>{try{return new URL(r.active?.scriptURL||r.waiting?.scriptURL||r.installing?.scriptURL).pathname==='/service-worker.js';}catch(_){return false;}}).map(r=>r.unregister()))).catch(()=>{});
  if('caches'in window)caches.keys().then(keys=>Promise.all(keys.filter(k=>k==='bmt-reader-pages-v1'||k==='bmt-reader-assets-v2-xiyu').map(k=>caches.delete(k)))).catch(()=>{});
})();
