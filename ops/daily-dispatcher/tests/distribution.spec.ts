import { env } from "cloudflare:test";
import { afterEach, expect, it, vi } from "vitest";
import { dispatchDistribution, readPrivateJson, squareHasWork, xHasWork } from "../src/distribution";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const now = Date.parse("2026-10-01T10:50:00Z"), day = "2026-10-01";
const past = "2026-10-01T10:40:00Z", future = "2026-10-01T11:40:00Z";
function square(due: string | null = future, rows: Record<string, unknown> = {}) {
  return {version: 1, editions: {[day]: rows}, plans: {[day]: {revision: "same", jobs: [{id:"a",due_at:due}]}}};
}
const feed = {date:day, timezone:"Asia/Shanghai", updated_at:"2026-10-01T00:26:00Z"};
function job(status = "planned", due: string | null = future) {
  return {language:"zh", slot:1, status, due_at:due, deadline:future, attempted_at:null};
}
function xQueue(items = [job()], updated = feed.updated_at) {
  return {version:2, editions:{[day]:{status:"active",state_updated_at:updated,jobs:items}}};
}

it("does not launch Square for future, unscheduled, recent or already attempted stories", () => {
  expect(squareHasWork(square(),now,day)).toBe(false);
  expect(squareHasWork(square(null),now,day)).toBe(false);
  for (const status of ["sent","pending","unknown","rejected","blocked"]) {
    expect(squareHasWork(square(past,{a:{status}}),now,day)).toBe(false);
  }
  expect(squareHasWork(square(past,{b:{status:"sent",attempted_at:"2026-10-01T10:48:00Z"}}),now,day)).toBe(false);
});
it("runs Square only for bootstrap or unattempted due work", () => {
  expect(squareHasWork({version:1,editions:{},plans:{}},now,day)).toBe(true);
  expect(squareHasWork(square(past),now,day)).toBe(true);
});
it("rejects corrupt Square versions, outcomes, identities and times", () => {
  expect(() => squareHasWork({version:2},now,day)).toThrow();
  expect(() => squareHasWork(square(past,{a:{status:"planned"}}),now,day)).toThrow();
  expect(() => squareHasWork(square("not-a-time"),now,day)).toThrow();
  const state = square(); state.plans[day]!.jobs.push({id:"a",due_at:past});
  expect(() => squareHasWork(state,now,day)).toThrow();
});
it("keeps X idle for future jobs and completed, failed or unknown receipts", () => {
  expect(xHasWork(xQueue(),feed,now,day,"Asia/Shanghai")).toBe(false);
  for (const status of ["sent","failed","unknown","expired","void","skipped"]) {
    expect(xHasWork(xQueue([job(status,past)]),feed,now,day,"Asia/Shanghai")).toBe(false);
  }
});
it("detects X new/revised editions with equivalent timezone timestamp spelling", () => {
  expect(xHasWork({version:2,editions:{}},feed,now,day,"Asia/Shanghai")).toBe(true);
  expect(xHasWork(xQueue([],past),feed,now,day,"Asia/Shanghai")).toBe(true);
  expect(xHasWork(xQueue([],"2026-10-01T08:26:00+08:00"),feed,now,day,"Asia/Shanghai")).toBe(false);
});
it("dispatches X due, pending recovery, expiration and next-slot anchoring", () => {
  expect(xHasWork(xQueue([job("planned",past)]),feed,now,day,"Asia/Shanghai")).toBe(true);
  expect(xHasWork(xQueue([job("pending")]),feed,now,day,"Asia/Shanghai")).toBe(true);
  expect(xHasWork(xQueue([{...job(),deadline:past}]),feed,now,day,"Asia/Shanghai")).toBe(true);
  expect(xHasWork(xQueue([job("sent",past),{...job("planned",null),slot:2}]),feed,now,day,"Asia/Shanghai")).toBe(true);
});
it("does not send a halted X language or use yesterday's stories as today's", () => {
  expect(xHasWork(xQueue([job("failed"),{...job("planned",past),slot:2}]),feed,now,day,"Asia/Shanghai")).toBe(false);
  expect(xHasWork({version:2,editions:{"2026-09-30":xQueue().editions[day]}},
    {...feed,date:"2026-09-30"},now,day,"Asia/Shanghai")).toBe(false);
});
it("rejects corrupt X status, duplicate slots, naive times and wrong feed timezone", () => {
  expect(() => xHasWork(xQueue([job("surprise")]),feed,now,day,"Asia/Shanghai")).toThrow();
  expect(() => xHasWork(xQueue([job(),job()]),feed,now,day,"Asia/Shanghai")).toThrow();
  expect(() => xHasWork(xQueue([job("planned","2026-10-01T10:00:00")]),feed,now,day,"Asia/Shanghai")).toThrow();
  expect(() => xHasWork(xQueue(),{...feed,timezone:"UTC"},now,day,"Asia/Shanghai")).toThrow();
});
it.each([403,404,429,500,302])("fails closed on private content HTTP %s without dispatch or redirect", async status => {
  const fetcher=vi.fn(async (_input: RequestInfo|URL, init?:RequestInit) =>
    String(_input).includes("/runs?") ? Response.json({workflow_runs:[]}) : new Response(null,{status}));
  vi.stubGlobal("fetch",fetcher);
  await expect(dispatchDistribution(env,"square",now)).rejects.toThrow(String(status));
  expect(fetcher.mock.calls.every(([,init])=>init?.method!=="POST")).toBe(true);
  expect(fetcher.mock.calls[1]?.[1]?.redirect).toBe("manual");
});
it("bounds private JSON even when Content-Length is missing or dishonest", async () => {
  vi.stubGlobal("fetch",vi.fn(async()=>new Response("x".repeat(1_048_577))));
  await expect(readPrivateJson(env,"queue.json","square-queue")).rejects.toThrow("Oversized");
  vi.stubGlobal("fetch",vi.fn(async()=>new Response("{}",{headers:{"Content-Length":"1048577"}})));
  await expect(readPrivateJson(env,"queue.json","square-queue")).rejects.toThrow("Oversized");
});
it("idle Square checks do not create any Actions runner", async () => {
  const fetcher=vi.fn(async (input: RequestInfo|URL)=> Response.json(String(input).includes("/runs?") ? {workflow_runs:[]} : square()));
  vi.stubGlobal("fetch",fetcher);
  expect(await dispatchDistribution(env,"square",now)).toBe("idle");
  expect(fetcher).toHaveBeenCalledTimes(2);
});
it("independent X checks use authenticated fixed content paths and dispatch only main", async () => {
  const calls:Request[]=[];
  vi.stubGlobal("fetch",vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
    const request=new Request(input,init);calls.push(request);
    if(request.method==="POST") return new Response(null,{status:204});
    if(request.url.includes("/runs?")) return Response.json({workflow_runs:[]});
    if(request.url.includes("config.github.json")) return Response.json({x_delivery:{enabled:true,mode:"drip"}});
    if(request.url.includes("bmtnews_state.json")) return Response.json(feed);
    return Response.json(xQueue([job("planned",past)]));
  }));
  expect(await dispatchDistribution(env,"x",now)).toBe("dispatched");
  expect(calls).toHaveLength(5);
  expect(calls.every(request=>new URL(request.url).hostname==="api.github.com")).toBe(true);
  expect(await calls.at(-1)!.json()).toEqual({ref:"main",inputs:{}});
});
it("keeps X off when delivery is disabled and backs off failed runs", async () => {
  vi.stubGlobal("fetch",vi.fn(async(input:RequestInfo|URL)=>Response.json(String(input).includes("/runs?")?
    {workflow_runs:[]}:{x_delivery:{enabled:false,mode:"drip"}})));
  expect(await dispatchDistribution(env,"x",now)).toBe("disabled");
  vi.stubGlobal("fetch",vi.fn(async()=>Response.json({workflow_runs:[{head_branch:"main",status:"completed",
    conclusion:"failure",run_started_at:"2026-10-01T10:40:00Z",html_url:null}]})));
  expect(await dispatchDistribution(env,"x",now)).toBe("cooldown");
});
it.each(["15:31","20:00","23:25"])("keeps X outside its reading window at UTC %s",async time=>{
  const fetcher=vi.fn();vi.stubGlobal("fetch",fetcher);
  expect(await dispatchDistribution(env,"x",Date.parse(`2026-10-01T${time}:00Z`))).toBe("outside_window");
  expect(fetcher).not.toHaveBeenCalled();
});
