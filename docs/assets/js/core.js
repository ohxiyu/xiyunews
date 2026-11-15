(() => {
  'use strict';
  const button = document.querySelector('.theme-toggle');
  const dark = () => document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme:dark)').matches;
  const label = () => {if(button){button.setAttribute('aria-label', dark() ? '切换浅色模式' : '切换深色模式');button.setAttribute('aria-pressed',String(dark()));}};
  if(button){button.hidden=false;label();button.addEventListener('click',()=>{const theme=dark()?'light':'dark';document.documentElement.dataset.theme=theme;try{localStorage.setItem('xiyu-core-theme',theme);}catch(_){}label();});}
  const enableCopy=()=>document.querySelectorAll('[data-copy]').forEach(b=>b.hidden=false);
  enableCopy();
  document.addEventListener('click',async event=>{const copy=event.target.closest('[data-copy]');if(!copy)return;const status=document.querySelector('.copy-status');try{await navigator.clipboard.writeText(new URL(copy.dataset.copy,location.href).href);if(status)status.textContent='链接已复制';}catch(_){if(status)status.textContent='复制失败，请复制地址栏链接';}setTimeout(()=>{if(status)status.textContent='';},2500);});
  let readerReveal;
  function reveal(){if(readerReveal){readerReveal();return;}if(!location.hash)return;let id;try{id=decodeURIComponent(location.hash.slice(1));}catch(_){return;}const target=document.getElementById(id);if(!target)return;target.querySelector(':scope > details')?.setAttribute('open','');for(let node=target.parentElement;node;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;requestAnimationFrame(()=>target.scrollIntoView());}
  const feed=document.querySelector('.daily-day .core-feed');
  const stories=feed ? Array.from(feed.querySelectorAll(':scope > .core-story[id]')).filter(a=>a.querySelector('h2')) : [];
  if(stories.length){
    const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text)n.textContent=text;return n;};
    const narrow=matchMedia('(max-width:760px)');
    const workspace=el('div','reading-workspace');
    const catalog=el('nav','story-catalog');catalog.setAttribute('aria-label','本期新闻目录');
    const catalogHeading=el('div','catalog-heading');catalogHeading.append(el('strong','','本期目录'),el('span','',stories.length+' 条'));catalog.append(catalogHeading);
    const list=el('ol','catalog-list');catalog.append(list);
    const panel=el('section','reading-panel');panel.setAttribute('aria-label','新闻全文');
    const tools=el('div','reading-tools');
    const back=el('button','reader-back','← 返回目录');back.type='button';
    const position=el('span','reading-position');position.setAttribute('aria-live','polite');
    const previous=el('button','reader-previous','上一条');previous.type='button';
    const next=el('button','reader-next','下一条');next.type='button';
    tools.append(back,position,previous,next);
    const links=[];
    stories.forEach((article,i)=>{
      const li=el('li');const a=el('a','catalog-link');a.href='#'+article.id;
      const meta=el('span','catalog-meta');meta.append(el('span','catalog-number',String(i+1).padStart(2,'0')));
      const time=article.querySelector('.story-meta time');meta.append(el('span','',time?.textContent||'来源未提供时间'));
      const title=el('span','catalog-title',article.querySelector('h2').textContent);
      const excerpt=article.querySelector('.story-summary-body');
      a.append(meta,title);if(excerpt){const text=excerpt.textContent.trim().replace(/\s+/g,' ');a.append(el('span','catalog-excerpt',Array.from(text).slice(0,85).join('')+(text.length>85?'…':'')));}
      a.setAttribute('aria-controls',article.id);li.append(a);list.append(li);links.push(a);
      article.querySelector('h2').tabIndex=-1;
      a.addEventListener('click',event=>{if(event.button||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;event.preventDefault();open(i,narrow.matches);});
      const actions=article.querySelector('.story-actions');
      if(actions&&i<stories.length-1){const onward=el('button','reader-continue','阅读下一条 →');onward.type='button';onward.addEventListener('click',()=>open(i+1,true));actions.append(onward);}
    });
    feed.before(workspace);workspace.append(catalog,panel);panel.append(tools,feed);
    let selected=0,listY=0;
    function hashIndex(){let id;try{id=decodeURIComponent(location.hash.slice(1));}catch(_){return -1;}return stories.findIndex(a=>a.id===id||Boolean(id&&a.querySelectorAll('[id]').length&&Array.from(a.querySelectorAll('[id]')).some(n=>n.id===id)));}
    function display(index,focus=false){
      selected=index<0?selected:index;workspace.classList.toggle('is-reading',index>=0);
      stories.forEach((a,i)=>{a.hidden=i!==selected;if(i===selected&&(!narrow.matches||index>=0))links[i].setAttribute('aria-current','true');else links[i].removeAttribute('aria-current');});
      position.textContent=(selected+1)+' / '+stories.length;
      previous.disabled=selected===0;next.disabled=selected===stories.length-1;
      panel.scrollTop=0;
      if(!narrow.matches){const item=links[selected].getBoundingClientRect(),box=catalog.getBoundingClientRect();if(item.bottom>box.bottom)catalog.scrollTop+=item.bottom-box.bottom;if(item.top<box.top+46)catalog.scrollTop-=box.top+46-item.top;}
      if(focus)stories[selected].querySelector('h2').focus({preventScroll:true});
    }
    function open(index,focus){if(narrow.matches&&!workspace.classList.contains('is-reading'))listY=scrollY;history.pushState({readerEntry:true},'','#'+stories[index].id);display(index,focus);if(narrow.matches)workspace.scrollIntoView({block:'start'});}
    previous.addEventListener('click',()=>{if(selected>0)open(selected-1,true);});
    next.addEventListener('click',()=>{if(selected<stories.length-1)open(selected+1,true);});
    back.addEventListener('click',()=>{history.pushState(null,'',location.pathname+location.search);display(-1);links[selected].focus({preventScroll:true});scrollTo(0,listY);});
    readerReveal=()=>{display(hashIndex());if(narrow.matches){if(hashIndex()>=0)workspace.scrollIntoView({block:'start'});else scrollTo(0,listY);}};
    addEventListener('popstate',readerReveal);
    narrow.addEventListener('change',()=>display(hashIndex()));
    addEventListener('load',()=>{if(!narrow.matches&&hashIndex()>=0)requestAnimationFrame(()=>{scrollTo(0,0);panel.scrollTop=0;});},{once:true});
    display(hashIndex());
  }
  reveal();addEventListener('hashchange',reveal);
  // Retire only this site's old reader worker/caches; leave user preferences intact.
  if('serviceWorker'in navigator)navigator.serviceWorker.getRegistrations().then(rows=>Promise.all(rows.filter(r=>{try{return new URL(r.active?.scriptURL||r.waiting?.scriptURL||r.installing?.scriptURL).pathname==='/service-worker.js';}catch(_){return false;}}).map(r=>r.unregister()))).catch(()=>{});
  if('caches'in window)caches.keys().then(keys=>Promise.all(keys.filter(k=>k==='bmt-reader-pages-v1'||k==='bmt-reader-assets-v2-xiyu').map(k=>caches.delete(k)))).catch(()=>{});
})();
