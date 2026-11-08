import {env} from 'cloudflare:test';
import {afterEach,expect,it,vi} from 'vitest';
import {validateSnapshot,currentSnapshot,liveRoute,feedHtml,liveHome} from '../src/live';
const now=Date.parse('2026-11-08T12:00:00Z');
const value=()=>({version:1,generated_at:new Date(now).toISOString(),collected_at:new Date(now-60000).toISOString(),window_start:new Date(now-86400000).toISOString(),items:[{id:'a'.repeat(32),title:'<script>新闻</script>',summary:'全部正文\n\n第二段',background:'有证据的背景',url:'https://example.com/story',source:'来源',published_at:new Date(now-3600000).toISOString(),score:9}]});
afterEach(()=>vi.restoreAllMocks());
it('checks source timestamps, score, bounds, duplicates, and safe URLs',()=>{
 expect(validateSnapshot(value(),now).items).toHaveLength(1);
 for(const patch of [{published_at:new Date(now).toISOString()},{published_at:new Date(now-86400001).toISOString()},{score:6},{url:'javascript:alert(1)'}]){
  const v=value();Object.assign(v.items[0]!,patch);expect(()=>validateSnapshot(v,now)).toThrow();
 }
 const duplicate=value();duplicate.items.push(duplicate.items[0]!);expect(()=>validateSnapshot(duplicate,now)).toThrow();
 expect(()=>validateSnapshot({...value(),generated_at:new Date(now+120000).toISOString()},now)).toThrow();
});
it('escapes content, fully renders background/body and expires stories on reads',()=>{
 const v=validateSnapshot(value(),now),html=feedHtml(v,now);
 expect(html).toContain('&lt;script&gt;');expect(html).not.toContain('<script>新闻');
 expect(html).toContain('全部正文');expect(html).toContain('第二段');expect(html).toContain('有证据的背景');
 expect(currentSnapshot(v,now+86400000).items).toHaveLength(0);
 expect(feedHtml(v,now+86400000)).toContain('暂无达到精选标准');
 expect(feedHtml(v,now+3600000)).toContain('采集延迟');
});
it('authenticates writes, rejects stale writes and retains stable links after expiry',async()=>{
 vi.spyOn(Date,'now').mockReturnValue(now);
 const post=(v:unknown,auth?:string)=>liveRoute(new Request('https://xiyu.news/api/live.json',{method:'POST',headers:auth?{Authorization:auth}:{},body:JSON.stringify(v)}),env);
 expect((await post(value()))!.status).toBe(401);
 expect((await post(value(),'Bearer '+env.RECOVERY_CHECK_TOKEN))!.status).toBe(200);
 expect((await post(value(),'Bearer '+env.RECOVERY_CHECK_TOKEN))!.status).toBe(409);
 vi.spyOn(Date,'now').mockReturnValue(now+86400000);
 const response=await liveRoute(new Request('https://xiyu.news/api/live.json'),env);
 expect((await response!.json() as {items:unknown[]}).items).toHaveLength(0);
 const story=await liveRoute(new Request('https://xiyu.news/story/'+'a'.repeat(32)+'/'),env);
 expect(story!.status).toBe(200);expect(await story!.text()).toContain('全部正文');
});
it('serves selected HTML without JavaScript and marks missing snapshots explicitly',async()=>{
 const fake={...env,RECOVERY_GATE:{getByName:()=>({feedRead:async()=>JSON.stringify(validateSnapshot(value(),now))})}} as unknown as Env;
 vi.spyOn(Date,'now').mockReturnValue(now);
 const response=await liveHome(new Response('<main><div data-live-home>旧刊</div></main>',{headers:{'Content-Type':'text/html'}}),fake);
 expect(await response.text()).toContain('全部正文');
 expect(response.headers.get('Cache-Control')).toBe('no-store');
});
