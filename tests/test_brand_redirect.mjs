import test from 'node:test';
import assert from 'node:assert/strict';
import {handleRequest} from '../docs/_worker.js';

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
