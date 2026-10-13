// No credentials, redirects, process details or private deployment paths.
export async function runtimeHealth(url: string | undefined, now = Date.now()): Promise<Record<string, unknown>> {
  if (!url) return {status: "not_configured"};
  if (url !== "https://api.xiyu.news/ops/runtime.json") throw new Error("Invalid runtime probe origin");
  try {
    const response = await fetch(url, {redirect: "manual", signal: AbortSignal.timeout(5000), headers: {"Cache-Control": "no-cache"}});
    if (!response.ok) return {status: "unreachable"};
    const reader = response.body?.getReader();
    if (!reader) return {status: "invalid"};
    let text = "", size = 0;
    try {
      while (true) {
        const part = await reader.read();
        if (part.done) break;
        size += part.value.length;
        if (size > 4096) return {status: "invalid"};
        text += new TextDecoder().decode(part.value);
      }
    } finally { await reader.cancel(); }
    const data = JSON.parse(text);
    if (data.service !== "xiyunews-runner" || !["busy", "idle", "paused", "stopped"].includes(data.status) ||
      !Number.isInteger(data.checked_at) || data.checked_at * 1000 > now + 30_000 || now - data.checked_at * 1000 > 180_000 ||
      !Number.isInteger(data.starts_24h) || data.starts_24h < 0 || data.starts_24h > 3) return {status: "stale_or_invalid"};
    return {status: data.status, checked_at: data.checked_at, starts_24h: data.starts_24h};
  } catch { return {status: "unreachable"}; }
}
