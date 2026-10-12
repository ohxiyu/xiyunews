import dispatcher from "./index";
import type { RecoveryEnv } from "./recovery";
import {runGroupNews} from "./group-news";
// Reuse the audited Pages handler; do not duplicate auth, caching or API routing.
// @ts-expect-error The existing JavaScript module is validated by its Node tests.
import website from "../../../docs/_worker.js";
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
  TELEGRAM_BOT_TOKEN?: string;
  ALERT_CHAT_ID?: string;
  ADMIN_GITHUB_TOKEN?: string;
  ADMIN_ACCESS_ISSUER?: string;
  ADMIN_ACCESS_AUD?: string;
  ADMIN_ALLOWED_EMAIL?: string;
  QUICK_POST_AI_API_KEY?: string;
  QUICK_POST_AI_ENABLED?: string;
}

const OPERATIONS = new Set(["/health", "/ready", "/publication/check"]);

function publicationEnv(env: UnifiedEnv, ctx?: ExecutionContext): RecoveryEnv {
  return {...env, PUBLICATION_FETCH: (request: Request) => website.fetch(request, env, ctx)};
}

export default {
  async fetch(request: Request, env: UnifiedEnv, ctx: ExecutionContext): Promise<Response> {
    const path = new URL(request.url).pathname;
    if (path === "/api/_telegram-group.json") {
      return new Response(null,{status:404,headers:{"Cache-Control":"no-store"}});
    }
    if (!OPERATIONS.has(path)) return website.fetch(request, env, ctx);
    if (path === "/publication/check" && env.ENABLE_DISPATCHER !== "true") {
      return Response.json({error: "scheduler_paused"}, {
        status: 503, headers: {"Cache-Control": "no-store"},
      });
    }
    const response = await dispatcher.fetch(request, publicationEnv(env, ctx));
    if (path !== "/health" || !response.ok) return response;
    const health = await response.json() as Record<string, unknown>;
    return Response.json({...health, service: "xiyunews", project: "xiyunews",
      dispatcher_enabled: env.ENABLE_DISPATCHER === "true",
      realtime_watchdog_enabled: env.ENABLE_REALTIME_WATCHDOG === "true",
      site_source_commit: env.SITE_SOURCE_COMMIT ?? null,
      site_artifact_commit: env.SITE_ARTIFACT_COMMIT ?? null,
    }, {headers: {"Cache-Control": "no-store"}});
  },

  async scheduled(controller: ScheduledController, env: UnifiedEnv): Promise<void> {
    const tasks: Promise<void>[] = [];
    if (env.ENABLE_DISPATCHER === "true") {
      tasks.push(Promise.resolve().then(() => dispatcher.scheduled(controller, publicationEnv(env))));
    }
    if (env.ENABLE_REALTIME_WATCHDOG === "true" && controller.cron === "*/5 * * * *") {
      tasks.push(Promise.resolve().then(() => watchdog.scheduled(controller, env)));
    }
    if (env.ENABLE_DISPATCHER === "true" && controller.cron === "*/5 * * * *") {
      tasks.push(Promise.resolve().then(() => runGroupNews(env)));
    }
    // A publication error must not suppress the independent server watchdog.
    const results = await Promise.allSettled(tasks);
    if (results.some(result => result.status === "rejected")) {
      throw new Error("xiyunews scheduled component failed; inspect component logs");
    }
  },
} satisfies ExportedHandler<UnifiedEnv>;
