import {handleOAuthAuth,handleOAuthCallback} from "../src/oauth";
import { afterEach, describe, expect, it, vi } from "vitest";

import worker from "../src/index";
import { testing, SCHEDULE_CRONS } from "../src/lib";
import { CONFIGURED_CRONS } from "../src/schedule";
import { env } from "cloudflare:test";

const ENV = {
  ...env,
  GITHUB_REPOSITORY: "ohxiyu/xiyunews",
  GITHUB_WORKFLOW: "daily-summary.yml",
  GITHUB_REF: "main",
  EDITION_TIMEZONE: "Asia/Shanghai",
  EDITION_CUTOFF_HOUR: "7",
  PUBLIC_SITE_URL: "https://xiyu.news",
  GITHUB_DISPATCH_TOKEN: "test-token",
} satisfies Env;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("edition scheduling", () => {
  it("maps 07:26 to the preceding UTC day and the correct local edition", () => {
    const context = testing.editionContextFor(
      Date.parse("2026-09-16T23:26:00Z"), "Asia/Shanghai", 7,
    );
    expect(context.date).toBe("2026-09-17");
    expect(context.cutoffUtc.toISOString()).toBe("2026-09-16T23:00:00.000Z");
    expect(testing.stageForCron("26 23 * * *")).toBe("primary");
  });
  it("routes all extended schedule groups and accepts queued legacy events", () => {
    expect(SCHEDULE_CRONS.map(testing.stageForCron)).toEqual([
      "primary", "morning-check", "morning-check", "hourly-check",
    ]);
    expect(testing.stageForCron("40 0 * * *")).toBe("retry-1");
    expect(testing.stageForCron("55 0 * * *")).toBe("retry-2");
    expect(testing.stageForCron("10 1 * * *")).toBe("final");
    expect(() => testing.stageForCron("* * * * *")).toThrow("Unsupported");
  });
  it("targets the Shanghai edition ending at 08:00", () => {
    const context = testing.editionContextFor(
      Date.parse("2026-07-31T00:30:00Z"),
      "Asia/Shanghai",
      8,
    );

    expect(context.date).toBe("2026-07-31");
    expect(context.cutoffUtc.toISOString()).toBe(
      "2026-07-31T00:00:00.000Z",
    );
  });

  it("builds raw and rendered URLs for the Chinese edition", () => {
    expect(testing.publicationUrls(ENV, "2026-07-31")).toEqual({
      raw: [
        "https://api.github.com/repos/ohxiyu/xiyunews/contents/_posts/2026-07-31-summary-zh.md?ref=gh-pages",
      ],
      rendered: [
        "https://xiyu.news/2026/07/31/summary-zh.html",
      ],
    });
  });
});

describe("dispatcher behavior", () => {

  it("retires delayed legacy cron and coordinator callbacks without external calls", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const retired = {...ENV, XIYUNEWS_LEGACY_DISABLED: "true"};
    await worker.scheduled({cron: "*/5 * * * *", scheduledTime: Date.now()} as ScheduledController, retired);
    const response = await worker.fetch(new Request("https://dispatcher.example/publication/check", {
      method: "POST", headers: {Authorization: "Bearer test-check-token"},
    }), retired);
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({status: "coordinator_retired"});
    const health = await worker.fetch(new Request("https://dispatcher.example/health"), retired);
    expect(await health.json()).toMatchObject({legacy_scheduled_disabled: true});
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("exposes only a read-only health endpoint", async () => {
    const health = await worker.fetch(
      new Request("https://dispatcher.example/health"),
      ENV,
    );
    const notFound = await worker.fetch(
      new Request("https://dispatcher.example/run", { method: "POST" }),
      ENV,
    );

    expect(health.status).toBe(200);
    await expect(health.json()).resolves.toMatchObject({
      service: "bmtnews-daily-dispatcher",
      status: "ok",
      admin_oauth: "retired",
      schedule_crons_utc: CONFIGURED_CRONS,
      collection_workflow: "feed-collection.yml",
      collection_max_age_hours: 30 / 60,
      schedule_timezone: "Asia/Shanghai",
      edition_cutoff_hour: 7,
      first_check_local: "07:26",
      last_check_local: "23:00",
    });
    expect(notFound.status).toBe(404);
  });

  it("actively verifies Actions write permission without creating a run", async () => {
    const fetchSpy = vi.fn(
      async (_input: RequestInfo | URL, init?: RequestInit) =>
        new Response(null, { status: init?.method === "POST" ? 422 : 200 }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    const response = await worker.fetch(
      new Request("https://dispatcher.example/ready"),
      ENV,
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    await expect(response.json()).resolves.toMatchObject({
      status: "ready",
      repository: "ohxiyu/xiyunews",
      workflow: "daily-summary.yml",
      ref: "main",
      dispatch_permission: "actions:write",
      contents_permission: "contents:read",
    });
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    const [input, init] = fetchSpy.mock.calls[0] ?? [];
    expect(String(input)).toContain("/daily-summary.yml/dispatches");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({
      ref: "refs/heads/__bmtnews_permission_probe__/invalid..ref",
    });
  });

  it("rejects a read-only token without leaking GitHub API details", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 403 })));
    const response = await worker.fetch(
      new Request("https://dispatcher.example/ready"),
      ENV,
    );
    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      status: "not_ready",
      resolution: "Verify GITHUB_DISPATCH_TOKEN and redeploy the Worker.",
    });
  });
});

describe("retained OAuth helper (not exposed by the daily Worker)", () => {
  const OAUTH_ENV = {
    ...ENV,
    GITHUB_OAUTH_CLIENT_ID: "client-id",
    GITHUB_OAUTH_CLIENT_SECRET: "client-secret",
  } as Env;

  it("returns 503 while OAuth secrets are unset", async () => {
    const auth = await handleOAuthAuth(
      new Request("https://dispatcher.example/oauth/auth"),
      ENV,
    );
    const callback = await handleOAuthCallback(
      new Request("https://dispatcher.example/oauth/callback?code=x&state=y"),
      ENV,
    );
    expect(auth.status).toBe(503);
    expect(callback.status).toBe(503);
  });

  it("redirects to GitHub with a narrow scope and a state cookie", async () => {
    const response = await handleOAuthAuth(
      new Request("https://dispatcher.example/oauth/auth"),
      OAUTH_ENV,
    );

    expect(response.status).toBe(302);
    const location = new URL(response.headers.get("Location") ?? "");
    expect(location.origin).toBe("https://github.com");
    expect(location.pathname).toBe("/login/oauth/authorize");
    expect(location.searchParams.get("client_id")).toBe("client-id");
    expect(location.searchParams.get("scope")).toBe("public_repo");
    const state = location.searchParams.get("state");
    expect(state).toBeTruthy();
    expect(response.headers.get("Set-Cookie")).toContain(
      `bmtnews_oauth_state=${state}`,
    );
    expect(response.headers.get("Set-Cookie")).toContain("HttpOnly");
  });

  it("rejects a callback whose state does not match the cookie", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const response = await handleOAuthCallback(
      new Request(
        "https://dispatcher.example/oauth/callback?code=abc&state=forged",
        { headers: { Cookie: "bmtnews_oauth_state=expected" } },
      ),
      OAUTH_ENV,
    );

    const body = await response.text();
    expect(body).toContain("authorization:github:error");
    expect(body).not.toContain("authorization:github:success");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("exchanges the code and hands the token to the admin origin only", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ access_token: "gho_test_token", token_type: "bearer" }),
      ),
    );

    const response = await handleOAuthCallback(
      new Request(
        "https://dispatcher.example/oauth/callback?code=abc&state=expected",
        { headers: { Cookie: "bmtnews_oauth_state=expected" } },
      ),
      OAUTH_ENV,
    );

    const body = await response.text();
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(body).toContain("authorization:github:success");
    expect(body).toContain("gho_test_token");
    expect(body).toContain('"https://xiyu.news"');
    // The state cookie is cleared after one use.
    expect(response.headers.get("Set-Cookie")).toContain("Max-Age=0");
  });
});

it("does not expose admin OAuth routes from the daily dispatcher",async()=>{for(const path of ["/oauth/auth","/oauth/callback"]){const r=await worker.fetch(new Request("https://dispatcher.example"+path),ENV);expect(r.status).toBe(404);}});
