const base = 'https://api.eqn.news/public/v1';
export const channels = Object.fromEntries([
  ['all', '全部快讯'], ['main', '主频道'], ['tradfi', '传统金融'],
  ['binance', '币安公告'], ['korea', '韩国交易所'], ['pricechange', '价格异动'],
  ['oi', '持仓异动'], ['major', '大型交易所'], ['tier2', '二线交易所'],
  ['tier3', '三线交易所'], ['alpha', '币安 Alpha'], ['cz', 'CZ 动态'],
  ['earn', '理财公告'], ['hl', 'Hyperliquid'], ['tfmoves', '传统金融异动'],
]);

export const text = value => typeof value === 'string' ? value.trim() : '';
export const localized = item => text(item?.zh) || text(item?.en);
export const validStory = no => /^[1-9]\d{0,15}$/.test(no ?? '') && Number.isSafeInteger(Number(no));
export const validChannel = key => /^[a-z][a-z0-9_-]{0,39}$/.test(key ?? '');
export const validCoin = coin => /^[a-z0-9][a-z0-9._-]{0,23}$/i.test(coin ?? '');
export const headline = item => localized(item).split(/\r?\n/, 1)[0];

export function safeUrl(value) {
  try {
    const url = new URL(value);
    if (['https:', 'http:'].includes(url.protocol) && !url.username && !url.password) return url.href;
  } catch { /* Missing or invalid external link. */ }
  return '';
}

export class ApiError extends Error {
  constructor(status, retryAfter) {
    super(`Equation News returned ${status}`);
    this.status = status;
    const seconds = Number(retryAfter);
    this.retryMs = retryAfter && Number.isFinite(seconds)
      ? Math.max(0, seconds * 1000)
      : Math.max(0, Date.parse(retryAfter) - Date.now()) || 0;
  }
}

async function request(path, params, signal) {
  const query = new URLSearchParams(params);
  const url = new URL(path + (query.size ? '?' + query : ''), base + '/');
  // Browser revalidation uses the upstream ETag without a custom CORS header.
  const response = await fetch(url, {
    cache: 'no-cache',
    signal: AbortSignal.any([signal, AbortSignal.timeout(12_000)]),
  });
  if (!response.ok) throw new ApiError(response.status, response.headers.get('Retry-After'));
  return response.json();
}

export async function listNews({channel, query, coin}, before, signal) {
  const params = {channel, limit: '20'};
  if (query) params.query = query;
  if (coin) params.coin = coin;
  if (before) params.before = before;
  const page = await request('news', params, signal);
  if (!Array.isArray(page?.items)) throw new TypeError('Invalid news list');
  return {
    items: page.items.filter(item => validStory(item?.no) && headline(item)),
    cursor: text(page.next_cursor),
  };
}

export async function listChannels(signal) {
  const result = await request('channels', {}, signal);
  const items = Array.isArray(result) ? result : result?.channels ?? result?.items;
  if (!Array.isArray(items)) throw new TypeError('Invalid channel list');
  return Object.fromEntries(items.flatMap(item => {
    const key = item?.key;
    const name = localized(item) || text(item?.name_zh) || text(item?.name_en) || text(item?.name) || channels[key] || key;
    return validChannel(key) && typeof name === 'string' ? [[key, name]] : [];
  }));
}

export async function getNews(no, signal) {
  const item = await request('news/' + no, {}, signal);
  if (String(item?.no) !== no) throw new TypeError('Invalid story');
  return item;
}
