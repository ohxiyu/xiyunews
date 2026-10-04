(() => {
  'use strict';
  const status = document.querySelector('[data-quick-post-status]');
  if (!status) return;
  const fallback = document.querySelector('[data-quick-post-unplaced]');
  const en = document.documentElement.lang.startsWith('en');
  let version = 0, knownDates = '', timer;
  function card(post) {
    const node = document.createElement('article');
    node.className = 'quick-post-public';
    node.dataset.quickPost = post.id;
    const meta = document.createElement('small');
    meta.textContent = 'Quick Post · ' + post.date + (post.breaking ? ' · Breaking' : '') + (post.pin ? ' · PIN' : '');
    node.append(meta);
    if (post.title) {
      const title = document.createElement('h2'); title.textContent = post.title; node.append(title);
    }
    for (const text of post.body.split(/\n\s*\n/)) {
      const paragraph = document.createElement('p');
      paragraph.textContent = text;
      paragraph.style.whiteSpace = 'pre-wrap';
      node.append(paragraph);
    }
    if (/^\/assets\/uploads\/quick-[a-f0-9]{64}\.(png|jpg|webp)$/.test(post.image)) {
      const image = document.createElement('img');
      image.src = post.image; image.alt = en ? 'Quick Post image' : 'Quick Post 配图'; image.loading = 'lazy';
      node.append(image);
    }
    const extras = document.createElement('details'); extras.className = 'quick-post-details';
    const caption = document.createElement('summary');
    caption.textContent = en ? 'Background, impact and references' : '背景、影响与参考资料';
    extras.append(caption);
    for (const [key, label] of [['market_impact',en?'Market impact':'市场影响'],['background',en?'Background':'背景']]) {
      if (!post[key]) continue;
      const heading=document.createElement('h3');heading.textContent=label;
      const text=document.createElement('p');text.textContent=post[key];extras.append(heading,text);
    }
    if (Array.isArray(post.tags) && post.tags.length) {
      const tags=document.createElement('p');tags.className='quick-post-tags';tags.textContent=post.tags.map(tag=>'#'+tag).join(' ');extras.append(tags);
    }
    if (extras.children.length>1) node.append(extras);
    const sources = Array.isArray(post.sources) ? post.sources : post.url ? [{url:post.url,title:en?'Source ↗':'原文 ↗'}] : [];
    for (const source of sources) {
      try {
        const url = new URL(source.url);
        if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) {
          const link = document.createElement('a');
          link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
          link.textContent = source.title || (en ? 'Source ↗' : '原文 ↗');
          if(post.batch_id){extras.append(link);if(!extras.parentElement)node.append(extras);}else node.append(link);
        }
      } catch {}
    }
    return node;
  }
  function dates() {
    return [...new Set([...document.querySelectorAll('.daily-day[data-date]')].map(day => day.dataset.date))].sort().join(',');
  }
  async function refresh() {
    const run = ++version;
    knownDates = dates();
    // Remove previously rendered content when verification fails; never present it as current.
    document.querySelectorAll('[data-quick-post]').forEach(node => node.remove());
    status.textContent = en ? 'Loading Quick Post…' : '正在核对 Quick Post…';
    try {
      const today = new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date());
      const yesterday = new Date(Date.parse(today) - 86400000).toISOString().slice(0, 10);
      const wanted = [...new Set([today, yesterday, ...knownDates.split(',').filter(Boolean)])];
      const queries = []; // Include recent posts even before today's daily edition exists.
      for (let i = 0; i < wanted.length; i += 10) queries.push('?' + wanted.slice(i, i + 10).map(day => 'date=' + encodeURIComponent(day)).join('&'));
      const rows = [];
      let revision;
      for (const query of queries) {
        const response = await fetch('/api/quick-posts.json' + query, {cache: 'no-store', signal: AbortSignal.timeout(15000)});
        if (!response.ok) throw Error('unavailable');
        const payload = await response.json();
        if (!Array.isArray(payload.items) || !payload.revision) throw Error('unverified');
        if (revision && revision !== payload.revision) throw Error('registry changed during history read');
        revision = payload.revision;
        rows.push(...payload.items);
      }
      if (run !== version) return;
      const posts = [...new Map(rows.map(post => [post.id, post])).values()];
      const groups = [];
      const batches = new Map();
      for (const post of posts) {
        if (!post.batch_id) { groups.push([post]); continue; }
        if (!batches.has(post.batch_id)) { const group=[];batches.set(post.batch_id,group);groups.push(group); }
        batches.get(post.batch_id).push(post);
      }
      for (const group of groups) {
        const post=group[0];
        group.sort((a,b)=>(a.batch_index||0)-(b.batch_index||0));
        const day = [...document.querySelectorAll('.daily-day[data-date]')].find(day => day.dataset.date === post.date);
        const stream = day?.querySelector('.daily-story-stream');
        const fragment=document.createDocumentFragment();
        group.forEach(item=>fragment.append(card(item)));
        if (!stream) { fallback.append(fragment); continue; }
        const stories = [...stream.children].filter(node => node.classList.contains('digest-item'));
        if(post.batch_id) {
          let anchor=null;
          if(post.anchor_id) {
            anchor=stories.find(node=>node.dataset.storyId===post.anchor_id);
            // Older generated HTML has rank-only IDs. Match exact source URL from
            // the edition, never fall back to its rank after an editorial rebuild.
            if(!anchor&&stories.some(node=>!node.dataset.storyId))try{
              const response=await fetch('/editions/'+post.date+'/edition.json',{cache:'no-store',signal:AbortSignal.timeout(10000)});
              const edition=response.ok?await response.json():null;
              const item=edition?.items?.find(item=>item.id===post.anchor_id);
              if(item?.url)anchor=stories.find(node=>!node.dataset.storyId&&[...node.querySelectorAll('h2 a')].some(link=>link.href===item.url));
            }catch{}
          }
          if(run!==version)return;
          if(post.anchor_id&&!anchor){
            const warning=document.createElement('small');warning.textContent=en?'Original anchor unavailable; group placed last.':'原插入新闻已不存在或无法核验，本组暂置末尾。';
            fragment.firstElementChild.prepend(warning);stream.append(fragment);
          }else{
            // Keep earlier groups at this same anchor before newer insertions.
            let next=anchor?anchor.nextElementSibling:stream.firstElementChild;
            while(next?.hasAttribute('data-quick-post'))next=next.nextElementSibling;
            stream.insertBefore(fragment,next);
          }
          continue;
        }
        const position = Number.isInteger(post.position) ? Math.min(post.position, stories.length) : 0;
        stream.insertBefore(fragment, stories[position] || null);
      }
      status.textContent = '';
    } catch {
      if (run !== version) return;
      status.textContent = en ? 'Quick Post is unavailable. ' : 'Quick Post 暂时无法核实。';
      const retry = document.createElement('button');
      retry.type = 'button'; retry.textContent = en ? 'Retry' : '重试'; retry.onclick = refresh;
      status.append(retry);
    }
  }
  const observer = new MutationObserver(mutations => {
    const storiesChanged=mutations.some(change=>[...change.addedNodes].some(node=>node.nodeType===1&&
      (node.matches('.digest-item,.daily-story-stream')||node.querySelector('.digest-item'))));
    if (dates() !== knownDates || storiesChanged) { clearTimeout(timer); timer = setTimeout(refresh, 50); }
  });
  observer.observe(document.querySelector('.day-stream') || fallback.parentElement, {childList: true, subtree: true});
  window.addEventListener('focus', refresh);
  refresh();
})();
