import {env} from "cloudflare:test";
import {afterEach,describe,expect,it,vi} from "vitest";
import {CONFIG_KEY,STATUS_KEY,eventPlan,runGroupNews,groupStatus,type Snapshot,type Event} from "../src/group-news";
import type {UnifiedEnv} from "../src/unified";
import unified from "../src/unified";

const NOW=Date.parse("2026-10-12T16:00:00+08:00"), TODAY="2026-10-12";
let serial=0;
const e1:Event={id:"evt_test01",focus:true,title:"测试 <事件>",status:"developing",status_label:"进展中",
  state:"当前已报道状态",background:"已报道背景",latest_at:"2026-10-12T08:00:00+08:00",
  updates:[{id:"upd_test01",date:TODAY,kind:"确认",text:"新增事实 & 引用",sources:[{url:"https://example.com/report",label:"原始来源"}]}]};
const snap=():Snapshot=>({version:1,date:TODAY,artifact:"a".repeat(40),feed_parts:["<b>每日信息流</b>"],events:[structuredClone(e1)]});
function fixture(snapshot=snap()) {
  const cfg={enabled:true,chat_id:"-100"+String(1000000+(++serial)),feed_topic:100,events_topic:102,
    start_date:TODAY,expected_bot:"xiyunewsbot"};
  const observer=new Map<string,string>();
  const e={...env,ENABLE_DISPATCHER:"true",TELEGRAM_BOT_TOKEN:"test-group-token",SITE_ARTIFACT_COMMIT:snapshot.artifact,
    STATE:{get:vi.fn(async(key:string)=>key===CONFIG_KEY?cfg:null),
      put:vi.fn(async(key:string,value:string)=>{observer.set(key,value);})},
    ASSETS:{fetch:vi.fn(async(req:Request)=>{
      if(req.url.endsWith("_telegram-group.json")) return Response.json(snapshot);
      if(req.url.endsWith("latest.json")) return Response.json({date:snapshot.date});
      return new Response(`<div data-latest-edition-date="${snapshot.date}"></div>`);
    })}} as unknown as UnifiedEnv;
  const sends:Record<string,unknown>[]=[];
  let behaviour:"ok"|"timeout"|"event-timeout"|"429"|"403"|"invalid"|"wrong-bot"="ok";
  vi.stubGlobal("fetch",vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
    if(String(input).endsWith("getMe")) return Response.json({ok:true,result:{username:behaviour==="wrong-bot"?"wrongbot":"xiyunewsbot"}});
    const body=JSON.parse(String(init?.body)); sends.push(body);
    if(behaviour==="timeout" && body.message_thread_id===100) throw new Error("test-group-token must not leak");
    if(behaviour==="event-timeout" && body.message_thread_id===102) throw new Error("unknown event result");
    if(behaviour==="429" && body.message_thread_id===100) return Response.json({ok:false,error_code:429,parameters:{retry_after:600}}, {status:429});
    if(behaviour==="403" && body.message_thread_id===100) return Response.json({ok:false,error_code:403},{status:403});
    if(behaviour==="invalid" && body.message_thread_id===100) return new Response("not-json");
    return Response.json({ok:true,result:{message_id:serial*100+sends.length,chat:{id:Number(cfg.chat_id)},message_thread_id:body.message_thread_id}});
  }));
  return {e,cfg,sends,snapshot,observer,set:(b:typeof behaviour)=>{behaviour=b;}};
}
const tick=(e:UnifiedEnv,now=NOW)=>runGroupNews(e,now,async()=>{});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});

describe("isolated daily group delivery",()=>{
  it("routes both topics once and keeps receipts; repeated ticks do not send",async()=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);
    const f=fixture(); await tick(f.e); await tick(f.e);
    expect(f.sends.map(p=>p.message_thread_id)).toEqual([100,102]);
    expect(f.sends.every(p=>p.chat_id===f.cfg.chat_id)).toBe(true);
    expect(await groupStatus(f.e,TODAY)).toMatchObject({feed:{status:"sent"},events:{status:"sent"}});
    expect(JSON.parse(f.observer.get(STATUS_KEY)!)).toMatchObject({events:{receipts:[{status:"sent",message_id:expect.any(Number)}]}});
    expect(f.e.STATE.put).toHaveBeenCalledOnce();
  });
  it("does not send old/future/mixed-build snapshots or before activation",async()=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);
    for(const changed of [{date:"2026-10-11"},{date:"2026-10-13"},{artifact:"b".repeat(40)}]){
      const f=fixture();Object.assign(f.snapshot,changed);await tick(f.e);expect(f.sends).toHaveLength(0);
    }
    const f=fixture();f.cfg.start_date="2026-10-13";await tick(f.e);expect(f.sends).toHaveLength(0);
  });
  it("does not send before the published homepage and API agree",async()=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);
    const f=fixture();f.e.ASSETS.fetch=vi.fn(async(req:Request)=>req.url.endsWith("_telegram-group.json")?
      Response.json(f.snapshot):Response.json({date:"2026-10-11"}));
    await tick(f.e);expect(f.sends).toHaveLength(0);
  });
  it("does not overlap a live group lease",async()=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);
    const f=fixture(),gate=f.e.RECOVERY_GATE.getByName(`telegram-group-v1:${f.cfg.chat_id}:100:102`);
    const owner=await gate.claim(NOW);await tick(f.e);expect(f.sends).toHaveLength(0);await gate.release(owner!);
    await tick(f.e);expect(f.sends).toHaveLength(2);
  });
  it.each(["timeout","invalid"] as const)("keeps %s unknown and independent event delivery succeeds",async(mode)=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);
    const f=fixture();f.set(mode);await tick(f.e);f.set("ok");await tick(f.e,NOW+300000);
    expect(f.sends).toHaveLength(2);
    expect(await groupStatus(f.e,TODAY)).toMatchObject({feed:{status:"unknown"},events:{status:"sent"}});
  });
  it("obeys retry_after and does not repeat the successful other topic",async()=>{
    const clock=vi.spyOn(Date,"now").mockReturnValue(NOW);
    const f=fixture();f.set("429");await tick(f.e);f.set("ok");clock.mockReturnValue(NOW+300000);
    await tick(f.e,NOW+300000);expect(f.sends).toHaveLength(2);
    clock.mockReturnValue(NOW+601000);await tick(f.e,NOW+601000);expect(f.sends).toHaveLength(3);
    expect(await groupStatus(f.e,TODAY)).toMatchObject({feed:{status:"sent"},events:{status:"sent"}});
  });
  it("does not keep retrying a definite permission rejection",async()=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);
    const f=fixture();f.set("403");await tick(f.e);await tick(f.e,NOW+300000);
    expect(f.sends).toHaveLength(2);expect(await groupStatus(f.e,TODAY)).toMatchObject({feed:{status:"failed"},events:{status:"sent"}});
  });
  it("refuses a different bot without sending and without logging secrets",async()=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);const warn=vi.spyOn(console,"warn").mockImplementation(()=>{});
    const f=fixture();f.set("wrong-bot");await tick(f.e);expect(f.sends).toHaveLength(0);
    expect(JSON.stringify(warn.mock.calls)).not.toContain("test-group-token");
  });
  it("freezes multipart content and sends at most two parts per topic each tick",async()=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);const f=fixture();f.snapshot.feed_parts=["one","two","three"];
    await tick(f.e);expect(f.sends.filter(p=>p.message_thread_id===100).map(p=>p.text)).toEqual(["one","two"]);
    f.snapshot.feed_parts=["changed"];
    await tick(f.e,NOW+300000);expect(f.sends.filter(p=>p.message_thread_id===100).map(p=>p.text)).toEqual(["one","two","three"]);
  });
  it("does not expose the internal snapshot or a public sending endpoint",async()=>{
    const f=fixture();const response=await unified.fetch(new Request("https://xiyu.news/api/_telegram-group.json"),f.e,{waitUntil:vi.fn()} as unknown as ExecutionContext);
    expect(response.status).toBe(404);expect(f.e.ASSETS.fetch).not.toHaveBeenCalled();expect(f.sends).toHaveLength(0);
  });
  it("does not deliver while the unified project is paused",async()=>{
    const f=fixture();f.e.ENABLE_DISPATCHER="false";await tick(f.e);expect(f.sends).toHaveLength(0);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("does not replay unknown first-day event nodes on the next day",async()=>{
    const clock=vi.spyOn(Date,"now").mockReturnValue(NOW),f=fixture();f.set("event-timeout");await tick(f.e);
    expect(await groupStatus(f.e,TODAY)).toMatchObject({events:{status:"unknown"}});
    f.snapshot.date="2026-10-13";f.set("ok");clock.mockReturnValue(NOW+86400000);
    await tick(f.e,NOW+86400000);
    expect(f.sends.filter(p=>p.message_thread_id===102)).toHaveLength(1);
    expect(await groupStatus(f.e,"2026-10-13")).toMatchObject({feed:{status:"sent"},events:{status:"skipped"}});
  });
  it("limits definite temporary errors to three attempts",async()=>{
    const clock=vi.spyOn(Date,"now").mockReturnValue(NOW),f=fixture();f.set("429");
    for(let n=0;n<4;n++){clock.mockReturnValue(NOW+n*601000);await tick(f.e,NOW+n*601000);}
    expect(f.sends.filter(p=>p.message_thread_id===100)).toHaveLength(3);
    expect(await groupStatus(f.e,TODAY)).toMatchObject({feed:{status:"failed"},events:{status:"sent"}});
  });
  it("does not retry an in-flight receipt recovered after a crash",async()=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);
    const f=fixture(),gate=f.e.RECOVERY_GATE.getByName(`telegram-group-v1:${f.cfg.chat_id}:100:102`);
    const owner=await gate.claim(NOW);
    await gate.groupWrite(owner!,`tg:${TODAY}:feed`,JSON.stringify({date:TODAY,parts:["claimed"],
      receipts:[{status:"sending",attempts:1}],status:"pending"}),NOW);await gate.release(owner!);
    await tick(f.e);expect(f.sends.map(p=>p.message_thread_id)).toEqual([102]);
    expect(await groupStatus(f.e,TODAY)).toMatchObject({feed:{status:"unknown"}});
  });
  it("isolates event formatting failure without truncating facts or blocking feed",async()=>{
    vi.spyOn(Date,"now").mockReturnValue(NOW);const f=fixture(),event=f.snapshot.events[0]!;
    event.background="&".repeat(420);event.state="&".repeat(420);event.updates[0]!.text="&".repeat(420);
    await tick(f.e);expect(f.sends.map(p=>p.message_thread_id)).toEqual([100]);
    expect(await groupStatus(f.e,TODAY)).toMatchObject({events:{status:"failed",reason:"rendering_failed"},feed:{status:"sent"}});
  });
});

describe("material event deltas",()=>{
  it("bootstrap is labeled a current overview, not today's invented progress",()=>{
    const s=snap();s.events[0]!.updates[0]!.date="2026-10-10";
    const p=eventPlan(s,null);expect(p.parts[0]).toContain("当前追踪概览");expect(p.parts[0]).toContain("2026-10-10");
    expect(p.parts[0]).toContain("&lt;事件&gt;");expect(p.parts[0]).toContain("&amp; 引用");
  });
  it("ranking, source repetition and wording edits are not new progress",()=>{
    const s=snap(),first=eventPlan(s,null);s.events[0]!.state="仅调整措辞";
    expect(eventPlan(s,first.baseline).parts).toEqual([]);
    s.events[0]!.latest_at="2026-10-12T09:00:00+08:00";
    expect(eventPlan(s,first.baseline).parts).toEqual([]);
  });
  it("shows real new nodes and the last confirmed delivered state",()=>{
    const s=snap(),first=eventPlan(s,null);s.events[0]!.updates[0]!.id="upd_test02";
    s.events[0]!.latest_at="2026-10-12T09:00:00+08:00";s.events[0]!.state="新的状态";
    const p=eventPlan(s,first.baseline);expect(p.parts[0]).toContain("之前：当前已报道状态");expect(p.parts[0]).toContain("现在：新的状态");
  });
  it("wraps up a previously tracked event even after leaving focus",()=>{
    const s=snap(),first=eventPlan(s,null);s.events[0]!.status="resolved";s.events[0]!.status_label="已解决";s.events[0]!.focus=false;
    const ending=eventPlan(s,first.baseline);expect(ending.parts[0]).toContain("已解决");
    expect(eventPlan(s,ending.baseline).parts).toEqual([]);
  });
  it("a newly focused old event does not become new progress solely from rank",()=>{
    const s=snap();s.events[0]!.focus=false;s.events[0]!.updates[0]!.date="2026-10-10";
    const first=eventPlan(s,null);s.events[0]!.focus=true;
    expect(eventPlan(s,first.baseline).parts).toEqual([]);
  });
});
