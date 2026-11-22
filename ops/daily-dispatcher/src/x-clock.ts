import {dispatchDistribution} from "./distribution";

export interface Wakeup {
  at: number;
  deadline: number;
}
interface Armed extends Wakeup {
  attempts: number;
}

const KEY = "x-wakeup";
const RETRY_MS = 10 * 60_000;
const MAX_ATTEMPTS = 5;

export function wakeup(value: unknown, now: number): Wakeup | null | undefined {
  if (value === null) return null;
  if (!value || typeof value !== "object") return undefined;
  const {at, deadline} = value as Wakeup;
  if (!Number.isSafeInteger(at) || !Number.isSafeInteger(deadline) ||
      at < now - 60_000 || deadline < at || deadline > now + 24 * 60 * 60_000) return undefined;
  return {at, deadline};
}

export async function armX(ctx: DurableObjectState, due: Wakeup | null, guard = false): Promise<number | null> {
  return ctx.blockConcurrencyWhile(async () => {
    if (due === null) {
      await ctx.storage.delete(KEY);
      await ctx.storage.deleteAlarm();
      return null;
    }
    const previous = guard && await ctx.storage.get<Armed>(KEY);
    if (previous && previous.deadline >= Date.now()) return previous.at;
    await ctx.storage.put(KEY, {...due, attempts: 0} satisfies Armed);
    await ctx.storage.setAlarm(due.at);
    return due.at;
  });
}

export async function dispatchXAlarm(ctx: DurableObjectState, env: Env, now = Date.now()): Promise<void> {
  const shouldDispatch = await ctx.blockConcurrencyWhile(async () => {
    const alarm = await ctx.storage.get<Armed>(KEY);
    if (!alarm) return false;
    if (alarm.at > now) {
      await ctx.storage.setAlarm(alarm.at);
      return false;
    }
    if (alarm.deadline < now || alarm.attempts >= MAX_ATTEMPTS) {
      return false;
    }
    // Arm a watchdog before contacting GitHub. A newer workflow's re-arm can
    // replace it while this request is in flight.
    const next = now + RETRY_MS;
    if (next <= alarm.deadline && alarm.attempts + 1 < MAX_ATTEMPTS) {
      await ctx.storage.put(KEY, {...alarm, at: next, attempts: alarm.attempts + 1});
      await ctx.storage.setAlarm(next);
    } else {
      await ctx.storage.put(KEY, {...alarm, attempts: MAX_ATTEMPTS});
    }
    return true;
  });
  if (shouldDispatch) {
    const status = await dispatchDistribution(env, "x", now);
    console.log(JSON.stringify({event: "x_due_alarm", status}));
  }
}
