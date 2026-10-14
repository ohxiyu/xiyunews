const CARD_CSS_WIDTH = 440;
const CARD_SCALE = 3;
const CARD_MAX_HEIGHT = 12288;
const X_COMPOSE_URL = 'https://x.com/compose/post';
const SANS_FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
const MONO_FONT = 'ui-monospace, "SF Mono", "Cascadia Mono", "JetBrains Mono", Menlo, Consolas, monospace';

const DEFAULT_COLORS = {
  background: '#f5f6f8', surface: '#ffffff', detail: '#f6f7f9', border: '#e6e9ee',
  text: '#202329', soft: '#3d4550', muted: '#69717d', accent: '#3555a2',
  up: '#278167', warn: '#a05a12', high: '#b33c3c'
};

// Use the site's current light/dark tokens, not a separately drifting palette.
export function cardPalette(styles) {
  const tokens = {background: 'bg', surface: 'surface', detail: 'surface-soft',
    border: 'border', text: 'text', soft: 'text-soft', muted: 'text-muted',
    accent: 'accent', up: 'up', warn: 'warn', high: 'tier-high'};
  return Object.fromEntries(Object.entries(tokens).map(([key, token]) =>
    [key, styles?.getPropertyValue(`--${token}`).trim() || DEFAULT_COLORS[key]]));
}

const METRICS = {
  left: 26, right: 26, headerHeight: 47, titleY: 76,
  xs: 11.5, small: 12.8, body: 15, title: 18,
  xsLine: 17.25, smallLine: 23.04, bodyLine: 27.75, titleLine: 28.8
};

const LABELS = {
  zh: {
    title: '分享', close: '关闭', generating: '正在生成完整长卡…', download: '保存图片',
    xShare: '复制图片并打开 X', ready: '完整长卡已生成', failed: '卡片生成失败，请重试',
    copyReady: '图片已复制，请在 X 编辑器中粘贴后发布',
    copyFailed: '无法复制图片，请保存后手动上传到 X',
    clipboardUnavailable: '当前浏览器不支持复制图片，请保存后上传到 X', details: '背景、讨论与参考资料',
    references: '参考链接', tags: '标签'
  },
  en: {
    title: 'Share', close: 'Close', generating: 'Generating the full story card…', download: 'Save image',
    xShare: 'Copy image and open X', ready: 'Full story card ready',
    failed: 'Could not generate the card. Please try again.',
    copyReady: 'Image copied. Paste it into the X composer to post.',
    copyFailed: 'Could not copy the image. Save it and upload it to X instead.',
    clipboardUnavailable: 'This browser cannot copy images. Save it and upload it to X instead.',
    details: 'Background, discussion, and references', references: 'References', tags: 'Tags'
  }
};

let cardGeneration = 0;
let activeCardBlob = null;
let activeCardStory = null;

function cardFilename(story) {
  const rank = String(story.rank || '').replace(/\D+/g, '') || 'story';
  return `xiyunews-${story.date || 'daily'}-${rank}.png`;
}

export function supportsImageClipboard() {
  return Boolean(window.isSecureContext && navigator.clipboard &&
    typeof navigator.clipboard.write === 'function' && typeof window.ClipboardItem === 'function');
}

export async function copyImageToClipboard(blob, clipboard, ClipboardItemType) {
  const targetClipboard = clipboard || navigator.clipboard;
  const ItemType = ClipboardItemType || window.ClipboardItem;
  const item = new ItemType({'image/png': blob});
  await targetClipboard.write([item]);
}

function actionIcon(kind) {
  const icon = document.createElement('span');
  icon.className = 'share-card-action-icon';
  icon.setAttribute('aria-hidden', 'true');
  if (kind === 'x') {
    icon.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.657l-5.214-6.817-5.966 6.817H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z"></path></svg>';
  } else {
    icon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12m0 0 4-4m-4 4-4-4"></path><path d="M5 18v2h14v-2"></path></svg>';
  }
  return icon;
}

function setActionLabel(button, icon, text) {
  const label = document.createElement('span');
  label.textContent = text;
  button.replaceChildren(actionIcon(icon), label);
}

function closeCardDialog(dialog) {
  cardGeneration += 1;
  activeCardBlob = null;
  activeCardStory = null;
  const preview = dialog.querySelector('.share-card-preview');
  if (preview) preview.replaceChildren();
  if (typeof dialog.close === 'function') dialog.close();
  else dialog.removeAttribute('open');
}

function ensureCardDialog(language) {
  let dialog = document.querySelector('.share-card-dialog');
  if (!dialog) {
    dialog = document.createElement('dialog');
    dialog.className = 'share-card-dialog';

    const panel = document.createElement('section');
    panel.className = 'share-card-panel';
    const header = document.createElement('header');
    const title = document.createElement('h2');
    title.dataset.cardLabel = 'title';
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'share-card-close';
    close.dataset.cardAction = 'close';
    close.textContent = '×';
    header.appendChild(title);
    header.appendChild(close);

    const preview = document.createElement('div');
    preview.className = 'share-card-preview';
    preview.setAttribute('aria-live', 'polite');
    const status = document.createElement('p');
    status.className = 'share-card-status';
    status.setAttribute('role', 'status');

    const actions = document.createElement('footer');
    actions.className = 'share-card-actions';
    const download = document.createElement('button');
    download.type = 'button';
    download.dataset.cardAction = 'download';
    download.disabled = true;
    const xShare = document.createElement('button');
    xShare.type = 'button';
    xShare.className = 'share-card-primary';
    xShare.dataset.cardAction = 'x-share';
    xShare.disabled = true;
    actions.appendChild(download);
    actions.appendChild(xShare);

    panel.appendChild(header);
    panel.appendChild(preview);
    panel.appendChild(status);
    panel.appendChild(actions);
    dialog.appendChild(panel);
    document.body.appendChild(dialog);

    dialog.addEventListener('click', (event) => {
      if (event.target === dialog || event.target.closest('[data-card-action="close"]')) closeCardDialog(dialog);
    });
    dialog.addEventListener('cancel', () => {
      cardGeneration += 1;
      activeCardBlob = null;
      activeCardStory = null;
      preview.replaceChildren();
    });
    download.addEventListener('click', () => {
      if (!activeCardBlob || !activeCardStory) return;
      const objectUrl = URL.createObjectURL(activeCardBlob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = cardFilename(activeCardStory);
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    });
    xShare.addEventListener('click', async () => {
      if (!activeCardBlob || !activeCardStory) return;
      const labels = LABELS[activeCardStory.language];
      const copyPromise = copyImageToClipboard(activeCardBlob);
      const composerWindow = window.open('about:blank', '_blank');
      try {
        await copyPromise;
        status.textContent = labels.copyReady;
        if (composerWindow) {
          composerWindow.opener = null;
          composerWindow.location.replace(X_COMPOSE_URL);
        } else {
          window.location.assign(X_COMPOSE_URL);
        }
      } catch (error) {
        if (composerWindow && !composerWindow.closed) composerWindow.close();
        status.textContent = labels.copyFailed;
      }
    });
  }

  const labels = LABELS[language];
  dialog.querySelector('[data-card-label="title"]').textContent = labels.title;
  const closeButton = dialog.querySelector('[data-card-action="close"]');
  closeButton.setAttribute('aria-label', labels.close);
  closeButton.title = labels.close;
  setActionLabel(dialog.querySelector('[data-card-action="download"]'), 'download', labels.download);
  setActionLabel(dialog.querySelector('[data-card-action="x-share"]'), 'x', labels.xShare);
  return dialog;
}

function setFont(context, size, weight, mono, letterSpacing = 0) {
  context.font = `${weight} ${size}px ${mono ? MONO_FONT : SANS_FONT}`;
  if ('letterSpacing' in context) context.letterSpacing = `${letterSpacing}px`;
}

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function segmentText(text, language) {
  if (typeof Intl !== 'undefined' && Intl.Segmenter) {
    const segmenter = new Intl.Segmenter(language === 'zh' ? 'zh-CN' : 'en', {granularity: 'word'});
    return Array.from(segmenter.segment(text), (part) => part.segment);
  }
  return text.split(/(\s+|(?=[\u2e80-\u9fff])|(?<=[\u2e80-\u9fff]))/).filter(Boolean);
}

function breakLongToken(context, token, maxWidth) {
  const pieces = [];
  let current = '';
  Array.from(token).forEach((character) => {
    const next = current + character;
    if (current && context.measureText(next).width > maxWidth) {
      pieces.push(current);
      current = character;
    } else current = next;
  });
  if (current) pieces.push(current);
  return pieces;
}

export function wrapText(context, value, maxWidth, language) {
  const paragraphs = String(value || '').split(/\n+/);
  const lines = [];
  paragraphs.forEach((paragraph, paragraphIndex) => {
    const clean = normalizeText(paragraph);
    if (!clean) {
      if (paragraphIndex < paragraphs.length - 1) lines.push('');
      return;
    }
    let line = '';
    segmentText(clean, language).forEach((token) => {
      const candidate = line + token;
      if (!line && context.measureText(candidate).width > maxWidth) {
        const pieces = breakLongToken(context, token.trimStart(), maxWidth);
        lines.push(...pieces.slice(0, -1));
        line = pieces[pieces.length - 1] || '';
        return;
      }
      if (!line || context.measureText(candidate).width <= maxWidth) {
        line = candidate;
        return;
      }
      const trimmed = token.trimStart();
      if (line && /^[，。！？；：、）】》”’…]/.test(trimmed)) {
        line = candidate;
        return;
      }
      lines.push(line.trimEnd());
      if (context.measureText(trimmed).width <= maxWidth) {
        line = trimmed;
        return;
      }
      const pieces = breakLongToken(context, trimmed, maxWidth);
      lines.push(...pieces.slice(0, -1));
      line = pieces[pieces.length - 1] || '';
    });
    if (line) lines.push(line.trimEnd());
  });
  return lines.length ? lines : [''];
}

export function wrapBalancedText(context, value, maxWidth, language) {
  const greedy = wrapText(context, value, maxWidth, language);
  if (greedy.length < 2) return greedy;

  const score = (lines) => {
    const widths = lines.map((line) => context.measureText(line).width);
    const average = widths.reduce((total, width) => total + width, 0) / widths.length;
    return widths.reduce((total, width) => total + ((width - average) ** 2), 0);
  };

  let best = greedy;
  let bestScore = score(greedy);
  const minimumWidth = maxWidth * 0.6;
  for (let width = maxWidth - 2; width >= minimumWidth; width -= 2) {
    const candidate = wrapText(context, value, width, language);
    if (candidate.length !== greedy.length) continue;
    const candidateScore = score(candidate);
    if (candidateScore < bestScore) {
      best = candidate;
      bestScore = candidateScore;
    }
  }
  return best;
}

function drawLines(context, lines, x, y, lineHeight) {
  lines.forEach((line, index) => context.fillText(line, x, y + index * lineHeight));
  return y + lines.length * lineHeight;
}

function buildLayout(context, story) {
  const contentX = METRICS.left;
  const contentWidth = CARD_CSS_WIDTH - METRICS.left - METRICS.right;
  setFont(context, METRICS.title, 700, false);
  const titleLines = wrapBalancedText(context, story.title, contentWidth, story.language);
  let y = METRICS.titleY + titleLines.length * METRICS.titleLine + 14;

  // Explicit field for new pages; section fallback supports older editions.
  const background = normalizeText(story.background) || (story.sections || [])
    .filter(section => /背景|Background/i.test(section.title))
    .map(section => normalizeText(section.text)).filter(Boolean).join('\n\n');
  let backgroundPanel = null;
  if (background) {
    setFont(context, METRICS.small, 400, false);
    const lines = wrapText(context, background, contentWidth - 28, story.language);
    backgroundPanel = {top: y, titleY: y + 12, textY: y + 12 + METRICS.xsLine + 6, lines};
    backgroundPanel.bottom = backgroundPanel.textY + lines.length * METRICS.smallLine + 12;
    y = backgroundPanel.bottom + 16;
  }

  setFont(context, METRICS.body, 400, false);
  const blocks = (Array.isArray(story.summaryParagraphs) && story.summaryParagraphs.length
    ? story.summaryParagraphs : String(story.summary || '').split(/\n\s*\n+/))
    .map(normalizeText).filter(Boolean);
  const summaryParagraphs = blocks.map(paragraph => {
    const lines = wrapText(context, paragraph, contentWidth, story.language);
    const row = {y, lines};
    y += lines.length * METRICS.bodyLine + 9;
    return row;
  });
  return {height: Math.ceil(Math.max(y + 20, 180)), contentX, contentWidth,
    titleY: METRICS.titleY, titleLines, backgroundPanel, summaryParagraphs};
}

function drawHeader(context, COLORS) {
  // Reuse the inline master path, without a network request or raster resampling.
  const marks = document.querySelectorAll('.site-brand .site-brand-mark path');
  const markWidth = marks.length && typeof Path2D !== 'undefined' ? 30 : 0;
  if (markWidth) {
    context.save();
    context.translate(14, 11);
    context.scale(24 / 512, 24 / 512);
    marks.forEach((mark) => {
      const fill = mark.getAttribute('fill');
      if (fill === 'none') return;
      context.fillStyle = !fill || fill === 'currentColor' ? COLORS.accent : fill;
      context.fill(new Path2D(mark.getAttribute('d')), 'evenodd');
    });
    context.restore();
  }
  setFont(context, 18, 750, false, -0.4);
  context.fillStyle = COLORS.text;
  context.fillText('xiyu.news', 14 + markWidth, 16);

  context.fillStyle = COLORS.border;
  context.fillRect(0, METRICS.headerHeight - 1, CARD_CSS_WIDTH, 1);
}

function drawPanel(context, x, y, width, height, radius, fill, border) {
  context.beginPath();
  if (context.roundRect) context.roundRect(x, y, width, height, radius);
  else context.rect(x, y, width, height);
  context.fillStyle = fill;
  context.fill();
  context.strokeStyle = border;
  context.lineWidth = 1;
  context.stroke();
}

function drawCard(context, story, layout, COLORS) {
  context.fillStyle = COLORS.background;
  context.fillRect(0, 0, CARD_CSS_WIDTH, layout.height);
  context.textBaseline = 'top';
  context.fillStyle = COLORS.surface;
  context.fillRect(0, 0, CARD_CSS_WIDTH, METRICS.headerHeight);
  drawHeader(context, COLORS);
  drawPanel(context, 12, 56, CARD_CSS_WIDTH - 24, layout.height - 68,
    12, COLORS.surface, COLORS.border);
  setFont(context, METRICS.title, 700, false);
  context.fillStyle = COLORS.text;
  drawLines(context, layout.titleLines, layout.contentX, layout.titleY, METRICS.titleLine);

  const background = layout.backgroundPanel;
  if (background) {
    drawPanel(context, layout.contentX, background.top, layout.contentWidth,
      background.bottom - background.top, 9, COLORS.detail, COLORS.border);
    context.fillStyle = COLORS.accent;
    context.fillRect(layout.contentX, background.top + 10, 3, background.bottom - background.top - 20);
    setFont(context, METRICS.xs, 600, false);
    context.fillText(story.language === 'en' ? 'Background' : '背景', layout.contentX + 14, background.titleY);
    setFont(context, METRICS.small, 400, false);
    context.fillStyle = COLORS.soft;
    drawLines(context, background.lines, layout.contentX + 14, background.textY, METRICS.smallLine);
  }
  setFont(context, METRICS.body, 400, false);
  context.fillStyle = COLORS.soft;
  layout.summaryParagraphs.forEach(paragraph => {
    drawLines(context, paragraph.lines, layout.contentX, paragraph.y, METRICS.bodyLine);
  });
}

export async function renderStoryCard(story) {
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  story.sections = Array.isArray(story.sections) ? story.sections : [];
  story.references = Array.isArray(story.references) ? story.references : [];
  story.tags = Array.isArray(story.tags) ? story.tags : [];

  const measuringCanvas = document.createElement('canvas');
  const measuringContext = measuringCanvas.getContext('2d');
  if (!measuringContext) throw new Error('Canvas is not supported');
  const COLORS = cardPalette(typeof getComputedStyle === 'function'
    ? getComputedStyle(document.documentElement) : undefined);
  const layout = buildLayout(measuringContext, story, COLORS);
  const rasterHeight = layout.height * CARD_SCALE;
  if (rasterHeight > CARD_MAX_HEIGHT) {
    throw new Error(story.language === 'zh' ? '内容过长，无法生成单张卡片' : 'This story is too long for one card');
  }

  const canvas = document.createElement('canvas');
  canvas.width = CARD_CSS_WIDTH * CARD_SCALE;
  canvas.height = rasterHeight;
  canvas.setAttribute('aria-label', story.language === 'zh' ? '分享卡片预览' : 'Share card preview');
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvas is not supported');
  context.scale(CARD_SCALE, CARD_SCALE);
  drawCard(context, story, layout, COLORS);
  return canvas;
}

export function canvasToBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('PNG export failed'));
    }, 'image/png');
  });
}

export async function openStoryCard(story) {
  const labels = LABELS[story.language];
  const dialog = ensureCardDialog(story.language);
  const preview = dialog.querySelector('.share-card-preview');
  const status = dialog.querySelector('.share-card-status');
  const download = dialog.querySelector('[data-card-action="download"]');
  const xShare = dialog.querySelector('[data-card-action="x-share"]');
  const generation = ++cardGeneration;
  activeCardBlob = null;
  activeCardStory = null;
  preview.replaceChildren();
  preview.classList.add('is-loading');
  status.textContent = labels.generating;
  download.disabled = true;
  xShare.disabled = true;
  download.classList.add('share-card-primary');
  xShare.classList.remove('share-card-primary');

  if (!dialog.open) {
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }

  try {
    const canvas = await renderStoryCard(story);
    const blob = await canvasToBlob(canvas);
    if (generation !== cardGeneration) return;
    preview.classList.remove('is-loading');
    preview.replaceChildren(canvas);
    activeCardBlob = blob;
    activeCardStory = story;
    download.disabled = false;
    status.textContent = `${labels.ready} · ${canvas.width} × ${canvas.height} px`;
    if (supportsImageClipboard()) {
      xShare.disabled = false;
      xShare.classList.add('share-card-primary');
      download.classList.remove('share-card-primary');
      xShare.removeAttribute('title');
    } else {
      xShare.title = labels.clipboardUnavailable;
      status.textContent += ` · ${labels.clipboardUnavailable}`;
    }
  } catch (error) {
    if (generation !== cardGeneration) return;
    preview.classList.remove('is-loading');
    status.textContent = error && error.message ? error.message : labels.failed;
  }
}
