import { checkReadiness } from "./lib";
import { runRecovery, responseStatus } from "./recovery";
import { CONFIGURED_CRONS, runCombinedSchedule } from "./square";
import { FEED_INTERVAL_MS, FEED_WORKFLOW } from "./collection";
import { timingSafeEqual } from "node:crypto";
export { RecoveryGate } from "./gate";
import {
  handleOAuthAuth,
  handleOAuthCallback,
  type OAuthEnv,
} from "./oauth";

interface LifecycleEnv extends Env {
  // Used only to retire the old Worker while cached Cron triggers propagate.
  XIYUNEWS_LEGACY_DISABLED?: string;
}

export default {
  async fetch(request: Request, env: LifecycleEnv): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/publication/check") {
      if (env.XIYUNEWS_LEGACY_DISABLED === "true") {
        return Response.json({status: "coordinator_retired"}, {
          status: 503, headers: {"Cache-Control": "no-store"},
        });
      }
      if (request.method !== "POST") {
        return new Response(null, { status: 405, headers: { Allow: "POST" } });
      }
      const provided = new TextEncoder().encode(request.headers.get("Authorization") ?? "");
      const expected = new TextEncoder().encode("Bearer " + env.RECOVERY_CHECK_TOKEN);
      if (!env.RECOVERY_CHECK_TOKEN || provided.length !== expected.length ||
          !timingSafeEqual(provided, expected)) {
        return Response.json({ error: "Unauthorized" }, { status: 401 });
      }
      try {
        const result = await runRecovery(env, Date.now(), "publication-watchdog");
        console.log(JSON.stringify({ event: "publication_check", ...result }));
        return Response.json(result, {
          status: responseStatus(result), headers: { "Cache-Control": "no-store" },
        });
      } catch (error) {
        const message = String(error instanceof Error ? error.message : "unknown")
          .replaceAll(env.RECOVERY_CHECK_TOKEN, "[secret]")
          .replaceAll(env.GITHUB_DISPATCH_TOKEN, "[secret]")
          .replaceAll(env.PAGES_DEPLOY_HOOK, "[secret]")
          .replace(/https?:\/\/\S+/g, "[url]").slice(0, 300);
        console.error(JSON.stringify({ event: "publication_check_failed", message }));
        return Response.json({ status: "check_failed" }, {
          status: 503, headers: { "Cache-Control": "no-store" },
        });
      }
    }
    if (!(env as LifecycleEnv & {CORE_ONLY?: boolean}).CORE_ONLY && request.method === "GET" && url.pathname === "/oauth/auth") {
      return handleOAuthAuth(request, env as OAuthEnv);
    }
    if (!(env as LifecycleEnv & {CORE_ONLY?: boolean}).CORE_ONLY && request.method === "GET" && url.pathname === "/oauth/callback") {
      return handleOAuthCallback(request, env as OAuthEnv);
    }
    if (request.method === "GET" && url.pathname === "/ready") {
      try {
        return Response.json(await checkReadiness(env), {
          headers: { "Cache-Control": "no-store" },
        });
      } catch (error) {
        console.error(JSON.stringify({
          event: "dispatcher_readiness_failed",
          message: String(error instanceof Error ? error.message : error),
        }));
        return Response.json(
          {
            status: "not_ready",
            resolution: "Verify GITHUB_DISPATCH_TOKEN and redeploy the Worker.",
          },
          { status: 503, headers: { "Cache-Control": "no-store" } },
        );
      }
    }
    if (request.method !== "GET" || url.pathname !== "/health") {
      return Response.json({ error: "Not found" }, { status: 404 });
    }
    const oauthEnv = env as OAuthEnv;
    const core = Boolean((env as Env & {CORE_ONLY?: boolean}).CORE_ONLY);
    return Response.json({
      service: "bmtnews-daily-dispatcher",
      repository: env.GITHUB_REPOSITORY,
      public_site_url: env.PUBLIC_SITE_URL,
      version_id: env.CF_VERSION_METADATA?.id ?? null,
      publication_revision: "story-content-v1",
      status: "ok",
      legacy_scheduled_disabled: env.XIYUNEWS_LEGACY_DISABLED === "true",
      primary_cron_utc: "26 23 * * *",
      schedule_crons_utc: CONFIGURED_CRONS,
      square_check_window_local: core ? null : "09:00–23:30",
      distribution_gate: core ? "retired" : "private-queue-due-v1",
      x_check_window_local: core ? null : "07:26–23:30",
      collection_workflow: FEED_WORKFLOW,
      collection_max_age_hours: (env as Env & {ROLLING_FEED?: boolean}).ROLLING_FEED ? 5 / 60 : FEED_INTERVAL_MS / 3_600_000,
      schedule_timezone: env.EDITION_TIMEZONE,
      edition_cutoff_hour: Number(env.EDITION_CUTOFF_HOUR),
      first_check_local: "07:26",
      last_check_local: "23:00",
      admin_oauth: Boolean(
        !core && oauthEnv.GITHUB_OAUTH_CLIENT_ID && oauthEnv.GITHUB_OAUTH_CLIENT_SECRET,
      )
        ? "configured"
        : "not_configured",
    });
  },

  async scheduled(
    controller: ScheduledController,
    env: LifecycleEnv,
  ): Promise<void> {
    if (env.XIYUNEWS_LEGACY_DISABLED === "true") {
      console.log("xiyunews legacy dispatcher disabled; cron ignored");
      return;
    }
    await runCombinedSchedule(controller.cron, controller.scheduledTime, env);
  },
} satisfies ExportedHandler<Env>;
