import { env } from "cloudflare:test";
import { afterEach, expect, it, vi } from "vitest";
import { dispatchSquare, publicationCron, runCombinedSchedule, SQUARE_CRON } from "../src/square";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const now = Date.parse("2026-09-12T03:35:00Z");

it("dispatches a missing daily plan queue-only without posting to Binance", async () => {
  const calls: Request[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init); calls.push(request);
    if (request.method === "POST") return new Response(null, { status: 204 });
    return Response.json(request.url.includes("/contents/") ? {version: 1, editions: {}, plans: {}} : { workflow_runs: [] });
  }));
  expect(await dispatchSquare(env, now)).toBe("dispatched");
  expect(calls).toHaveLength(3);
  expect(calls[0]?.url).toContain("square-distribution.yml/runs");
  expect(calls[1]?.url).toContain("queue.json?ref=square-queue");
  expect(await calls[2]?.json()).toEqual({ ref: "main", inputs: { queue_only: true } });
});

it.each(["queued", "in_progress", "waiting", "pending", "requested"])("does not replace an %s run", async status => {
  const fetcher = vi.fn(async () => Response.json({ workflow_runs: [{ status, conclusion: null,
    head_branch: "main", run_started_at: "2026-09-12T03:30:00Z", html_url: null }] }));
  vi.stubGlobal("fetch", fetcher);
  expect(await dispatchSquare(env, now)).toBe("active");
  expect(fetcher).toHaveBeenCalledOnce();
});

it.each(["00:00", "00:59", "15:31", "23:26", "23:59"])("does not dispatch outside window %s", async time => {
  const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
  expect(await dispatchSquare(env, Date.parse(`2026-09-12T${time}:00Z`))).toBe("outside_window");
  expect(fetcher).not.toHaveBeenCalled();
});

it("fails closed on GitHub API failure", async () => {
  const fetcher = vi.fn(async () => new Response(null, { status: 403 }));
  vi.stubGlobal("fetch", fetcher);
  await expect(dispatchSquare(env, now)).rejects.toThrow("403");
  expect(fetcher).toHaveBeenCalledOnce();
});

it("preserves original publication cadence while adding Square ticks", () => {
  const actual = [];
  for (let hour = 0; hour <= 15; hour++) {
    for (let minute = 0; minute < 60; minute += 5) {
      if (publicationCron(Date.UTC(2026, 8, 12, hour, minute))) actual.push((hour + 8) * 60 + minute);
    }
  }
  const expected = [];
  for (let minute = 8 * 60; minute < 12 * 60; minute += 10) expected.push(minute);
  for (let hour = 12; hour <= 23; hour++) expected.push(hour * 60);
  expect(actual).toEqual(expected);
  expect(publicationCron(Date.parse("2026-09-12T03:30:00Z"))).toBe("*/10 0-3 * * *");
  expect(publicationCron(now)).toBeNull();
  expect(publicationCron(Date.parse("2026-09-12T04:00:00Z"))).toBe("0 4-15 * * *");
  expect(publicationCron(Date.parse("2026-09-12T04:10:00Z"))).toBeNull();
});

it("combined tick runs distribution even when publication is not due", async () => {
  vi.spyOn(Date, "now").mockReturnValue(now);
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") return new Response(null, { status: 204 });
    const url = String(input);
    if (url.includes("config.github.json")) return Response.json({x_delivery: {enabled: false, mode: "drip"}});
    if (url.includes("queue.json")) return Response.json({version: 1, editions: {}, plans: {}});
    return Response.json({ workflow_runs: [] });
  });
  vi.stubGlobal("fetch", fetcher);
  await runCombinedSchedule(SQUARE_CRON, now, env);
  expect(fetcher).toHaveBeenCalledTimes(5);
});
