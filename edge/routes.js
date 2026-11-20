const gone = () => new Response('此功能已停用。', {
  status: 410,
  headers: {'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store'},
});

const retired = /^\/(?:s(?:\/|$)|s\.html$|admin(?:\/|$)|oauth(?:\/|$)|quick-posts(?:\/|$)|developers?(?:\/|$)|mcp(?:\/|$)|manifest\.webmanifest$|offline(?:\.html)?$|llms(?:-full)?\.txt$|openapi\.json$|\.well-known\/|internal\/publication-state(?:\/|$)|api\/(?:admin|quick-posts|_telegram-group\.json)(?:[\/.]|$))/i;
const oldProducts = /^\/(?:en\/)?(?:events|threads|entity|weekly|sources)(?:[\/.]|$)/i;
const oldFeeds = /^\/(?:en\/)?feeds?(?:[\/.-]|$)/;
const rss = 'https://api.eqn.news/public/rss?ch=all&lang=';
const cleanup = "self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(Promise.all([self.registration.unregister(),caches.keys().then(keys=>Promise.all(keys.filter(k=>k==='bmt-reader-pages-v1'||k==='bmt-reader-assets-v2-xiyu').map(k=>caches.delete(k))))])));";

export async function serve(request, env) {
  const url = new URL(request.url);
  if (url.hostname === 'www.xiyu.news') {
    url.hostname = 'xiyu.news';
    return Response.redirect(url, 308);
  }
  if (['bmt.news', 'www.bmt.news'].includes(url.hostname)) return gone();
  let path;
  try {
    path = decodeURIComponent(url.pathname).replace(/\/{2,}/g, '/');
  } catch {
    return new Response(null, {status: 400});
  }
  const withoutEnglish = path.replace(/^\/en(?:\/|$)/, '/');
  if (retired.test(withoutEnglish) || path === '/publication/check') return gone();
  if (!['GET', 'HEAD'].includes(request.method)) {
    return new Response(null, {status: 405, headers: {Allow: 'GET, HEAD', 'Cache-Control': 'no-store'}});
  }

  const redirect = (target, status = 308) => {
    url.pathname = target;
    return Response.redirect(url, status);
  };
  if (oldProducts.test(path) || path === '/history.html') return redirect('/history/');
  if (/^\/(?:en\/)?feed(?:-(?:zh|en))?\.xml$/.test(path)) {
    return Response.redirect(rss + (path.includes('-en') || path.startsWith('/en/') ? 'en' : 'zh'), 307);
  }
  if (oldFeeds.test(path)) return gone();
  if (/^\/api\/(?:live\.json|(?:events|entities|editions)(?:[\/.]|$))/.test(path)) {
    return redirect('/api/latest.json');
  }
  const story = /^\/story\/([a-f0-9]{32})\/?$/.exec(path);
  if (story) {
    try {
      const value = await env.RECOVERY_GATE.getByName('rolling-news').legacyStory(story[1]);
      const target = new URL(JSON.parse(value)?.url);
      if (['https:', 'http:'].includes(target.protocol) && !target.username && !target.password) {
        return Response.redirect(target, 308);
      }
    } catch { /* The old entry may be absent. */ }
    return redirect('/history/', 307);
  }

  const target = withoutEnglish.replace(/summary-en(?=(?:\.html)?\/?$)/, 'summary-zh')
    .replace(/(\/editions\/\d{4}-\d{2}-\d{2}\/)en\.html(?=\/?$)/, '$1zh.html');
  if (target !== path) return redirect(target);
  if (path === '/service-worker.js') {
    return new Response(request.method === 'HEAD' ? null : cleanup, {
      headers: {'Content-Type': 'application/javascript', 'Cache-Control': 'no-store', 'Service-Worker-Allowed': '/'},
    });
  }
  if (path === '/health' || path === '/ready') {
    const headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-store'};
    return new Response(request.method === 'HEAD' ? null : JSON.stringify({
      status: 'ok', service: 'xiyu.news', product: 'newswire', provider: 'Equation News',
      commit: env.SITE_SOURCE_COMMIT ?? null,
    }), {headers});
  }
  const response = await env.ASSETS.fetch(request);
  const headers = new Headers(response.headers);
  headers.set('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' https:; connect-src https://api.eqn.news; base-uri 'none'; form-action 'self'; frame-ancestors 'none'");
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  headers.set('Cache-Control', 'no-cache, max-age=0, must-revalidate');
  return new Response(response.body, {status: response.status, headers});
}
