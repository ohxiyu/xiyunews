// FomoBTC watchdog: runs on Cloudflare (outside the server) every 5 minutes, reads the
// public health endpoint and messages the operator privately when the service is down
// or degraded. It never posts to the public group.
const HEALTH_URL = "https://api.xiyu.news/api/health";
const CONFIRM_CHECKS = 2; // Alert only after two consecutive failing checks (10 minutes).
const REMIND_MS = 2 * 60 * 60 * 1000;

export function problems(health, nowMs) {
  if (!health) return ["服务无响应：健康检查接口请求失败"];
  const found = [];
  if (!health.telegram_enabled) found.push("Telegram 推送已关闭");
  const spot = health.monitoring?.per_market?.spot;
  if (!spot?.last_received || nowMs / 1000 - spot.last_received > 300) {
    found.push("行情采集中断：超过 5 分钟没有收到币安成交");
  }
  const failing = Object.entries(health.sources || {})
    .filter(([, source]) => ["error", "stale", "blocked"].includes(source.state))
    .map(([name]) => name)
    .sort();
  if (failing.length) found.push(`数据源异常：${failing.join("、")}`);
  const queued =
    (health.events?.pending || 0) + (health.monitoring?.notification_counts?.pending || 0);
  if (queued > 30) found.push(`推送积压：${queued} 条待发送`);
  return found;
}

// Pure state machine: returns the next stored state and an optional message to send.
export function step(state, found, nowMs) {
  const previous = state || { failing: 0, alerted: false, lastAlert: 0 };
  if (!found.length) {
    const message = previous.alerted ? "✅ xiyu.news 实时服务已恢复正常" : null;
    return { state: { failing: 0, alerted: false, lastAlert: 0 }, message };
  }
  const failing = previous.failing + 1;
  const due = !previous.alerted || nowMs - previous.lastAlert >= REMIND_MS;
  if (failing < CONFIRM_CHECKS || !due) {
    return { state: { ...previous, failing }, message: null };
  }
  const title = previous.alerted ? "⚠️ xiyu.news 实时服务仍未恢复" : "🚨 xiyu.news 实时服务异常";
  const message = [title, ...found.map((item) => `• ${item}`), "", HEALTH_URL].join("\n");
  return { state: { failing, alerted: true, lastAlert: nowMs }, message };
}

async function readHealth() {
  try {
    const response = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(10000) });
    return response.ok ? await response.json() : null;
  } catch {
    return null;
  }
}

async function notify(env, text) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.ALERT_CHAT_ID) {
    console.log("watchdog: Telegram secrets missing; alert not sent");
    return false;
  }
  try {
    const response = await fetch(
      `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ chat_id: env.ALERT_CHAT_ID, text, disable_web_page_preview: true }),
        signal: AbortSignal.timeout(10000),
      },
    );
    return response.ok;
  } catch {
    return false; // Never log the request: its URL contains the bot token.
  }
}

export default {
  async scheduled(controller, env) {
    // Empty Cron configuration can take up to 15 minutes to propagate. Disable
    // callbacks explicitly on the old Worker before enabling the new owner.
    if (env.XIYUNEWS_LEGACY_DISABLED === "true") {
      console.log("xiyunews legacy watchdog disabled; cron ignored");
      return;
    }
    const now = Date.now();
    const found = problems(await readHealth(), now);
    const stored = await env.STATE.get("state", "json");
    const { state, message } = step(stored, found, now);
    if (message && !(await notify(env, message))) {
      state.alerted = stored?.alerted || false; // Retry the alert on the next check.
      state.lastAlert = stored?.lastAlert || 0;
    }
    if (JSON.stringify(state) !== JSON.stringify(stored)) await env.STATE.put("state", JSON.stringify(state));
    console.log(`watchdog: ${found.length ? found.join(" | ") : "ok"}`);
  },
};
