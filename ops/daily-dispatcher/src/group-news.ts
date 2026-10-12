import type {UnifiedEnv} from "./unified";

export const CONFIG_KEY = "telegram-group:v1:config";
export const STATUS_KEY = "telegram-group:v1:last-status";
type Config = {enabled: true; chat_id: string; feed_topic: number; events_topic: number;
  start_date: string; expected_bot: "xiyunewsbot"};
type Update = {id: string; date: string; kind: string; text: string;
  sources: {url: string; label: string}[]};
export type Event = {id: string; focus: boolean; title: string; status: string; status_label: string;
  state: string; background: string; latest_at: string; updates: Update[]};
export type Snapshot = {version: number; date: string; artifact: string; feed_parts: string[]; events: Event[]};
type Known = {status: string; state: string; latest_at: string; ids: string[]; tracked: boolean;
  delivered_state?: string; delivered_status?: string};
type Baseline = Record<string, Known>;
type Receipt = {status: "pending" | "sending" | "sent" | "unknown" | "failed";
  attempts: number; next_at?: number; message_id?: number; sent_at?: number; code?: number};
type Job = {date: string; parts: string[]; receipts: Receipt[]; baseline?: Baseline;
  reason?: "rendering_failed";
  status: "pending" | "sent" | "skipped" | "unknown" | "failed"};
type Gate = ReturnType<UnifiedEnv["RECOVERY_GATE"]["getByName"]>;
const esc = (s: string) => s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const closed = (s: string) => s === "closed" || s === "resolved";
const day = (now: number) => new Date(now + 8*3600_000).toISOString().slice(0,10);
const read = async <T>(gate: Gate, key: string): Promise<T | null> => {
  const value = await gate.groupRead(key);
  return value ? JSON.parse(value) as T : null;
};
const write = (gate: Gate, token: string, key: string, value: unknown, now: number) =>
  gate.groupWrite(token, key, JSON.stringify(value), now);

async function config(env: UnifiedEnv): Promise<Config | null> {
  if (!env.STATE || typeof env.STATE.get !== "function") return null;
  const c = await env.STATE.get<Config>(CONFIG_KEY, "json");
  if (!c || c.enabled !== true) return null;
  if (!/^-100\d{5,}$/.test(c.chat_id) || !Number.isSafeInteger(c.feed_topic) ||
      !Number.isSafeInteger(c.events_topic) || c.feed_topic <= 7 || c.events_topic <= 7 ||
      c.feed_topic === c.events_topic || !/^20\d\d-\d\d-\d\d$/.test(c.start_date) ||
      c.expected_bot !== "xiyunewsbot") throw new Error("invalid group configuration");
  return c;
}
function gateFor(env: UnifiedEnv, c: Config): Gate {
  return env.RECOVERY_GATE.getByName(`telegram-group-v1:${c.chat_id}:${c.feed_topic}:${c.events_topic}`);
}

export function eventPlan(snapshot: Snapshot, previous: Baseline | null): {parts: string[]; baseline: Baseline} {
  const baseline: Baseline = {}, entries: string[] = [];
  const bootstrap = previous === null;
  let selected = 0;
  for (const event of snapshot.events) {
    const old = previous?.[event.id];
    const newUpdates = event.updates.filter(u => !old?.ids.includes(u.id));
    const material = old ? Date.parse(event.latest_at) > Date.parse(old.latest_at) && newUpdates.length > 0
      : newUpdates.some(u => u.date === snapshot.date);
    const ending = !!old?.tracked && closed(event.status) && event.status !== old.delivered_status;
    const eligible = bootstrap ? event.focus : (event.focus && material) || ending;
    const include = eligible && (selected < 6 || ending);
    baseline[event.id] = {status: event.status, state: event.state, latest_at: event.latest_at,
      ids: event.updates.map(u => u.id), tracked: !!old?.tracked || include,
      delivered_state: include ? event.state : old?.delivered_state,
      delivered_status: include ? event.status : old?.delivered_status};
    if (!include) continue;
    selected++;
    const link = `https://xiyu.news/events/${event.id}/`;
    let entry = `<b>${String(selected).padStart(2,"0")} ${esc(event.title)}</b> · ${esc(event.status_label)}`;
    if (!old?.tracked && event.background) entry += `\n背景：${esc(event.background)}`;
    if (old?.tracked && old.delivered_state && old.delivered_state !== event.state) entry += `\n之前：${esc(old.delivered_state)}`;
    if (event.state) entry += `\n现在：${esc(event.state)}`;
    const updates = bootstrap ? event.updates.slice(0,1) : newUpdates.slice(0,3);
    for (const update of updates) {
      entry += `\n${esc(update.date)} · ${esc(update.kind)}：${esc(update.text)}`;
      entry += ` <a href="${link}#${update.id}">节点依据</a>`;
    }
    const sources = updates.flatMap(u => u.sources).filter((s,i,a) => a.findIndex(x => x.url === s.url) === i).slice(0,2);
    if (sources.length) entry += "\n来源：" + sources.map(s => `<a href="${esc(s.url)}">${esc(s.label)}</a>`).join(" · ");
    entry += `\n<a href="${link}">完整时间线 →</a>`;
    entries.push(entry);
  }
  const header = `<b>xiyu.news · ${bootstrap ? "当前追踪概览" : "事件进展"} · ${snapshot.date}</b>`;
  const footer = '\n\n<a href="https://xiyu.news/threads/">全部重点追踪 →</a>';
  const parts: string[] = [];
  let current = header;
  for (const entry of entries) {
    if ((header + entry + footer).length > 3550) throw new Error("event entry too long");
    if ((current + "\n\n" + entry + footer).length > 3600) {parts.push(current+footer); current=header;}
    current += "\n\n" + entry;
  }
  if (entries.length) parts.push(current+footer);
  return {parts, baseline};
}

function validSnapshot(value: Snapshot, env: UnifiedEnv, today: string): boolean {
  if (value.version !== 1 || value.date !== today || value.artifact !== env.SITE_ARTIFACT_COMMIT ||
      !Array.isArray(value.feed_parts) || !value.feed_parts.length || value.feed_parts.length > 10 ||
      value.feed_parts.some(p => typeof p !== "string" || p.length > 3600) ||
      !Array.isArray(value.events) || value.events.length > 2000) return false;
  // The artifact is built by trusted code, but source text and URLs remain untrusted.
  return value.events.every(e => /^evt_[a-z0-9]+$/.test(e.id) &&
    [e.title,e.state,e.background,e.status_label].every(t => typeof t === "string" && t.length <= 420) &&
    Number.isFinite(Date.parse(e.latest_at)) && Array.isArray(e.updates) && e.updates.length <= 3 &&
    e.updates.every(u => /^upd_[a-z0-9]+$/.test(u.id) && /^20\d\d-\d\d-\d\d$/.test(u.date) &&
      typeof u.text === "string" && u.text.length <= 420 && typeof u.kind === "string" &&
      Array.isArray(u.sources) && u.sources.every(s => /^https?:\/\//.test(s.url) &&
        s.url.length <= 300 && typeof s.label === "string" && s.label.length <= 40)));
}

async function botCall(env: UnifiedEnv, method: string, payload: unknown): Promise<Response> {
  return fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload),
    redirect: "error", signal: AbortSignal.timeout(10_000),
  });
}

async function deliver(gate: Gate, owner: string, env: UnifiedEnv, c: Config,
  kind: "feed" | "events", job: Job, now: number): Promise<void> {
  const key = `tg:${job.date}:${kind}`;
  if (job.status !== "pending") return;
  const index = job.receipts.findIndex(r => r.status !== "sent");
  if (index < 0) {job.status="sent"; await write(gate,owner,key,job,now); return;}
  const receipt = job.receipts[index];
  if (!receipt) throw new Error("invalid group receipt");
  if (receipt.status === "sending" || receipt.status === "unknown") {
    receipt.status="unknown"; job.status="unknown";
    await write(gate,owner,key,job,now); return;
  }
  if (receipt.status === "failed" || receipt.attempts >= 3) {
    job.status="failed"; await write(gate,owner,key,job,now); return;
  }
  if ((receipt.next_at ?? 0) > now) return;
  receipt.status="sending"; receipt.attempts++;
  await write(gate,owner,key,job,now); // Claim survives a crash/timeout BEFORE external I/O.
  try {
    const response = await botCall(env,"sendMessage", {chat_id:c.chat_id,
      message_thread_id:kind==="feed" ? c.feed_topic : c.events_topic,
      text:job.parts[index], parse_mode:"HTML", link_preview_options:{is_disabled:true},
      disable_notification:index>0});
    const result = await response.json() as {ok?: boolean; error_code?: number;
      parameters?: {retry_after?: number}; result?: {message_id?: number; message_thread_id?: number; chat?: {id?: number}}};
    if (result.ok === true && response.ok && Number.isSafeInteger(result.result?.message_id) &&
        Number(result.result?.message_id)>0 && String(result.result?.chat?.id) === c.chat_id &&
        result.result?.message_thread_id === (kind==="feed" ? c.feed_topic : c.events_topic)) {
      receipt.status="sent"; receipt.message_id=result.result!.message_id; receipt.sent_at=now;
      if (job.receipts.every(r => r.status==="sent")) job.status="sent";
    } else if (result.ok === false && Number.isInteger(result.error_code)) {
      receipt.code=result.error_code;
      const retry = result.error_code===429 || (result.error_code!>=500);
      receipt.status=retry && receipt.attempts<3 ? "pending" : "failed";
      receipt.next_at=now+Math.max(300, Math.min(86400,result.parameters?.retry_after ?? 300))*1000;
      if (receipt.status==="failed") job.status="failed";
    } else {receipt.status="unknown"; job.status="unknown";}
  } catch {receipt.status="unknown"; job.status="unknown";}
  await write(gate,owner,key,job,Date.now());
}

export async function runGroupNews(env: UnifiedEnv, now=Date.now(),
  pause: (ms: number) => Promise<void> = ms => new Promise(resolve=>setTimeout(resolve,ms))): Promise<void> {
  if (env.ENABLE_DISPATCHER!=="true") return;
  const c=await config(env);
  if (!c || !env.TELEGRAM_BOT_TOKEN || day(now)<c.start_date) return;
  const gate=gateFor(env,c), owner=await gate.claim(now);
  if (!owner) return;
  try {
    const today=day(now);
    const identityKey=env.SITE_SOURCE_COMMIT ?? env.SITE_ARTIFACT_COMMIT;
    if (!identityKey || !/^[a-f0-9]{40}$/.test(identityKey)) throw new Error("missing group build identity");
    if (await gate.groupRead("tg:bot-verified")!==JSON.stringify(identityKey)) {
      const me=await (await botCall(env,"getMe",{})).json() as {ok?:boolean;result?:{username?:string}};
      if (!me.ok || me.result?.username!==c.expected_bot) throw new Error("group bot mismatch");
      await write(gate,owner,"tg:bot-verified",identityKey,now);
    }
    let feed=await read<Job>(gate,`tg:${today}:feed`), events=await read<Job>(gate,`tg:${today}:events`);
    if (feed?.status!=="pending" && events?.status!=="pending" && feed && events) {
      if ((events.status==="sent" || events.status==="skipped") && events.baseline) {
        await write(gate,owner,"tg:baseline",events.baseline,now);
      }
      return;
    }
    if (!feed || !events) {
      const response=await env.ASSETS.fetch(new Request("https://xiyu.news/api/_telegram-group.json"));
      if (!response.ok) return;
      const snapshot=await response.json() as Snapshot;
      if (!validSnapshot(snapshot,env,today)) return; // Old/future editions and mixed builds never send.
      const latest=await env.ASSETS.fetch(new Request("https://xiyu.news/api/latest.json"));
      if (!latest.ok || (await latest.json() as {date?:string}).date!==today) return;
      const home=await env.ASSETS.fetch(new Request("https://xiyu.news/",{signal:AbortSignal.timeout(5000)}));
      if (!home.ok || !(await home.text()).includes(`data-latest-edition-date="${today}"`)) return;
      if (!feed) {
        feed={date:today,parts:snapshot.feed_parts,receipts:snapshot.feed_parts.map(()=>({status:"pending",attempts:0})),status:"pending"};
        await write(gate,owner,`tg:${today}:feed`,feed,now);
      }
      if (!events) {
        const previous=await read<Baseline>(gate,"tg:baseline");
        // Remember observed IDs before any send, separately from confirmed delivery.
        // An unknown/partial first day must not replay the same nodes the next day.
        const observed: Baseline={};
        for (const event of snapshot.events) {
          const old=previous?.[event.id];
          observed[event.id]={status:event.status,state:event.state,latest_at:event.latest_at,
            ids:event.updates.map(u=>u.id),tracked:!!old?.tracked,
            delivered_state:old?.delivered_state,delivered_status:old?.delivered_status};
        }
        try {
          const plan=eventPlan(snapshot,previous);
          events={date:today,parts:plan.parts,receipts:plan.parts.map(()=>({status:"pending",attempts:0})),
            status:plan.parts.length ? "pending" : "skipped",baseline:plan.baseline};
        } catch {
          // Fail closed for this topic only; never truncate facts or block the daily feed.
          events={date:today,parts:[],receipts:[],status:"failed",reason:"rendering_failed"};
        }
        await write(gate,owner,"tg:baseline",observed,now);
        await write(gate,owner,`tg:${today}:events`,events,now);
      }
    }
    if (feed.status==="pending" || events.status==="pending") {
      const result=await (await botCall(env,"getMe",{})).json() as {ok?:boolean;result?:{username?:string}};
      if (!result.ok || result.result?.username!==c.expected_bot) throw new Error("group bot mismatch");
      // Bounded, spaced parts; 429 waits for a later EXISTING Cron, not a new scheduler.
      let attempted=false;
      for (const [kind,job] of [["feed",feed],["events",events]] as const) {
        for (let part=0;part<2 && job.status==="pending";part++) {
          if (attempted) await pause(3200);
          await gate.groupRenew(owner,Date.now());
          const sent=job.receipts.filter(r=>r.status==="sent").length;
          await deliver(gate,owner,env,c,kind,job,Date.now()); attempted=true;
          if (job.receipts.filter(r=>r.status==="sent").length===sent) break;
        }
      }
    }
    if ((events.status==="sent" || events.status==="skipped") && events.baseline) {
      await write(gate,owner,"tg:baseline",events.baseline,Date.now());
    }
    console.log(JSON.stringify({event:"group_digest_tick",date:today,feed:feed.status,events:events.status}));
  } catch {console.warn(JSON.stringify({event:"group_digest_tick_failed"}));}
  finally {
    try {
      const status=JSON.stringify(await groupStatus(env,day(now)));
      if (await gate.groupRead("tg:last-status")!==status) {
        await env.STATE.put(STATUS_KEY,status,{expirationTtl:86400*90});
        await write(gate,owner,"tg:last-status",JSON.parse(status),Date.now());
      }
    }
    catch { /* Observer failure cannot re-send a confirmed/unknown part. */ }
    await gate.release(owner);
  }
}

export async function groupStatus(env: UnifiedEnv, date: string): Promise<unknown> {
  const c=await config(env);
  if (!c) return {enabled:false};
  const gate=gateFor(env,c), jobs: Record<string,unknown>={};
  for (const kind of ["feed","events"]) {
    const job=await read<Job>(gate,`tg:${date}:${kind}`);
    jobs[kind]=job ? {status:job.status,parts:job.receipts.length,receipts:job.receipts,
      ...(job.reason ? {reason:job.reason} : {})} : {status:"not_prepared"};
  }
  const identityKey=env.SITE_SOURCE_COMMIT ?? env.SITE_ARTIFACT_COMMIT;
  return {enabled:true,date,bot_verified:await gate.groupRead("tg:bot-verified")===JSON.stringify(identityKey),...jobs};
}
