import assert from "node:assert/strict";
import test from "node:test";
import { problems, step } from "./worker.js";

const now = 1_800_000_000_000;
const healthy = {
  telegram_enabled: true,
  sources: { okx: { state: "polling" }, hyperliquid: { state: "degraded" }, spot_stream_0: { state: "warming" } },
  monitoring: { per_market: { spot: { last_received: now / 1000 - 3 } }, notification_counts: { sent: 9 } },
  events: { archived: 5 },
};

test("healthy, degraded and warming sources are not problems", () => {
  assert.deepEqual(problems(healthy, now), []);
});

test("each failure kind is reported", () => {
  assert.deepEqual(problems(null, now), ["服务无响应：健康检查接口请求失败"]);
  const broken = {
    ...healthy,
    telegram_enabled: false,
    sources: { bybit: { state: "error" }, flow_tron: { state: "stale" } },
    monitoring: { per_market: { spot: { last_received: now / 1000 - 600 } }, notification_counts: { pending: 25 } },
    events: { pending: 10 },
  };
  assert.deepEqual(problems(broken, now), [
    "Telegram 推送已关闭",
    "行情采集中断：超过 5 分钟没有收到币安成交",
    "数据源异常：bybit、flow_tron",
    "推送积压：35 条待发送",
  ]);
});

test("alert after two failing checks, remind every two hours, announce recovery", () => {
  const found = ["服务无响应：健康检查接口请求失败"];
  let r = step(null, found, now);
  assert.equal(r.message, null); // One transient failure is ignored.
  r = step(r.state, found, now + 300_000);
  assert.match(r.message, /^🚨 xiyu.news 实时服务异常\n• 服务无响应/);
  r = step(r.state, found, now + 600_000);
  assert.equal(r.message, null); // No repeat within two hours.
  r = step(r.state, found, now + 300_000 + 2 * 3600_000);
  assert.match(r.message, /^⚠️ xiyu.news 实时服务仍未恢复/);
  r = step(r.state, [], now + 3 * 3600_000);
  assert.equal(r.message, "✅ xiyu.news 实时服务已恢复正常");
  assert.deepEqual(step(r.state, [], now).message, null); // Quiet when nothing was alerted.
});
