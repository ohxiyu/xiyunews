import test from 'node:test';
import assert from 'node:assert/strict';
import {handleRequest} from '../docs/_worker.js';

for (const protocol of ['http', 'https']) {
  for (const path of ['/', '/2026/10/13/summary-zh?ref=telegram&x=a%2Fb', '/api/latest.json?x=1&x=2', '/feed-zh.xml', '/health', '/s/?next=edit']) {
    test(`www canonical redirect preserves ${protocol} ${path} before assets/auth`, async () => {
      const response = await handleRequest(new Request(`${protocol}://www.xiyu.news${path}`), {
        ASSETS: {fetch() { throw new Error('Redirect must not access assets'); }}
      });
      assert.equal(response.status, 301);
      assert.equal(response.headers.get('Location'), `https://xiyu.news${path}`);
    });
  }
}

for (const host of ['bmt.news', 'www.bmt.news']) {
  for (const path of ['/x?y=1', '/api/latest.json?source=agent', '/feed.xml', '/s/', '/openapi.json', '/llms.txt', '/2026/10/01/summary-zh.html']) {
    test(`${host}${path} retires the old entry without redirect or origin access`, async () => {
      const response = await handleRequest(new Request(`https://${host}${path}`), {
        ASSETS: {fetch() { throw new Error('Retired hosts must not access auth, assets or caches'); }}
      });
      assert.equal(response.status, 410);
      assert.equal(response.headers.get('Location'), null);
      assert.equal(response.headers.get('Cache-Control'), 'no-store');
      assert.equal(response.headers.get('X-Robots-Tag'), 'noindex, nofollow');
    });
  }
}
test('A similar hostname is not treated as the old brand domain', async () => {
  const response = await handleRequest(new Request('https://bmt.news.example/robots.txt'), {
    ASSETS: {fetch: async () => new Response('robots', {status: 200})}
  });
  assert.equal(response.status, 200);
});

for (const host of ['bmt.news', 'www.bmt.news']) {
  test(`${host} cannot reactivate redirects through the obsolete deployment switch`, async () => {
    for (const setting of ['false', 'true', undefined]) {
      const response = await handleRequest(new Request(`https://${host}/api/admin/quick-posts`), {
        LEGACY_REDIRECT_ENABLED: setting,
        ASSETS: {fetch() { throw new Error('Old admin entry is retired'); }}
      });
      assert.equal(response.status, 410);
      assert.equal(response.headers.get('Location'), null);
    }
  });
}
