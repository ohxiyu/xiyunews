import test from 'node:test';
import assert from 'node:assert/strict';
import {handleRequest} from '../docs/_worker.js';

for (const host of ['bmt.news', 'www.bmt.news']) {
  for (const path of ['/x?y=1', '/api/latest.json?source=agent', '/feed.xml', '/s/', '/openapi.json', '/llms.txt', '/2026/10/01/summary-zh.html']) {
    test(`${host}${path} preserves the full URL in a 301`, async () => {
      const response = await handleRequest(new Request(`https://${host}${path}`), {
        ASSETS: {fetch() { throw new Error('Legacy redirects must precede auth, assets and caches'); }}
      });
      assert.equal(response.status, 301);
      assert.equal(response.headers.get('Location'), 'https://xiyu.news' + path);
    });
  }
}
test('A similar hostname is not treated as the old brand domain', async () => {
  const response = await handleRequest(new Request('https://bmt.news.example/robots.txt'), {
    ASSETS: {fetch: async () => new Response('robots', {status: 200})}
  });
  assert.equal(response.status, 200);
});
