import {legacyRoute} from "./legacy";
import dispatcher from "./index";
import {runtimeHealth} from "./runtime";
import type { RecoveryEnv } from "./recovery";
import {publicationRoute} from "./publication-state";
// Reuse the audited Pages handler; do not duplicate auth, caching or API routing.
// @ts-expect-error The existing JavaScript module is validated by its Node tests.
import website, {primaryHostRedirect} from "../../../docs/core-worker.js";
export { RecoveryGate } from "./gate";

export interface UnifiedEnv extends Env {
  ASSETS: Fetcher;
  STATE: KVNamespace;
  ENABLE_DISPATCHER?: string;
  EDGE_DEPLOY_WORKFLOW?: string;
  SITE_SOURCE_COMMIT?: string;
  SITE_ARTIFACT_COMMIT?: string;
  SITE_BUILD_KEY?: string;
  ADMIN_GITHUB_TOKEN?: string;
  ADMIN_ACCESS_ISSUER?: string;
  ADMIN_ACCESS_AUD?: string;
  ADMIN_ALLOWED_EMAIL?: string;
  QUICK_POST_AI_API_KEY?: string;
  QUICK_POST_AI_ENABLED?: string;
  RUNTIME_HEALTH_URL?: string;
  PUBLICATION_RUNTIME?: string;
}

const OPERATIONS = new Set(["/health", "/ready", "/publication/check"]);

function publicationEnv(env: UnifiedEnv, ctx?: ExecutionContext): RecoveryEnv {
  return {...env, PUBLICATION_FETCH: (request: Request) => website.fetch(request, env, ctx)};
}

export default {
  async fetch(request: Request, env: UnifiedEnv, ctx: ExecutionContext): Promise<Response> {
    const redirect = primaryHostRedirect(request);
    if (redirect) return redirect;
    const path = new URL(request.url).pathname;
    if (path.startsWith("/internal/publication-state/")) return publicationRoute(request,env);
    if (path === "/api/_telegram-group.json") {
      return new Response(null,{status:404,headers:{"Cache-Control":"no-store"}});
    }
    const live = await legacyRoute(request, env);
    if (live) return live;
    if (!OPERATIONS.has(path)) {
      return website.fetch(request,env,ctx);
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
      product: "daily-edition", collection_interval_minutes: 5, languages: ["zh"], delivery: ["x"],
      runner: env.PUBLICATION_RUNTIME === "hosted" ? {status:"github-hosted",state_backend:"cloudflare-private",service:"xiyunews"} : await runtimeHealth(env.RUNTIME_HEALTH_URL),
      modules: ["daily-edition"],
      dispatcher_enabled: env.ENABLE_DISPATCHER === "true",
      site_source_commit: env.SITE_SOURCE_COMMIT ?? null,
      site_artifact_commit: env.SITE_ARTIFACT_COMMIT ?? null,
      site_build_key: env.SITE_BUILD_KEY ?? null,
    }, {headers: {"Cache-Control": "no-store"}});
  },

  async scheduled(controller: ScheduledController, env: UnifiedEnv): Promise<void> {
    if (env.ENABLE_DISPATCHER === "true") {
      await dispatcher.scheduled(controller, publicationEnv(env));
    }
  },
} satisfies ExportedHandler<UnifiedEnv>;
