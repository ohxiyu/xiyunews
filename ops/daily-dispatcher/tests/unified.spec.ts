import {env} from "cloudflare:test";
import {afterEach, describe, expect, it, vi} from "vitest";
import unified, {type UnifiedEnv} from "../src/unified";
import dispatcher from "../src/index";
// @ts-expect-error Independently validated JavaScript watchdog.
import watchdog from "../../../realtime/scripts/deploy/watchdog/worker.js";

function fixture(extra: Partial<UnifiedEnv> = {}): UnifiedEnv {
  return {...env, ASSETS: {fetch: vi.fn(async () => new Response("site asset"))},
    STATE: {} as KVNamespace, ...extra} as UnifiedEnv;
}
const context = {waitUntil: vi.fn()} as unknown as ExecutionContext;
const fiveMinutes = {cron: "*/5 * * * *", scheduledTime: Date.now()} as ScheduledController;
afterEach(() => {vi.restoreAllMocks(); vi.unstubAllGlobals();});

describe("single xiyunews project", () => {
  it("identifies one project and reports paused state and immutable build sources", async () => {
    const response = await unified.fetch(new Request("https://xiyu.news/health"),
      fixture({SITE_ARTIFACT_COMMIT: "a".repeat(40)}), context);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await response.json()).toMatchObject({service: "xiyunews", project: "xiyunews",
      repository: "ohxiyu/xiyunews", dispatcher_enabled: false,
      realtime_watchdog_enabled: false, site_artifact_commit: "a".repeat(40)});
  });
  it("reuses website routing rather than the dispatcher 404", async () => {
    const e = fixture();
    const response = await unified.fetch(new Request("https://xiyu.news/about/"), e, context);
    expect(response.status).toBe(200);
    expect(await response.text()).toBe("site asset");
    expect(e.ASSETS.fetch).toHaveBeenCalled();
  });
  it("authenticates admin requests before any static asset fallback", async () => {
    const e = fixture();
    const response = await unified.fetch(new Request("https://xiyu.news/s/"), e, context);
    expect(response.status).toBe(503);
    expect(e.ASSETS.fetch).not.toHaveBeenCalled();
    expect(response.headers.get("Cache-Control")).toBe("private, no-store");
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
  it("does not schedule anything until explicitly enabled", async () => {
    const daily = vi.spyOn(dispatcher, "scheduled").mockResolvedValue();
    const realtime = vi.spyOn(watchdog, "scheduled").mockResolvedValue();
    await unified.scheduled(fiveMinutes, fixture());
    await unified.scheduled(fiveMinutes, fixture({ENABLE_DISPATCHER: "TRUE"}));
    expect(daily).not.toHaveBeenCalled();
    expect(realtime).not.toHaveBeenCalled();
  });
  it("runs both independent components even if one fails without leaking its error", async () => {
    const daily = vi.spyOn(dispatcher, "scheduled").mockRejectedValue(new Error("secret-url"));
    const realtime = vi.spyOn(watchdog, "scheduled").mockResolvedValue();
    await expect(unified.scheduled(fiveMinutes,
      fixture({ENABLE_DISPATCHER: "true", ENABLE_REALTIME_WATCHDOG: "true"})))
      .rejects.toThrow("xiyunews scheduled component failed; inspect component logs");
    expect(daily).toHaveBeenCalledOnce();
    expect(realtime).toHaveBeenCalledOnce();
  });
  it("runs the realtime watchdog only on its original five-minute cron", async () => {
    const realtime = vi.spyOn(watchdog, "scheduled").mockResolvedValue();
    await unified.scheduled({...fiveMinutes, cron: "26 23 * * *"},
      fixture({ENABLE_REALTIME_WATCHDOG: "true"}));
    expect(realtime).not.toHaveBeenCalled();
    await unified.scheduled(fiveMinutes, fixture({ENABLE_REALTIME_WATCHDOG: "true"}));
    expect(realtime).toHaveBeenCalledOnce();
  });
});
