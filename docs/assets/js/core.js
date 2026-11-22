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

  const latest = document.querySelector('[data-latest-edition-date]');
  if (latest) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(new Date());
    const date = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
    const today = [date.year, date.month, date.day].join('-');
    if (latest.dataset.latestEditionDate === today) latest.querySelector('.day-state').textContent = '今日';
    const editionStatus = document.querySelector('[data-edition-status]');
    if (editionStatus) editionStatus.hidden = latest.dataset.latestEditionDate >= today;
  }

  const wide = matchMedia('(min-width: 1101px)');
  const openWide = () => {
    for (const disclosure of document.querySelectorAll('[data-desktop-open]')) disclosure.open = wide.matches;
  };
  openWide();
  wide.addEventListener('change', openWide);

  for (const edition of document.querySelectorAll('.daily-day')) {
    const filters = edition.querySelector('.category-filters');
    if (!filters) continue;
    const buttons = [...filters.querySelectorAll('[data-category-filter]')];
    const stories = edition.querySelectorAll('article.digest-item');
    const headlines = edition.querySelectorAll('.headline-list li');
    const count = edition.querySelector('[data-ranking-count]');
    const applyFilter = button => {
      const category = button.dataset.categoryFilter;
      for (const toggle of buttons) toggle.setAttribute('aria-pressed', String(toggle === button));
      for (const row of [...stories, ...headlines]) row.hidden = !!category && row.dataset.category !== category;
      count.textContent = headlines.length - [...headlines].filter(row => row.hidden).length;
    };
    filters.hidden = false;
    for (const button of buttons) button.addEventListener('click', () => applyFilter(button));
    const revealAnchor = () => {
      const target = document.getElementById(location.hash.slice(1));
      if (target?.hidden && edition.contains(target)) {
        applyFilter(buttons[0]);
        target.scrollIntoView();
      }
    };
    edition.querySelector('.edition-overview').addEventListener('click', event => {
      const href = event.target.closest('a')?.hash.slice(1);
      if (href && document.getElementById(href)?.hidden) applyFilter(buttons[0]);
    });
    window.addEventListener('hashchange', revealAnchor);
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
