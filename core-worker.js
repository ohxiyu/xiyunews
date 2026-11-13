/* Read-only daily reader; retired admin and mutation routes remain closed. */
export function primaryHostRedirect(request) {
  const url=new URL(request.url);
  if(url.hostname==='www.xiyu.news'){url.hostname='xiyu.news';return Response.redirect(url.href,308);}
  return null;
}
const retired=/^\/(?:s(?:\/|$)|s\.html$|admin(?:\/|$)|api\/(?:admin|quick-posts|_telegram-group\.json|entities(?:\/|\.json|$))|oauth(?:\/|$)|quick-posts(?:\/|$)|developers?(?:\/|$)|mcp(?:\/|$)|weekly(?:[\/.]|$)|manifest\.webmanifest$|offline(?:\.html)?$|llms(?:-full)?\.txt$|openapi\.json$|\.well-known\/)/i;
const gone=()=>new Response('此功能已停用。',{status:410,headers:{'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store'}});
export default {
  async fetch(request,env) {
    const redirect=primaryHostRedirect(request);if(redirect)return redirect;
    const url=new URL(request.url);
    if(url.hostname==='bmt.news'||url.hostname==='www.bmt.news')return gone();
    let path;try{path=decodeURIComponent(url.pathname);}catch(_){return new Response(null,{status:400});}
    // Normalize repeated/trailing slashes before feature matching, including POSTs.
    path=path.replace(/\/+/g,'/');
    // Retired content products retain a useful, read-only archive destination.
    if(['GET','HEAD'].includes(request.method)&&/^\/(?:en\/)?(?:events|threads|entity|weekly)(?:\/|\.html?$|$)/i.test(path)){
      url.pathname='/history/';return Response.redirect(url.href,308);
    }
    if(['GET','HEAD'].includes(request.method)&&/^\/feed-(?:zh|en)\.xml$/.test(path)){
      url.pathname='/feed.xml';return Response.redirect(url.href,308);
    }
    if(/^\/feeds?(?:[\/.-]|$)/.test(path)&&path!=='/feed.xml')return gone();
    if(['GET','HEAD'].includes(request.method)&&/^\/api\/(?:events|entities|editions)(?:[\/.]|$)/.test(path)){
      url.pathname='/api/latest.json';return Response.redirect(url.href,308);
    }
    if(retired.test(path)||retired.test(path.replace(/^\/en(?=\/|$)/,'')||'/'))return gone();
    if(!['GET','HEAD'].includes(request.method))return new Response(null,{status:405,headers:{Allow:'GET, HEAD','Cache-Control':'no-store'}});
    let target=path;
    if(target==='/en'||target.startsWith('/en/'))target=target.replace(/^\/en(?:\/|$)/,'/');
    target=target.replace(/summary-en(?=(?:\.html)?\/?$)/,'summary-zh').replace(/(\/editions\/\d{4}-\d{2}-\d{2}\/)en\.html(?=\/?$)/,'$1zh.html');
    if(target!==path){url.pathname=target;return Response.redirect(url.href,308);}
    // A fresh cleanup worker replaces installed offline copies, even if they
    // have not visited the new page yet. No network interception remains.
    if(path==='/service-worker.js')return new Response("self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',event=>event.waitUntil(Promise.all([self.registration.unregister(),caches.keys().then(keys=>Promise.all(keys.filter(k=>k==='bmt-reader-pages-v1'||k==='bmt-reader-assets-v2-xiyu').map(k=>caches.delete(k))))])));",{headers:{'Content-Type':'application/javascript','Cache-Control':'no-store','Service-Worker-Allowed':'/'}});
    const response=await env.ASSETS.fetch(request);
    const headers=new Headers(response.headers);
    headers.set('X-Content-Type-Options','nosniff');
    headers.set('Referrer-Policy','strict-origin-when-cross-origin');
    // No worker cache survives a source/artifact deployment. Browser clients
    // revalidate HTML and JSON, including ordinary URLs without a cache nonce.
    if(/(?:\.html?$|\.json$|\/$|\/summary-zh$)/.test(path))headers.set('Cache-Control','no-cache, max-age=0, must-revalidate');
    return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
  }
};
