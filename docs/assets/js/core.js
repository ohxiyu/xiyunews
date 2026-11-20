(() => {
  const root = document.documentElement;
  const toggle = document.querySelector('.theme-toggle');
  if (toggle) {
    const dark = () => root.dataset.theme
      ? root.dataset.theme === 'dark'
      : matchMedia('(prefers-color-scheme: dark)').matches;
    const label = () => {
      toggle.setAttribute('aria-label', dark() ? '切换浅色模式' : '切换深色模式');
      toggle.setAttribute('aria-pressed', String(dark()));
    };
    toggle.hidden = false;
    label();
    toggle.addEventListener('click', () => {
      const theme = dark() ? 'light' : 'dark';
      root.dataset.theme = theme;
      try { localStorage.setItem('xiyu-core-theme', theme); } catch {}
      label();
    });
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', label);
  }

  document.querySelectorAll('[data-copy]').forEach(button => { button.hidden = false; });
  const status = document.querySelector('.copy-status');
  let clearStatus;
  document.addEventListener('click', async event => {
    const copy = event.target.closest('[data-copy]');
    if (!copy || !status) return;
    try {
      await navigator.clipboard.writeText(new URL(copy.dataset.copy, location.href).href);
      status.textContent = '链接已复制';
    } catch {
      status.textContent = '复制失败，请复制地址栏链接';
    }
    clearTimeout(clearStatus);
    clearStatus = setTimeout(() => { status.textContent = ''; }, 2500);
  });

  const feed = document.querySelector('.daily-day .core-feed');
  const articles = feed?.querySelectorAll(':scope > article[id]');
  if (articles && articles.length > 1) {
    const catalog = document.createElement('nav');
    catalog.className = 'story-catalog';
    catalog.setAttribute('aria-label', '本期目录');
    const details = document.createElement('details');
    const title = document.createElement('summary');
    title.textContent = '本期目录';
    const list = document.createElement('ol');
    for (const article of articles) {
      const heading = article.querySelector('h2');
      if (!heading) continue;
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = '#' + encodeURIComponent(article.id);
      link.textContent = heading.textContent;
      item.append(link);
      list.append(item);
    }
    details.append(title, list);
    catalog.append(details);
    feed.before(catalog);
  }

  // Clean up the old offline reader while retaining other site preferences.
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(registrations => {
      for (const registration of registrations) {
        const worker = registration.active ?? registration.waiting ?? registration.installing;
        if (worker && new URL(worker.scriptURL).pathname === '/service-worker.js') {
          registration.unregister().catch(() => {});
        }
      }
    }).catch(() => {});
  }
  if ('caches' in window) {
    for (const key of ['bmt-reader-pages-v1', 'bmt-reader-assets-v2-xiyu']) {
      caches.delete(key).catch(() => {});
    }
  }
})();
