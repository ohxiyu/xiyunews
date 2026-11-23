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

  const storyText = button => button.closest('.story-body')?.querySelector(':scope > .story-summary-body');
  for (const button of document.querySelectorAll('[data-copy-body]')) {
    button.hidden = !storyText(button)?.textContent.trim();
  }
  const status = document.querySelector('.copy-status');
  let clearStatus;
  document.addEventListener('click', async event => {
    const copy = event.target.closest('[data-copy-body]');
    const body = copy && storyText(copy);
    if (!body || !status) return;
    const paragraphs = [...body.querySelectorAll(':scope > p')];
    const text = paragraphs.length
      ? paragraphs.map(paragraph => paragraph.innerText.trim()).filter(Boolean).join('\n\n')
      : body.innerText.trim();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = '正文已复制';
    } catch {
      status.textContent = '复制失败，请手动选中正文复制';
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
  const directory = document.getElementById('edition-directory');
  const jump = document.querySelector('.directory-jump');
  const syncDirectory = () => {
    if (directory) directory.open = wide.matches;
    if (jump) jump.hidden = !directory || wide.matches;
  };
  syncDirectory();
  wide.addEventListener('change', syncDirectory);

  if (directory && jump) {
    jump.addEventListener('click', () => {
      directory.open = true;
      directory.querySelector('summary').focus({ preventScroll: true });
      directory.scrollIntoView();
    });
  }

  for (const edition of document.querySelectorAll('.daily-day')) {
    const stories = [...edition.querySelectorAll('article.digest-item')];
    const headlines = [...edition.querySelectorAll('.headline-list li')];
    const links = new Map(headlines.map(row => {
      const link = row.querySelector('a');
      return [link.hash, link];
    }));
    let activeLink;
    let trackingFrame = 0;
    const markCurrent = () => {
      trackingFrame = 0;
      let story;
      if (wide.matches) {
        const readingLine = document.querySelector('.site-header').getBoundingClientRect().bottom + 96;
        const atEnd = window.scrollY + window.innerHeight >= root.scrollHeight - 2;
        for (const candidate of stories) {
          if (candidate.hidden) continue;
          if (story && !atEnd && candidate.getBoundingClientRect().top > readingLine) break;
          story = candidate;
        }
      }
      const nextLink = story && links.get('#' + story.id);
      if (activeLink === nextLink) return;
      activeLink?.removeAttribute('aria-current');
      nextLink?.setAttribute('aria-current', 'location');
      activeLink = nextLink;
    };
    const trackReading = () => {
      if (!trackingFrame) trackingFrame = requestAnimationFrame(markCurrent);
    };
    if (links.size) {
      markCurrent();
      window.addEventListener('scroll', trackReading, { passive: true });
      window.addEventListener('resize', trackReading);
      wide.addEventListener('change', trackReading);
    }

    const filters = edition.querySelector('.category-filters');
    if (!filters) continue;
    const buttons = [...filters.querySelectorAll('[data-category-filter]')];
    const count = edition.querySelector('[data-ranking-count]');
    const applyFilter = button => {
      const category = button.dataset.categoryFilter;
      for (const toggle of buttons) toggle.setAttribute('aria-pressed', String(toggle === button));
      for (const row of [...stories, ...headlines]) row.hidden = !!category && row.dataset.category !== category;
      count.textContent = headlines.filter(row => !row.hidden).length;
      trackReading();
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
