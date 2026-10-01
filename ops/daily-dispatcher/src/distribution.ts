import { ACTIVE_STATUSES, editionContextFor, fetchWorkflowRuns, githubRequest } from "./lib";

type Kind = "square" | "x";
const MAX_JSON_BYTES = 1_048_576;
const X_STATUSES = new Set(["planned", "pending", "sent", "unknown", "failed", "expired", "skipped", "void"]);
const SQUARE_STATUSES = new Set(["sent", "pending", "unknown", "rejected", "blocked"]);

function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`Invalid ${label}`);
  return value as Record<string, unknown>;
}

function stamp(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string" || !/(?:Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) {
    throw new Error("Invalid queue timestamp");
  }
  return Date.parse(value);
}

function jobs(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value) || value.length > 1000) throw new Error("Invalid queue jobs");
  return value.map(job => record(job, "job"));
}

// This gate never writes a plan or sends a social request. Python remains the
// authoritative planner/checkpointer; true means only "run its existing gate".
export function squareHasWork(payload: unknown, now: number, day: string): boolean {
  const state = record(payload, "Square queue");
  if (state.version !== 1) throw new Error("Invalid Square queue version");
  const editions = record(state.editions, "Square editions");
  const plans = record(state.plans ?? {}, "Square plans");
  const rows = record(editions[day] ?? {}, "Square outcomes");
  let recent = false;
  for (const value of Object.values(rows)) {
    const row = record(value, "Square outcome");
    if (!SQUARE_STATUSES.has(String(row.status))) throw new Error("Invalid Square outcome status");
    const attempted = stamp(row.attempted_at);
    if (attempted !== null && now - attempted < 300_000) recent = true;
  }
  const plan = plans[day];
  if (plan === undefined) return true; // Existing workflow bootstraps today's plan.
  const planned = record(plan, "Square plan");
  if (typeof planned.revision !== "string") throw new Error("Invalid Square revision");
  const seen = new Set<string>();
  let due = false;
  for (const job of jobs(planned.jobs)) {
    if (typeof job.id !== "string" || !job.id || seen.has(job.id)) throw new Error("Invalid Square job identity");
    seen.add(job.id);
    const dueAt = stamp(job.due_at);
    if (!Object.hasOwn(rows, job.id) && dueAt !== null && dueAt <= now) due = true;
  }
  return !recent && due;
}

export function xHasWork(payload: unknown, feed: unknown, now: number, day: string, timezone: string): boolean {
  const state = record(payload, "X queue");
  if (state.version !== 2) throw new Error("Invalid X queue version");
  const editions = record(state.editions, "X editions");
  const published = record(feed, "published state");
  if (published.timezone !== timezone || typeof published.date !== "string") throw new Error("Invalid published state timezone/date");
  const current = editions[day];
  let work = false;
  for (const value of Object.values(editions)) {
    const edition = record(value, "X edition");
    if (edition.status !== "active" && edition.status !== "skipped_late") throw new Error("Invalid X edition status");
    const planned = jobs(edition.jobs);
    const seen = new Set<string>();
    for (const job of planned) {
      if (!X_STATUSES.has(String(job.status)) || typeof job.language !== "string" || !Number.isInteger(job.slot)) {
        throw new Error("Invalid X job status/identity");
      }
      const identity = `${job.language}:${job.slot}`;
      if (seen.has(identity)) throw new Error("Duplicate X job identity");
      seen.add(identity);
      const due = stamp(job.due_at), deadline = stamp(job.deadline);
      stamp(job.attempted_at);
      if (job.status === "pending") work = true; // Python converts this to unknown, NEVER resends it.
      if (job.status !== "planned") continue;
      if (deadline !== null && now > deadline) work = true;
      if (due === null) {
        const anchor = planned.find(row => row.language === job.language && row.slot === Number(job.slot) - 1);
        if (anchor && anchor.status !== "planned") work = true; // Set the next slot's persisted clock.
      } else if (edition === current && edition.status === "active" && due <= now &&
          !planned.some(row => row.language === job.language && row.status === "failed")) {
        work = true;
      }
    }
  }
  if (published.date === day) {
    const updatedAt = stamp(published.updated_at);
    if (updatedAt === null) throw new Error("Missing published state timestamp");
    if (!current || stamp(record(current, "X edition").state_updated_at) !== updatedAt) work = true;
  }
  return work;
}

export async function readPrivateJson(env: Env, path: string, ref: string): Promise<unknown> {
  const response = await githubRequest(env,
    `/repos/${env.GITHUB_REPOSITORY}/contents/${path}?ref=${encodeURIComponent(ref)}`,
    { headers: { Accept: "application/vnd.github.raw+json" } });
  // A 404 is an error, not an empty queue (it may be missing permission).
  if (Number(response.headers.get("Content-Length")) > MAX_JSON_BYTES) {
    await response.body?.cancel();
    throw new Error("Oversized queue JSON");
  }
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Missing queue JSON body");
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      size += next.value.byteLength;
      if (size > MAX_JSON_BYTES) { await reader.cancel(); throw new Error("Oversized queue JSON"); }
      chunks.push(next.value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder("utf-8", { fatal: true, ignoreBOM: false }).decode(bytes));
}

export async function dispatchDistribution(env: Env, kind: Kind, now: number): Promise<string> {
  const clock = new Date(now), minute = clock.getUTCHours() * 60 + clock.getUTCMinutes();
  // Preserve Shanghai 09:00–23:30 Square; X also covers the 07:26 kickoff.
  if (kind === "square" ? minute < 60 || minute > 930 : minute > 930 && minute < 1406) return "outside_window";
  const workflow = `${kind}-distribution.yml`;
  const runs = (await fetchWorkflowRuns(env, workflow)).filter(run => run.headBranch === env.GITHUB_REF);
  if (runs.some(run => ACTIVE_STATUSES.has(run.status))) return "active";
  const latest = runs.reduce<typeof runs[number] | undefined>((last, run) =>
    !last || run.startedAt > last.startedAt ? run : last, undefined);
  if (latest && latest.conclusion === "failure" && now - latest.startedAt.getTime() < 1_800_000) return "cooldown";
  const day = editionContextFor(now, env.EDITION_TIMEZONE, Number(env.EDITION_CUTOFF_HOUR)).date;
  let work: boolean;
  if (kind === "square") {
    work = squareHasWork(await readPrivateJson(env, "queue.json", "square-queue"), now, day);
  } else {
    const config = record(await readPrivateJson(env, "data/config.github.json", env.GITHUB_REF), "config");
    const delivery = record(config.x_delivery, "X delivery config");
    if (delivery.enabled !== true || delivery.mode !== "drip") return "disabled";
    const [queue, feed] = await Promise.all([
      readPrivateJson(env, "data/x-queue.json", "x-queue"),
      readPrivateJson(env, "_data/bmtnews_state.json", "gh-pages"),
    ]);
    work = xHasWork(queue, feed, now, day, env.EDITION_TIMEZONE);
  }
  if (!work) return "idle";
  await githubRequest(env, `/repos/${env.GITHUB_REPOSITORY}/actions/workflows/${workflow}/dispatches`,
    { method: "POST", body: JSON.stringify({ ref: env.GITHUB_REF,
      inputs: kind === "square" ? { queue_only: true } : {} }) });
  return "dispatched";
}
