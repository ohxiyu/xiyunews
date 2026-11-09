/** Read-only destinations for bookmarks from the retired rolling feed. */
export async function legacyRoute(request:Request,env:Env):Promise<Response|null>{
  const url=new URL(request.url),match=/^\/story\/([a-f0-9]{32})\/?$/.exec(url.pathname);
  if(url.pathname!=="/api/live.json"&&!match)return null;
  if(!["GET","HEAD"].includes(request.method))return new Response(null,{status:410,headers:{"Cache-Control":"no-store"}});
  if(url.pathname==="/api/live.json"){url.pathname="/api/latest.json";return Response.redirect(url.href,308);}
  let target="https://xiyu.news/history/";
  try{
    const raw=await env.RECOVERY_GATE.getByName("rolling-news").legacyStory(match![1]!);
    if(raw){
      const source=new URL((JSON.parse(raw) as {url:string}).url);
      if(["https:","http:"].includes(source.protocol)&&!source.username&&!source.password)target=source.href;
    }
  }catch{/* A retired bookmark always keeps a readable archive destination. */}
  return Response.redirect(target,308);
}
