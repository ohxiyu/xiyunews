import { env } from "cloudflare:test";
import { afterEach, expect, it, vi } from "vitest";
import { publicationCron, runCombinedSchedule, COLLECTION_CRON } from "../src/schedule";
import * as recovery from "../src/recovery";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const now = Date.parse("2026-09-12T03:35:00Z");

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
  await runCombinedSchedule(COLLECTION_CRON, now, env);
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it.each([
  ["03:30:51", "03:31:23", true],
  ["04:00:51", "04:01:23", true],
  ["03:35:51", "03:40:23", false],
])("preserves scheduled publication cadence when %s arrives at %s", async (scheduled, arrival, expected) => {
  const time = Date.parse(`2026-10-04T${scheduled}Z`);
  vi.spyOn(Date, "now").mockReturnValue(Date.parse(`2026-10-04T${arrival}Z`));
  const check = vi.spyOn(recovery, "runSchedule").mockResolvedValue();
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") return new Response(null, {status: 204});
    const url = String(input);
    if (url.includes("config.github.json")) return Response.json({x_delivery: {enabled: false, mode: "drip"}});
    if (url.includes("queue.json")) return Response.json({version: 1, editions: {}, plans: {}});
    return Response.json({workflow_runs: []});
  }));
  await runCombinedSchedule(COLLECTION_CRON, time, env);
  expect(check).toHaveBeenCalledTimes(expected ? 1 : 0);
  if (expected) expect(check.mock.calls[0]?.[1]).toBe(Date.now());
});
