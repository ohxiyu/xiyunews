import { ACTIVE_STATUSES, fetchWorkflowRuns, githubRequest } from "./lib";

// GitHub's own schedule for feed-collection.yml often arrives hours late or
// not at all. The dispatcher keeps the newest collection at the configured five-minute cadence
// when no prior run is active; the GitHub schedule stays as a second, independent clock.
export const FEED_WORKFLOW = "feed-collection.yml";
export const FEED_INTERVAL_MS = 5 * 60 * 1000;

export type CollectionStatus =
  | "not_due" | "edition_window" | "active" | "fresh" | "dispatched"
  | "failed_waiting" | "retry_dispatched" | "check_in_progress"
  | "cooldown" | "retry_limit" | "lock_lost";

export function isSourceCollection(run: {displayTitle?: string}): boolean {
  return !["Operations alert test","Operations topic setup"].includes(run.displayTitle ?? "");
}

export async function dispatchCollection(env: Env, now: number): Promise<CollectionStatus> {
  const interval = FEED_INTERVAL_MS;
  const runs = (await fetchWorkflowRuns(env, FEED_WORKFLOW))
    .filter(run => run.headBranch === env.GITHUB_REF);
  if (runs.some(run => ACTIVE_STATUSES.has(run.status))) return "active";
  const newest = runs.filter(isSourceCollection).sort((a, b) => b.startedAt.getTime() - a.startedAt.getTime())[0];
  const age = now - (newest?.startedAt.getTime() ?? 0);
  const failed = newest?.status === "completed" &&
    ["failure", "timed_out", "startup_failure"].includes(newest.conclusion ?? "");
  // An operator cancellation is respected. Successful or cancelled recent
  // runs retain the normal cadence; infrastructure failures retry after 30m.
  if (age < interval && !failed) return "fresh";
  if (failed && age < 30 * 60_000) return "failed_waiting";
  const gate = env.RECOVERY_GATE.getByName("collection-" + (failed ? "failed-" + newest!.startedAt.getTime() : Math.floor(now / interval)));
  const owner = await gate.claim(now);
  if (!owner) return "check_in_progress";
  try {
    const claim = await gate.claimAction(owner, "collection", now);
    if (claim !== "claimed") return claim as CollectionStatus;
    await githubRequest(env,
    `/repos/${env.GITHUB_REPOSITORY}/actions/workflows/${FEED_WORKFLOW}/dispatches`,
    { method: "POST", body: JSON.stringify({ ref: env.GITHUB_REF }) });
    return failed ? "retry_dispatched" : "dispatched";
  } finally { await gate.release(owner); }
}
