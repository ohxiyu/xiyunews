import {liveRoute, liveHome} from "./live";
import dispatcher from "./index";
import {checkPrivateAlerts} from "./alerts";
import type { RecoveryEnv } from "./recovery";
import {runtimeHealth} from "./runtime";
// Reuse the audited Pages handler; do not duplicate auth, caching or API routing.
// @ts-expect-error The existing JavaScript module is validated by its Node tests.
import website, {primaryHostRedirect} from "../../../docs/core-worker.js";
// @ts-expect-error The standalone watchdog remains independently Node-tested.
import watchdog from "../../../realtime/scripts/deploy/watchdog/worker.js";
export { RecoveryGate } from "./gate";

export interface UnifiedEnv extends Env {
  ASSETS: Fetcher;
  STATE: KVNamespace;
  ENABLE_DISPATCHER?: string;
  ENABLE_REALTIME_WATCHDOG?: string;
  EDGE_DEPLOY_WORKFLOW?: string;
  SITE_SOURCE_COMMIT?: string;
  SITE_ARTIFACT_COMMIT?: string;
  SITE_BUILD_KEY?: string;
  TELEGRAM_BOT_TOKEN?: string;
  TELEGRAM_ALERT_CHAT_ID?: string;
  DAILY_TELEGRAM_BOT_TOKEN?: string;
  ALERT_CHAT_ID?: string;
  ADMIN_GITHUB_TOKEN?: string;
  ADMIN_ACCESS_ISSUER?: string;
  ADMIN_ACCESS_AUD?: string;
  ADMIN_ALLOWED_EMAIL?: string;
  QUICK_POST_AI_API_KEY?: string;
  QUICK_POST_AI_ENABLED?: string;
  RUNTIME_HEALTH_URL?: string;
}

const OPERATIONS = new Set(["/health", "/ready", "/publication/check"]);

function publicationEnv(env: UnifiedEnv, ctx?: ExecutionContext): RecoveryEnv {
  return {...env, CORE_ONLY: true, ROLLING_FEED: true, PUBLICATION_FETCH: (request: Request) => website.fetch(request, env, ctx)};
}

export default {
  async fetch(request: Request, env: UnifiedEnv, ctx: ExecutionContext): Promise<Response> {
    const redirect = primaryHostRedirect(request);
    if (redirect) return redirect;
    const path = new URL(request.url).pathname;
    if (path === "/api/_telegram-group.json") {
      return new Response(null,{status:404,headers:{"Cache-Control":"no-store"}});
    }
    const live = await liveRoute(request, env);
    if (live) return live;
    if (!OPERATIONS.has(path)) {
      // Static shell validators do not describe the live news snapshot.
      let assetRequest = request;
      if (path === "/" && request.method === "GET") {
        const headers = new Headers(request.headers);
        headers.delete("If-None-Match"); headers.delete("If-Modified-Since");
        assetRequest = new Request(request, {headers});
      }
      const response = await website.fetch(assetRequest, env, ctx);
      return path === "/" && request.method === "GET" ? liveHome(response, env) : response;
    }
    if (path === "/publication/check" && env.ENABLE_DISPATCHER !== "true") {
      return Response.json({error: "scheduler_paused"}, {
        status: 503, headers: {"Cache-Control": "no-store"},
      });
    }
    const response = await dispatcher.fetch(request, publicationEnv(env, ctx));
    if (path !== "/health" || !response.ok) return response;
    const health = await response.json() as Record<string, unknown>;
    return Response.json({...health, service: "xiyunews", project: "xiyunews",
      core_only: true, rolling_feed: true, collection_interval_minutes: 5, languages: ["zh"], delivery: ["telegram-daily"],
      runner: await runtimeHealth(env.RUNTIME_HEALTH_URL),
      dispatcher_enabled: env.ENABLE_DISPATCHER === "true",
      realtime_watchdog_enabled: env.ENABLE_REALTIME_WATCHDOG === "true",
      site_source_commit: env.SITE_SOURCE_COMMIT ?? null,
      site_artifact_commit: env.SITE_ARTIFACT_COMMIT ?? null,
      site_build_key: env.SITE_BUILD_KEY ?? null,
    }, {headers: {"Cache-Control": "no-store"}});
  },

  async scheduled(controller: ScheduledController, env: UnifiedEnv): Promise<void> {
    const tasks: Promise<void>[] = [];
    if (env.ENABLE_DISPATCHER === "true") {
      tasks.push(Promise.resolve().then(() => dispatcher.scheduled(controller, publicationEnv(env))));
      tasks.push(Promise.resolve().then(() => checkPrivateAlerts(env, controller.scheduledTime)));
    }
    if (env.ENABLE_REALTIME_WATCHDOG === "true" && controller.cron === "*/5 * * * *") {
      tasks.push(Promise.resolve().then(() => watchdog.scheduled(controller, env)));
    }
    // A publication error must not suppress the independent server watchdog.
    const results = await Promise.allSettled(tasks);
    if (results.some(result => result.status === "rejected")) {
      throw new Error("xiyunews scheduled component failed; inspect component logs");
    }
  },
} satisfies ExportedHandler<UnifiedEnv>;
