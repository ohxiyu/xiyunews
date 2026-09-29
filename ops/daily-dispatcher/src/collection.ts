import { ACTIVE_STATUSES, fetchWorkflowRuns, githubRequest } from "./lib";

// GitHub's own schedule for feed-collection.yml often arrives hours late or
// not at all. The dispatcher keeps the newest collection at most four hours
// old; the GitHub schedule stays as a second, independent clock.
export const FEED_WORKFLOW = "feed-collection.yml";
export const FEED_INTERVAL_MS = 4 * 60 * 60 * 1000;

export type CollectionStatus =
  | "not_due" | "edition_window" | "active" | "fresh" | "dispatched";

export async function dispatchCollection(env: Env, now: number): Promise<CollectionStatus> {
  const date = new Date(now);
  const hour = date.getUTCHours(), minute = date.getUTCMinutes();
  // Check on the :x0 ticks only; the 5-minute timer also drives Square.
  if (minute % 10 >= 5) return "not_due";
  // 07:00-07:45 Shanghai: the daily edition collects on its own and shares
  // the workflows' concurrency group, so a collection would only delay it.
  if (hour === 23 && minute < 45) return "edition_window";
  const runs = (await fetchWorkflowRuns(env, FEED_WORKFLOW))
    .filter(run => run.headBranch === env.GITHUB_REF);
  if (runs.some(run => ACTIVE_STATUSES.has(run.status))) return "active";
  const latest = Math.max(0, ...runs.map(run => run.startedAt.getTime()));
  if (now - latest < FEED_INTERVAL_MS) return "fresh";
  await githubRequest(env,
    `/repos/${env.GITHUB_REPOSITORY}/actions/workflows/${FEED_WORKFLOW}/dispatches`,
    { method: "POST", body: JSON.stringify({ ref: env.GITHUB_REF }) });
  return "dispatched";
}
