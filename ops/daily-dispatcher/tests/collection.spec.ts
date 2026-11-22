import { env } from "cloudflare:test";
import { afterEach, expect, it, vi } from "vitest";
import { dispatchCollection, FEED_WORKFLOW } from "../src/collection";
import { runCombinedSchedule, COLLECTION_CRON } from "../src/schedule";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

const run = (status: string, startedAt: string, branch = "main") => ({
  status, conclusion: status === "completed" ? "success" : null,
  head_branch: branch, run_started_at: startedAt, html_url: null,
});

function github(runs: unknown[]) {
  const calls: Request[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init); calls.push(request);
    return request.method === "POST" ? new Response(null, { status: 204 }) : Response.json({ workflow_runs: runs });
  }));
  return calls;
}

it("dispatches a collection when the newest one is over thirty minutes old", async () => {
  const calls = github([run("completed", "2026-09-29T14:00:00Z")]);
  expect(await dispatchCollection(env, Date.parse("2026-09-29T18:10:00Z"))).toBe("dispatched");
  expect(calls).toHaveLength(2);
  expect(calls[0]?.url).toContain(`${FEED_WORKFLOW}/runs`);
  expect(calls[1]?.url).toContain(`${FEED_WORKFLOW}/dispatches`);
  expect(await calls[1]?.json()).toEqual({ ref: "main" });
});

it("leaves a recent collection alone, including one on another branch only", async () => {
  github([run("completed", "2026-09-29T18:08:00Z"), run("completed", "2026-09-29T18:00:00Z", "feature")]);
  expect(await dispatchCollection(env, Date.parse("2026-09-29T18:10:00Z"))).toBe("fresh");
});

it.each(["queued", "in_progress", "waiting", "pending", "requested"])("does not stack on an %s run", async status => {
  const calls = github([run(status, "2026-09-29T10:00:00Z")]);
  expect(await dispatchCollection(env, Date.parse("2026-09-29T18:10:00Z"))).toBe("active");
  expect(calls).toHaveLength(1);
});

it("dispatches when no collection has ever run", async () => {
  github([]);
  expect(await dispatchCollection(env, Date.parse("2026-09-28T18:10:00Z"))).toBe("dispatched");
});

it.each([
  ["2026-09-29T18:30:00Z", "dispatched"],
  ["2026-09-29T23:30:00Z", "dispatched"],
  ["2026-09-29T23:00:00Z", "dispatched"],
])("collects at half-hour boundaries, including cutoff %s", async (time, expected) => {
  const calls = github([]);
  expect(await dispatchCollection(env, Date.parse(time))).toBe(expected);
  expect(calls.filter(call => call.method === "POST")).toHaveLength(1);
});

it("fails closed on GitHub API failure", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 403 })));
  await expect(dispatchCollection(env, Date.parse("2026-09-29T18:10:00Z"))).rejects.toThrow("403");
});

it("retries recent failures with a durable budget but respects cancellation", async () => {
  const now = Date.parse("2026-10-02T18:10:00Z");
  const failed = {...run("completed", "2026-10-02T17:00:00Z"), conclusion: "failure"};
  const calls = github([failed]);
  expect(await dispatchCollection(env, now)).toBe("retry_dispatched");
  expect(await dispatchCollection(env, now + 10 * 60_000)).toBe("cooldown");
  expect(await dispatchCollection(env, now + 30 * 60_000)).toBe("retry_dispatched");
  expect(await dispatchCollection(env, now + 60 * 60_000)).toBe("retry_limit");
  expect(calls.filter(call => call.method === "POST")).toHaveLength(2);
  github([{...failed, run_started_at: new Date(now - 60_000).toISOString(), conclusion: "cancelled"}]);
  expect(await dispatchCollection(env, now)).toBe("fresh");
});

it("does not count a failed fresh run as successful collection", async () => {
  github([{...run("completed", "2026-10-03T18:00:00Z"), conclusion: "timed_out"}]);
  expect(await dispatchCollection(env, Date.parse("2026-10-03T18:10:00Z"))).toBe("failed_waiting");
});

it("the overnight tick checks collection without touching Square or publication", async () => {
  const now = Date.parse("2026-09-30T18:30:00Z"); // 02:30 Shanghai
  vi.spyOn(Date, "now").mockReturnValue(now);
  const calls = github([run("completed", "2026-09-29T13:00:00Z")]);
  await runCombinedSchedule(COLLECTION_CRON, now, env);
  expect(calls.map(call => new URL(call.url).pathname.split("/").slice(-2).join("/")))
    .toEqual([`${FEED_WORKFLOW}/runs`, `${FEED_WORKFLOW}/dispatches`]);
});

it('half-hour collection preserves active guards at the cutoff hour',async()=>{
 const rolling=env;
 github([run('completed','2026-11-08T22:29:00Z')]);
 expect(await dispatchCollection(rolling,Date.parse('2026-11-08T23:05:00Z'))).toBe('dispatched');
 github([run('in_progress','2026-11-08T23:05:00Z')]);
 expect(await dispatchCollection(rolling,Date.parse('2026-11-08T23:10:00Z'))).toBe('active');
});

it('does not count a successful operations test as source collection',async()=>{
  const moment=Date.parse('2026-11-09T12:10:00Z');
  const calls:Request[]=[];
  vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
    const request=new Request(input,init);calls.push(request);
    if(request.method==='POST')return new Response(null,{status:204});
    return Response.json({workflow_runs:[
      {status:'completed',conclusion:'success',head_branch:'main',display_title:'Operations alert test',run_started_at:new Date(moment-60_000).toISOString(),html_url:null},
      {status:'completed',conclusion:'success',head_branch:'main',display_title:'Feed collection',run_started_at:new Date(moment-1_860_000).toISOString(),html_url:null},
    ]});
  }));
  expect(await dispatchCollection(env,moment)).toBe('dispatched');
  expect(calls.filter(r=>r.method==='POST')).toHaveLength(1);
});
