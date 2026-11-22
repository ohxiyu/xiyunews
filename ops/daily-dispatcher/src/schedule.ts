import { SCHEDULE_CRONS } from "./lib";
import { runSchedule } from "./recovery";
import { dispatchCollection, FEED_INTERVAL_MINUTES } from "./collection";
import { dispatchDistribution } from "./distribution";

// The five-minute clock still checks X and out-of-band recovery. Collection
// uses only its half-hour boundaries, including overnight.
export const COLLECTION_CRON = "*/5 * * * *";
// Earlier timers, still accepted while Cron configuration propagates.
const LEGACY_COMBINED_CRONS = new Set(["*/5 0-15 * * *", "*/5 1-15 * * *"]);
export const CONFIGURED_CRONS = [SCHEDULE_CRONS[0], SCHEDULE_CRONS[1], COLLECTION_CRON];

// Share one timer, but preserve the existing publication probe frequency.
export function publicationCron(time: number): string | null {
  const date = new Date(time);
  const hour = date.getUTCHours(), minute = date.getUTCMinutes();
  if (hour >= 0 && hour <= 3 && minute % 10 === 0) return "*/10 0-3 * * *";
  if (hour >= 4 && hour <= 15 && minute === 0) return "0 4-15 * * *";
  return null;
}

export async function runCombinedSchedule(cron: string, scheduledTime: number, env: Env): Promise<void> {
  if (cron !== COLLECTION_CRON && !LEGACY_COMBINED_CRONS.has(cron)) return runSchedule(cron, scheduledTime, env);
  const now = Math.max(scheduledTime, Date.now());
  // Publication, distribution and collection must not block one another.
  // Select the scheduled cadence, not the minute of eventual delivery. A
  // 10-minute tick arriving one minute late must still perform its check.
  // runSchedule separately uses current time for edition/window decisions.
  const publication = publicationCron(scheduledTime);
  const results = await Promise.allSettled([
      dispatchDistribution(env, "x", now).then(status => console.log(JSON.stringify({ event: "x_dispatch", status }))),
    publication ? runSchedule(publication, now, env) : Promise.resolve(),
    new Date(scheduledTime).getUTCMinutes() % FEED_INTERVAL_MINUTES === 0
      ? dispatchCollection(env, now).then(status => console.log(JSON.stringify({ event: "collection_dispatch", status })))
      : Promise.resolve(),
  ]);
  if (results.some(result => result.status === "rejected")) {
    throw new Error("Scheduled publication, distribution or collection dispatch failed; inspect workflow and dispatcher permissions");
  }
}
