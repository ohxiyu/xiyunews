import {env, runInDurableObject} from "cloudflare:test";
import {afterEach, expect, it, vi} from "vitest";
import {dispatchXAlarm, wakeup} from "../src/x-clock";
import * as delivery from "../src/distribution";

afterEach(() => vi.restoreAllMocks());

it("rejects invalid or unbounded wakeups", () => {
  const now = Date.now();
  expect(wakeup(null, now)).toBeNull();
  expect(wakeup({at: now + 1000, deadline: now}, now)).toBeUndefined();
  expect(wakeup({at: now - 120_000, deadline: now}, now)).toBeUndefined();
  expect(wakeup({at: now, deadline: now + 25 * 3600_000}, now)).toBeUndefined();
  expect(wakeup({at: now, deadline: now + 200}, now)).toEqual({at: now, deadline: now + 200});
});

it("arms a persistent deadline, guards non-due work, and cancels after acknowledgement", async () => {
  const door = env.RECOVERY_GATE.getByName("due-clock-test");
  const dispatch = vi.spyOn(delivery, "dispatchDistribution").mockResolvedValue("dispatched");
  const due = Date.now() + 50_000;
  const spec = {at: due, deadline: due + 60 * 60_000};
  expect(await door.armX(spec, false)).toBe(due);
  expect(await door.armX({at: due + 1_000, deadline: spec.deadline}, true)).toBe(due);
  await runInDurableObject(door, async (_, ctx) => {
    expect(await ctx.storage.getAlarm()).toBe(due);
    await dispatchXAlarm(ctx, env, due - 1);
    expect(dispatch).not.toHaveBeenCalled();
    await dispatchXAlarm(ctx, env, due);
    expect(dispatch).toHaveBeenCalledWith(env, "x", due);
    expect(await ctx.storage.getAlarm()).toBe(due + 10 * 60_000);
  });
  expect(await door.armX(null, false)).toBeNull();
  await runInDurableObject(door, async (_, ctx) => {
    expect(await ctx.storage.getAlarm()).toBeNull();
    await dispatchXAlarm(ctx, env, due + 10 * 60_000);
  });
  expect(dispatch).toHaveBeenCalledTimes(1);
});
