import assert from 'node:assert/strict';
import {readFile, readdir} from 'node:fs/promises';
import test from 'node:test';
import {serve} from '../edge/routes.js';
import {ApiError, getNews, listChannels, listNews, safeUrl} from '../site/assets/eqn.js';

test('Equation News requests use the documented paths, filters, and opaque cursor', async t => {
  const fixture = {no: 6311, zh: '测试公告', en: 'Fixture only'};
  const replies = [{items: [fixture, {no: -1, zh: 'invalid'}], next_cursor: 'opaque+cursor'}, {channels: [{key: 'main', name_zh: '主频道'}]}, fixture];
  const calls = t.mock.method(globalThis, 'fetch', async () => Response.json(replies.shift()));
  const signal = new AbortController().signal;
  const criteria = {channel: 'binance', query: '现货 & 交易', coin: 'BTC'};
  assert.deepEqual(await listNews(criteria, 'opaque+previous', signal), {items: [fixture], cursor: 'opaque+cursor'});
  assert.deepEqual(await listChannels(signal), {main: '主频道'});
  assert.deepEqual(await getNews('6311', signal), fixture);
  const urls = calls.mock.calls.map(call => call.arguments[0]);
  assert.equal(urls[0].origin, 'https://api.eqn.news');
  assert.deepEqual(urls.map(url => url.pathname), ['/public/v1/news', '/public/v1/channels', '/public/v1/news/6311']);
  assert.deepEqual(Object.fromEntries(urls[0].searchParams), {...criteria, limit: '20', before: 'opaque+previous'});
  assert.equal(safeUrl('javascript:alert(1)'), '');
  assert.equal(safeUrl('https://user@example.com'), '');
  assert.equal(safeUrl('https://example.com/'), 'https://example.com/');
});

test('upstream rate limits carry retry timing', async t => {
  t.mock.method(globalThis, 'fetch', async () =>
    new Response(null, {status: 429, headers: {'Retry-After': '15'}}));
  await assert.rejects(listNews({channel: 'all'}, '', new AbortController().signal), error => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.retryMs, 15_000);
    return true;
  });
});

test('worker preserves routes, closes writes and keeps legacy storage read-only', async () => {
  const id = 'a'.repeat(32);
  const env = {
    ASSETS: {fetch: async () => new Response('asset')},
    RECOVERY_GATE: {
      getByName(name) {
        assert.equal(name, 'rolling-news');
        return {legacyStory: async key => key === id ? JSON.stringify({url: 'https://example.com/story'}) : null};
      },
    },
  };
  const handle = (path, opts) => serve(new Request('https://xiyu.news' + path, opts), env);
  assert.equal((await handle('/feed-en.xml')).headers.get('location'), 'https://api.eqn.news/public/rss?ch=all&lang=en');
  assert.equal((await handle('/2026/11/19/summary-en.html')).headers.get('location'), 'https://xiyu.news/2026/11/19/summary-zh.html');
  assert.equal((await handle('/en/threads/old')).headers.get('location'), 'https://xiyu.news/history/');
  assert.equal((await handle('/api/live.json')).headers.get('location'), 'https://xiyu.news/api/latest.json');
  assert.equal((await handle('/story/' + id)).headers.get('location'), 'https://example.com/story');
  assert.equal((await handle('/story/' + 'b'.repeat(32))).headers.get('location'), 'https://xiyu.news/history/');
  assert.equal((await handle('/internal//publication-state/lease', {method: 'POST'})).status, 410);
  assert.equal((await handle('/', {method: 'POST'})).status, 405);
  assert.match((await handle('/')).headers.get('content-security-policy'), /connect-src https:\/\/api\.eqn\.news/);
});

test('build preserves all frozen editions and the original compatibility payload', async () => {
  const snapshot = process.env.EDITION_SNAPSHOT_DIR ?? '.edition-snapshot';
  const read = path => readFile(path, 'utf8');
  assert.equal(await read('dist/api/latest.json'), await read(snapshot + '/api/latest.json'));
  const editions = (await readdir(snapshot + '/_posts')).flatMap(name => /^(\d{4}-\d{2}-\d{2})-summary-zh\.md$/.exec(name)?.[1] ?? []);
  assert.ok(editions.length >= 99);
  const index = await read('dist/history/index.html');
  for (const date of editions) {
    const path = '/' + date.replaceAll('-', '/') + '/summary-zh.html';
    assert.ok(index.includes(path), date);
    const page = await read('dist' + path);
    const source = await read(snapshot + '/editions/' + date + '/zh.html');
    for (const [, anchor] of source.matchAll(/\bid="([^"]+)"/g)) {
      assert.ok(page.includes('id="' + anchor + '"'), date + ' · ' + anchor);
    }
  }
  assert.match(await read('dist/2026/07/26/summary-zh.html'), /id="item-1"/);
  assert.match(await read('dist/2026/11/20/summary-zh.html'), /id="zh-2026-11-20-item-1"/);
});
