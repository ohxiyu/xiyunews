import assert from 'node:assert/strict';
import {getNews, listChannels, listNews} from '../site/assets/eqn.js';

// Send the production site's Origin and verify that the same responses are
// readable by the browser. Node fetch alone does not enforce CORS.
const origin = 'https://xiyu.news';
const fetchUpstream = globalThis.fetch;
globalThis.fetch = async (url, options) => {
  const response = await fetchUpstream(url, {...options, headers: {Origin: origin}});
  if (response.ok) {
    const allowed = response.headers.get('access-control-allow-origin');
    assert.ok(allowed === '*' || allowed === origin, 'Upstream CORS must allow xiyu.news');
  }
  return response;
};

const signal = new AbortController().signal;
const channel = 'all';
const [channels, news] = await Promise.all([
  listChannels(signal),
  listNews({channel}, '', signal),
]);
assert.ok(Object.keys(channels).length > 0, 'Channel endpoint returned no usable channels');
assert.ok(news.items.length, 'Feed endpoint returned no usable news');
const {no} = news.items[0];
const item = await getNews(String(no), signal);
assert.ok(item.zh || item.en || item.content || item.text, 'Detail endpoint returned no text');
console.log('Equation News channels, list, detail and production-origin CORS verified.');
