import { ACTIVE_STATUSES, fetchWorkflowRuns, githubRequest, SCHEDULE_CRONS } from "./lib";
import { runSchedule } from "./recovery";
import { dispatchCollection } from "./collection";

// Every 5 minutes, all day. Square and publication checks keep their own
// windows below; the collection check needs the overnight ticks.
export const SQUARE_CRON = "*/5 * * * *";
// Earlier timers, still accepted while Cron configuration propagates.
const LEGACY_COMBINED_CRONS = new Set(["*/5 0-15 * * *", "*/5 1-15 * * *"]);
export const CONFIGURED_CRONS = [SCHEDULE_CRONS[0], SCHEDULE_CRONS[1], SQUARE_CRON];

// Share one timer, but preserve the existing publication probe frequency.
export function publicationCron(time: number): string | null {
  const date = new Date(time);
  const hour = date.getUTCHours(), minute = date.getUTCMinutes();
  if (hour >= 0 && hour <= 3 && minute % 10 === 0) return "*/10 0-3 * * *";
  if (hour >= 4 && hour <= 15 && minute === 0) return "0 4-15 * * *";
  return null;
}

export async function dispatchSquare(env: Env, now: number): Promise<string> {
  const date = new Date(now);
  const minute = date.getUTCHours() * 60 + date.getUTCMinutes();
  if (minute < 60 || minute > 930) return "outside_window";
  const runs = await fetchWorkflowRuns(env, "square-distribution.yml");
  if (runs.some(run => run.headBranch === env.GITHUB_REF && ACTIVE_STATUSES.has(run.status))) {
    return "active";
  }
  await githubRequest(env,
    `/repos/${env.GITHUB_REPOSITORY}/actions/workflows/square-distribution.yml/dispatches`,
    { method: "POST", body: JSON.stringify({ ref: env.GITHUB_REF, inputs: { queue_only: true } }) });
  return "dispatched";
}

export async function runCombinedSchedule(cron: string, scheduledTime: number, env: Env): Promise<void> {
  if (cron !== SQUARE_CRON && !LEGACY_COMBINED_CRONS.has(cron)) return runSchedule(cron, scheduledTime, env);
  const now = Math.max(scheduledTime, Date.now());
  // Publication, distribution and collection must not block one another.
  const publication = publicationCron(now);
  const results = await Promise.allSettled([
    dispatchSquare(env, now).then(status => console.log(JSON.stringify({ event: "square_dispatch", status }))),
    publication ? runSchedule(publication, now, env) : Promise.resolve(),
    dispatchCollection(env, now).then(status => console.log(JSON.stringify({ event: "collection_dispatch", status }))),
  ]);
  if (results.some(result => result.status === "rejected")) {
    throw new Error("Scheduled publication, Square or collection dispatch failed; inspect workflow and dispatcher permissions");
  }
}
