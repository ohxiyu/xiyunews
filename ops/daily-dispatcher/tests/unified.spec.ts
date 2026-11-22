import {env} from "cloudflare:test";
import {afterEach, describe, expect, it, vi} from "vitest";
import unified, {type UnifiedEnv} from "../src/unified";
import dispatcher from "../src/index";

function fixture(extra: Partial<UnifiedEnv> = {}): UnifiedEnv {
  return {...env, ASSETS: {fetch: vi.fn(async () => new Response("site asset"))},
    STATE: {} as KVNamespace, ...extra} as UnifiedEnv;
}
const context = {waitUntil: vi.fn()} as unknown as ExecutionContext;
it("preserves cache validators for the static daily homepage", async()=>{
  const e=fixture();
  await unified.fetch(new Request("https://xiyu.news/", {headers:{"If-None-Match":"old-shell","If-Modified-Since":"Sun, 08 Nov 2026 12:00:00 GMT"}}),e,context);
  const request=vi.mocked(e.ASSETS.fetch).mock.calls[0]![0] as Request;
  expect(request.headers.has("If-None-Match")).toBe(true);
  expect(request.headers.has("If-Modified-Since")).toBe(true);
});
const fiveMinutes = {cron: "*/5 * * * *", scheduledTime: Date.now()} as ScheduledController;
afterEach(() => {vi.restoreAllMocks(); vi.unstubAllGlobals();});

describe("single xiyunews project", () => {
  it.each(["/", "/health", "/publication/check", "/api/_telegram-group.json", "/s/", "/api/latest.json?x=1&x=2"])("canonicalizes www before any routing: %s", async (path) => {
    const e=fixture(),call=vi.spyOn(dispatcher,"fetch");
    const response=await unified.fetch(new Request("https://www.xiyu.news"+path),e,context);
    expect(response.status).toBe(308);
    expect(response.headers.get("Location")).toBe("https://xiyu.news"+path);
    expect(e.ASSETS.fetch).not.toHaveBeenCalled();expect(call).not.toHaveBeenCalled();
  });
  it("identifies one project and reports paused state and immutable build sources", async () => {
    const response = await unified.fetch(new Request("https://xiyu.news/health"),
      fixture({SITE_ARTIFACT_COMMIT: "a".repeat(40)}), context);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await response.json()).toMatchObject({service: "xiyunews", project: "xiyunews",
      repository: "ohxiyu/xiyunews", dispatcher_enabled: false,
      modules: ["daily-edition"], delivery: ["x"], site_artifact_commit: "a".repeat(40)});
  });
  it("reuses website routing rather than the dispatcher 404", async () => {
    const e = fixture();
    const response = await unified.fetch(new Request("https://xiyu.news/legal/"), e, context);
    expect(response.status).toBe(200);
    expect(await response.text()).toBe("site asset");
    expect(e.ASSETS.fetch).toHaveBeenCalled();
  });
  it("retires admin requests before any static asset fallback", async () => {
    const e = fixture();
    const response = await unified.fetch(new Request("https://xiyu.news/s/"), e, context);
    expect(response.status).toBe(410);
    expect(e.ASSETS.fetch).not.toHaveBeenCalled();
    expect(response.headers.get("Cache-Control")).toBe("no-store");
  });
  it("fails closed on publication mutations while paused", async () => {
    const call = vi.spyOn(dispatcher, "fetch");
    const response = await unified.fetch(new Request("https://xiyu.news/publication/check", {
      method: "POST", headers: {Authorization: "Bearer test-check-token"},
    }), fixture(), context);
    expect(response.status).toBe(503);
    expect(call).not.toHaveBeenCalled();
  });
  it("keeps active publication mutations behind the original bearer check", async () => {
    const response = await unified.fetch(new Request("https://xiyu.news/publication/check", {
      method: "POST",
    }), fixture({ENABLE_DISPATCHER: "true"}), context);
    expect(response.status).toBe(401);
  });
  it.each([
    ["missing", false, false, "2026-10-04"],
    ["published", true, false, "2026-10-05"],
    ["stale HTML", true, true, "2026-10-06"],
  ] as const)("probes the local website when public self-fetch returns 522: %s", async (_label, published, stale, day) => {
    const now = Date.parse(day + "T07:26:00+08:00");
    vi.spyOn(Date, "now").mockReturnValue(now);
    const revision = "a".repeat(64);
    const json = JSON.stringify({date: published ? day : "2026-10-03",
      content_revision_version: 1, items: [{content_revision: {zh: revision, en: revision}}]});
    const html = `<div data-latest-edition-date="${day}"></div>` +
      `<section class="daily-day" data-date="${day}"><article class="digest-item" data-content-revision="${revision}"></article></section>`;
    const calls: Request[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = new Request(input, init); calls.push(request);
      if (new URL(request.url).hostname !== "api.github.com") return new Response("self origin timeout", {status: 522});
      if (request.method === "POST") return new Response(null, {status: 204});
      if (request.url.includes("/runs?")) return Response.json({workflow_runs: []});
      if (request.url.includes("/contents/_posts/")) return new Response(published ? "markdown" : "", {status: published ? 200 : 404});
      return new Response(json);
    }));
    const assetRequests: Request[] = [];
    const e = fixture({ENABLE_DISPATCHER: "true", ASSETS: {fetch: vi.fn(async (request: Request) => {
      assetRequests.push(request);
      const path = new URL(request.url).pathname;
      if (path.endsWith(".html")) return new Response(null, {status: 307, headers: {Location: path.replace(".html", "/")}});
      return new Response(path === "/api/latest.json" ? json : stale ? html.replaceAll(revision, "b".repeat(64)) : html, {headers: {
        "Content-Type": path === "/api/latest.json" ? "application/json" : "text/html",
      }});
    })} as unknown as Fetcher});
    const response = await unified.fetch(new Request("https://xiyu.news/publication/check", {
      method: "POST", headers: {Authorization: "Bearer test-check-token"},
    }), e, context);
    expect(await response.json()).toMatchObject({status: !published ? "daily_dispatched" : stale ? "pages_waiting" : "healthy", edition_date: day});
    expect(response.status).toBe(published && !stale ? 200 : 202);
    expect(calls.every(request => new URL(request.url).hostname === "api.github.com")).toBe(true);
    expect(calls.filter(request => request.method === "POST")).toHaveLength(published ? 0 : 1);
    expect(assetRequests.length).toBeGreaterThanOrEqual(published && !stale ? 4 : 2);
    expect(assetRequests.every(request => !request.headers.has("Authorization") && new URL(request.url).searchParams.has("publication_check"))).toBe(true);
  });
  it("injects the same local probe for Cron as for the authenticated recovery endpoint", async () => {
    const daily = vi.spyOn(dispatcher, "scheduled").mockResolvedValue();
    const e = fixture({ENABLE_DISPATCHER: "true"});
    await unified.scheduled(fiveMinutes, e);
    const injected = daily.mock.calls[0]?.[1] as UnifiedEnv & {PUBLICATION_FETCH: (request: Request) => Promise<Response>};
    expect(await (await injected.PUBLICATION_FETCH(new Request("https://xiyu.news/?publication_check=1"))).text()).toBe("site asset");
    expect(e.ASSETS.fetch).toHaveBeenCalledOnce();
  });
  it("schedules the daily dispatcher only when enabled", async () => {
    const daily = vi.spyOn(dispatcher, "scheduled").mockResolvedValue();
    await unified.scheduled(fiveMinutes, fixture());
    await unified.scheduled(fiveMinutes, fixture({ENABLE_DISPATCHER: "TRUE"}));
    expect(daily).not.toHaveBeenCalled();
    await unified.scheduled(fiveMinutes, fixture({ENABLE_DISPATCHER: "true"}));
    expect(daily).toHaveBeenCalledOnce();
  });
});
