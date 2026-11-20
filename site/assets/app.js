import {ApiError, channels, getNews, headline, listChannels, listNews, localized, safeUrl, text, validChannel, validCoin, validStory} from './eqn.js';

const byId = id => document.getElementById(id);
const form = byId('filters');
const feed = byId('stories');
const detail = byId('detail');
const more = byId('more');
const refresh = byId('refresh');
const state = byId('feed-status');
const announcement = byId('announcement');
const interval = 45_000;
const timezone = 'Asia/Shanghai';
const dayFormat = new Intl.DateTimeFormat('sv-SE', {timeZone: timezone, dateStyle: 'short'});
const timeFormat = new Intl.DateTimeFormat('zh-CN', {timeZone: timezone, hourCycle: 'h23', hour: '2-digit', minute: '2-digit'});
let names = {...channels};
let controller;
let route;
let rows = [];
let next = '';
let newest = '';
let loaded = false;
let newItems = false;
let busy = false;
let timer;
let retryAt = 0;
let failures = 0;

function node(tag, value, className) {
  const element = document.createElement(tag);
  if (value) element.textContent = value;
  if (className) element.className = className;
  return element;
}

function button(label, action) {
  const element = node('button', label);
  element.type = 'button';
  element.addEventListener('click', action);
  return element;
}

function link(label, href, className) {
  const anchor = node('a', label, className);
  anchor.href = href;
  return anchor;
}

function internalLink(label, params, className) {
  const query = new URLSearchParams();
  for (const key of ['channel', 'query', 'coin', 'story']) {
    if (params[key] && params[key] !== 'all') query.set(key, params[key]);
  }
  const anchor = link(label, query.size ? '/?' + query : '/', className);
  anchor.addEventListener('click', event => {
    if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(anchor.href, true);
  });
  return anchor;
}

function parseRoute() {
  const params = new URLSearchParams(location.search);
  const channel = params.get('channel');
  const coin = (params.get('coin') ?? '').trim().toUpperCase();
  return {
    channel: validChannel(channel) ? channel : 'all',
    query: (params.get('query') ?? '').trim().slice(0, 120),
    coin: validCoin(coin) ? coin : '',
    story: params.get('story') ?? '',
  };
}

function formatTime(value, includeDay = false) {
  const time = node('time');
  const date = new Date(value ?? NaN);
  if (!Number.isFinite(date.valueOf())) {
    time.textContent = '时间未知';
    return time;
  }
  time.dateTime = date.toISOString();
  const clock = timeFormat.format(date);
  time.textContent = includeDay ? dayFormat.format(date) + ' ' + clock : clock;
  return time;
}

function renderChannels() {
  const items = Object.entries(names);
  if (!Object.hasOwn(names, route.channel)) items.unshift([route.channel, route.channel]);
  byId('channels').replaceChildren(...items.map(([key, name]) => {
    const anchor = internalLink(name, {channel: key, query: route.query, coin: route.coin});
    if (key !== 'all') anchor.append(node('small', key));
    if (key === route.channel) anchor.setAttribute('aria-current', 'true');
    return anchor;
  }));
  byId('feed-title').textContent = route.channel === 'all' ? '最新快讯' : names[route.channel] ?? route.channel;
}

function appendRows(items) {
  const seen = new Set(rows.map(item => String(item.no)));
  const fragment = document.createDocumentFragment();
  let lastDay = feed.lastElementChild?.dataset.day;
  for (const item of items) {
    const id = String(item.no);
    if (seen.has(id)) continue;
    seen.add(id);
    rows.push(item);
    const stamp = formatTime(item.time);
    const day = stamp.dateTime ? dayFormat.format(new Date(stamp.dateTime)) : '时间未知';
    if (day !== lastDay) fragment.append(node('h3', day, 'day'));
    lastDay = day;
    const article = node('article', '', 'story');
    article.dataset.day = day;
    const content = node('div');
    content.append(internalLink(headline(item), {...route, story: id}, 'title'), metadata(item));
    article.append(stamp, content);
    fragment.append(article);
  }
  feed.append(fragment);
}

function metadata(item) {
  const meta = node('div', '', 'meta');
  if (text(item.source)) meta.append(node('span', item.source));
  if (Array.isArray(item.coins)) {
    for (const coin of new Set(item.coins.filter(validCoin))) {
      meta.append(internalLink(coin, {...route, story: '', coin}, 'tag'));
    }
  }
  return meta;
}

function showSkeleton() {
  const skeleton = node('div', '', 'skeleton');
  skeleton.setAttribute('aria-hidden', 'true');
  for (let i = 0; i < 8; i++) skeleton.append(node('i'));
  feed.replaceChildren(skeleton);
  announcement.textContent = '正在读取快讯';
}

function errorMessage(error) {
  if (error.status === 429) return '上游请求频率受限，请稍后重试。';
  if (error.status === 400) return '上游未接受当前筛选条件。';
  if (error.status === 404) return '上游找不到这条快讯。';
  return '暂时无法连接方程式新闻，请稍后重试。';
}

function handleFailure(error) {
  failures += 1;
  const delay = error instanceof ApiError ? error.retryMs : 0;
  retryAt = Date.now() + Math.max(delay, error.status === 429 ? 60_000 : 0);
}

function schedule() {
  clearTimeout(timer);
  if (route.story || document.hidden) return;
  const backoff = Math.min(300_000, interval * 2 ** Math.min(failures, 3));
  timer = setTimeout(() => load('poll'), Math.max(backoff, retryAt - Date.now()));
}

async function load(kind = 'replace') {
  if (busy || route.story || (kind === 'poll' && document.hidden)) return;
  if (Date.now() < retryAt) {
    if (kind !== 'poll') state.textContent = '请求过于频繁，请稍后重试。';
    schedule();
    return;
  }
  const signal = controller.signal;
  const cursor = kind === 'more' ? next : '';
  if (kind === 'more' && !cursor) return;
  busy = true;
  if (kind !== 'poll') {
    refresh.disabled = true;
    more.disabled = true;
    state.replaceChildren();
  }
  const checkOnly = kind === 'poll' && loaded;
  try {
    const result = await listNews(route, cursor, signal);
    if (signal.aborted) return;
    failures = 0;
    if (checkOnly) {
      const updated = Boolean(result.items.length && String(result.items[0].no) !== newest);
      if (updated !== newItems) {
        newItems = updated;
        state.replaceChildren(...(updated ? [button('查看新快讯', () => load())] : []));
        if (updated) announcement.textContent = '有新快讯可以查看';
      }
      return;
    }

    if (kind !== 'more') {
      rows = [];
      newest = String(result.items[0]?.no ?? '');
      feed.replaceChildren();
      newItems = false;
    }
    appendRows(result.items);
    next = result.cursor !== cursor ? result.cursor : '';
    loaded = true;
    if (!rows.length) feed.replaceChildren(node('p', '没有符合条件的快讯。', 'empty'));
    more.hidden = !next;
    announcement.textContent = rows.length ? `已显示 ${rows.length} 条快讯` : '没有符合条件的快讯';
  } catch (error) {
    if (signal.aborted) return;
    handleFailure(error);
    if (!loaded) feed.replaceChildren();
    if (kind !== 'poll' || !loaded) {
      state.replaceChildren(node('span', errorMessage(error)), button('重试', () => load(kind === 'more' ? 'more' : 'replace')));
      announcement.textContent = errorMessage(error);
    }
  } finally {
    if (!signal.aborted) {
      busy = false;
      refresh.disabled = false;
      more.disabled = false;
      schedule();
    }
  }
}

function appendAi(item) {
  const points = item.ai?.summary?.points;
  const summary = Array.isArray(points) ? points.map(localized).filter(Boolean) : [];
  const overview = item.ai?.overview;
  const paragraphs = overview?.zh?.paragraphs?.length ? overview.zh.paragraphs : overview?.en?.paragraphs;
  if (!summary.length && !paragraphs?.length && overview?.status !== 'pending') return;
  const section = node('section');
  section.append(node('h2', 'AI 解读'), node('p', '由方程式新闻生成，仅供参考。', 'notice'));
  if (summary.length) {
    const list = node('ul');
    list.append(...summary.map(point => node('li', point)));
    section.append(list);
  }
  if (Array.isArray(paragraphs)) {
    for (const paragraph of paragraphs) {
      if (!text(paragraph?.text)) continue;
      section.append(node('p', paragraph.text));
      const sources = Array.isArray(paragraph.sources) ? paragraph.sources.map(text).filter(Boolean) : [];
      if (sources.length) section.append(node('p', sources.join(' · '), 'notice'));
    }
  }
  if (overview?.status === 'pending') section.append(node('p', 'AI 信息总览正在更新。', 'notice'));
  detail.append(section);
}

async function renderDetail(focus) {
  const signal = controller.signal;
  const back = internalLink('返回快讯', {...route, story: ''}, 'button');
  const heading = node('h1', '快讯详情');
  heading.tabIndex = -1;
  detail.replaceChildren(back, heading);
  if (focus) heading.focus();
  if (!validStory(route.story)) {
    detail.append(node('p', '快讯编号无效。'));
    return;
  }
  const loading = node('p', '正在读取快讯…');
  loading.setAttribute('role', 'status');
  detail.append(loading);
  try {
    const item = await getNews(route.story, signal);
    if (signal.aborted) return;
    loading.remove();
    const body = localized(item.content) || localized(item.text) || localized(item);
    const title = headline(item) || body.split(/\r?\n/, 1)[0] || '快讯详情';
    heading.textContent = title;
    document.title = title + ' · xiyu.news';
    const meta = metadata(item);
    meta.prepend(formatTime(item.time, true));
    detail.append(meta);
    const remaining = body.startsWith(title) ? body.slice(title.length).trim() : body;
    if (remaining) detail.append(node('p', remaining, 'body-copy'));
    if (Array.isArray(item.images)) {
      for (const image of item.images) {
        const src = safeUrl(typeof image === 'string' ? image : image?.url);
        if (!src) continue;
        const figure = node('figure');
        const img = node('img');
        img.src = src;
        img.alt = text(image?.alt) || '快讯配图';
        img.loading = 'lazy';
        figure.append(img);
        detail.append(figure);
      }
    }
    appendAi(item);
    const links = node('div', '', 'links');
    const source = safeUrl(item.source_url);
    const original = safeUrl(item.url) || 'https://eqn.news/';
    if (source && source !== original) links.append(link('阅读原始来源', source, 'button'));
    links.append(link('在方程式新闻查看', original, 'button'));
    detail.append(links);
  } catch (error) {
    if (signal.aborted) return;
    loading.textContent = errorMessage(error);
    if (error.status !== 404) {
      const retry = button('重试', () => renderDetail(true));
      if (error.status === 429) {
        retry.disabled = true;
        const timeout = setTimeout(() => { retry.disabled = false; }, Math.max(error.retryMs, 60_000));
        signal.addEventListener('abort', () => clearTimeout(timeout), {once: true});
      }
      detail.append(retry);
    }
  }
}

function render(focus = false) {
  clearTimeout(timer);
  controller?.abort();
  controller = new AbortController();
  route = parseRoute();
  document.title = 'xiyu.news · 加密快讯';
  byId('workspace').hidden = Boolean(route.story);
  byId('hero').hidden = Boolean(route.story);
  detail.hidden = !route.story;
  if (route.story) {
    renderDetail(focus);
    return;
  }
  busy = loaded = newItems = false;
  rows = [];
  next = newest = '';
  refresh.disabled = more.disabled = false;
  more.hidden = true;
  form.elements.query.value = route.query;
  form.elements.coin.value = route.coin;
  form.elements.coin.setCustomValidity('');
  state.replaceChildren();
  byId('feed-caption').textContent = route.query ? '搜索近 30 天 · 北京时间' : '北京时间 · 按发布时间倒序';
  renderChannels();
  if (focus) {
    byId('feed-title').tabIndex = -1;
    byId('feed-title').focus({preventScroll: true});
  }
  if (Date.now() >= retryAt) showSkeleton();
  else feed.replaceChildren();
  load();
}

function navigate(href, focus) {
  if (href !== location.href) history.pushState(null, '', href);
  render(focus);
  window.scrollTo(0, 0);
}

form.addEventListener('submit', event => {
  event.preventDefault();
  const query = form.elements.query.value.trim();
  const coin = form.elements.coin.value.trim().toUpperCase();
  if (coin && !validCoin(coin)) {
    form.elements.coin.setCustomValidity('请输入币种代码，例如 BTC。');
    form.elements.coin.reportValidity();
    return;
  }
  navigate(internalLink('', {...route, query, coin}).href, true);
});
form.elements.coin.addEventListener('input', () => form.elements.coin.setCustomValidity(''));
refresh.addEventListener('click', () => load());
more.addEventListener('click', () => load('more'));
window.addEventListener('popstate', () => render(true));
document.addEventListener('visibilitychange', schedule);

const today = byId('today');
today.dateTime = dayFormat.format(new Date());
today.textContent = today.dateTime + ' / UTC+8';
render();
listChannels(new AbortController().signal).then(result => {
  names = Object.keys(result).length ? {all: channels.all, ...result} : names;
  if (!route.story) renderChannels();
}).catch(() => { /* Documented channel keys stay available when discovery fails. */ });
