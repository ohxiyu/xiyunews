import {afterEach, expect, it, vi} from "vitest";
import {runtimeHealth} from "../src/runtime";
afterEach(() => vi.unstubAllGlobals());
const url = "https://api.xiyu.news/ops/runtime.json";
it("returns only a fresh whitelisted runtime status without credentials", async () => {
  const fetcher = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => Response.json({service: "xiyunews-runner", status: "busy", checked_at: 1000, starts_24h: 0, secret: "do not return"}));
  vi.stubGlobal("fetch", fetcher);
  expect(await runtimeHealth(url, 1010000)).toEqual({status: "busy", checked_at: 1000, starts_24h: 0});
  const init = fetcher.mock.calls[0]?.[1] as RequestInit;
  expect(init.redirect).toBe("manual");
  expect(new Headers(init.headers).has("Authorization")).toBe(false);
  expect(await runtimeHealth(url, 2000000)).toEqual({status: "stale_or_invalid"});
  await expect(runtimeHealth("https://evil.example/")).rejects.toThrow("Invalid runtime");
});
it("fails closed on redirects and oversized payloads", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, {status: 302, headers: {Location: "https://evil.example"}})));
  expect(await runtimeHealth(url)).toEqual({status: "unreachable"});
  vi.stubGlobal("fetch", vi.fn(async () => new Response("x".repeat(5000))));
  expect(await runtimeHealth(url)).toEqual({status: "invalid"});
});
