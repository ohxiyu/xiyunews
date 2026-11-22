// Public projection of the latest accepted edition. Never contains the private
// selection, run report, queue or delivery receipts.
export interface LatestEdition {
  day: string;
  artifact: string;
  build: string;
  home: string;
  page: string;
  api: string;
  rss: string;
}

export interface EditionEnv extends Env {
  SITE_ARTIFACT_COMMIT?: string;
  SITE_BUILD_KEY?: string;
  SITE_EDITION_DATE?: string;
}

const dates = /^(\d{4})\/(\d{2})\/(\d{2})\/summary-zh(?:\.html)?$/;
const fragments = /^editions\/(\d{4}-\d{2}-\d{2})\/(zh\.html|edition\.json)$/;
const homepage = new Set(["", "index.html"]);

export function validateLatest(input: unknown, env: EditionEnv): input is LatestEdition {
  if (!input || typeof input !== "object") return false;
  const row = input as Record<string, unknown>;
  if (row.artifact !== env.SITE_ARTIFACT_COMMIT || row.build !== env.SITE_BUILD_KEY ||
      row.day !== env.SITE_EDITION_DATE || typeof row.day !== "string" ||
      !/^\d{4}-\d{2}-\d{2}$/.test(row.day) || typeof row.artifact !== "string" ||
      !/^[a-f0-9]{40}$/.test(row.artifact) || typeof row.build !== "string" || !row.build) return false;
  const {home, page, api, rss} = row;
  if (typeof home !== "string" || typeof page !== "string" || typeof api !== "string" ||
      typeof rss !== "string" || !home.includes(`data-latest-edition-date="${row.day}"`) ||
      !page.includes(`data-date="${row.day}"`) || !rss.includes("<item>") ||
      rss.split("<item>").length !== 2) return false;
  try {
    const parsed = JSON.parse(api);
    return parsed.date === row.day && Array.isArray(parsed.items) && parsed.items.length > 0;
  } catch {
    return false;
  }
}

export function editionStore(env: EditionEnv) {
  return env.RECOVERY_GATE.getByName("current-public-edition");
}

export async function latestEditionRoute(request: Request, env: EditionEnv): Promise<Response | null> {
  const url = new URL(request.url);
  if (url.hostname !== "xiyu.news" || !env.SITE_EDITION_DATE ||
      !["GET", "HEAD"].includes(request.method)) return null;
  let path: string;
  try {
    path = decodeURIComponent(url.pathname).replace(/^\/+|\/+$/g, "").replace(/\/+/g, "/");
  } catch {
    return null;
  }
  const dated = path.match(dates);
  const fragment = path.match(fragments);
  const date = dated?.slice(1).join("-") ?? fragment?.[1];
  if (date && date !== env.SITE_EDITION_DATE) {
    return new Response(null, {status: 410, headers: {"Cache-Control": "no-store"}});
  }
  const isHome = homepage.has(path);
  const isApi = path === "api/latest.json" || fragment?.[2] === "edition.json";
  const isRss = path === "feed.xml";
  if (!isHome && !dated && !isApi && !isRss) return null;
  // A new code deploy ships a verified single-edition static fallback. Until
  // its matching record is seeded, or for a storage read failure, use it.
  const row = await editionStore(env).readLatestEdition().catch(() => undefined);
  if (!row || row.artifact !== env.SITE_ARTIFACT_COMMIT || row.build !== env.SITE_BUILD_KEY ||
      row.day !== env.SITE_EDITION_DATE) return null;
  const body = isHome ? row.home : isApi ? row.api : isRss ? row.rss : row.page;
  const type = isApi ? "application/json" : isRss ? "application/rss+xml" : "text/html";
  return new Response(request.method === "HEAD" ? null : body, {headers: {
    "Content-Type": `${type}; charset=utf-8`,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Xiyunews-Edition-Source": "durable-object",
  }});
}
