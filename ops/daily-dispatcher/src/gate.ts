import { DurableObject } from "cloudflare:workers";

// One object per edition. Synchronous SQL claims are committed before any
// caller performs external I/O; a crashed caller leaves a bounded lease.
export class RecoveryGate extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    this.ctx.storage.sql.exec(
      "CREATE TABLE IF NOT EXISTS gate (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    );
  }

  private read(key: string): string | null {
    return this.ctx.storage.sql.exec<{ value: string }>(
      "SELECT value FROM gate WHERE key = ?", key,
    ).toArray()[0]?.value ?? null;
  }

  private write(key: string, value: string): void {
    this.ctx.storage.sql.exec(
      "INSERT OR REPLACE INTO gate (key, value) VALUES (?, ?)", key, value,
    );
  }

  claim(now: number): string | null {
    if (Number(this.read("lease_until") ?? "0") > now) return null;
    const token = crypto.randomUUID();
    this.write("owner", token);
    this.write("lease_until", String(now + 120_000));
    return token;
  }

  release(token: string): void {
    if (this.read("owner") === token) this.write("lease_until", "0");
  }

  firstRawSeen(now: number): number {
    const previous = this.read("raw_seen");
    if (previous !== null) return Number(previous);
    this.write("raw_seen", String(now));
    return now;
  }

  // Group delivery uses a DIFFERENT named object, not any publication lease.
  // No public HTTP handler exposes these trusted binding-only RPC methods.
  groupRead(key: string): string | null {
    if (!/^tg:[a-z0-9:.-]{1,100}$/.test(key)) throw new Error("invalid group key");
    return this.read(key);
  }

  groupRenew(token: string, now: number): void {
    if (this.read("owner") !== token || Number(this.read("lease_until")) <= now) {
      throw new Error("group lock lost");
    }
    this.write("lease_until", String(now + 120_000));
  }

  groupWrite(token: string, key: string, value: string, now: number): void {
    if (this.read("owner") !== token || Number(this.read("lease_until")) <= now) {
      throw new Error("group lock lost");
    }
    if (!/^tg:[a-z0-9:.-]{1,100}$/.test(key) || value.length > 500_000) {
      throw new Error("invalid group record");
    }
    this.write(key, value);
  }

  claimAction(token: string, kind: "daily" | "pages" | "collection", now: number): string {
    if (this.read("owner") !== token ||
        Number(this.read("lease_until")) <= now) return "lock_lost";
    const attempts = Number(this.read(kind + "_attempts") ?? "0");
    if (attempts >= (kind === "daily" ? 3 : 2)) return "retry_limit";
    if (Number(this.read(kind + "_next") ?? "0") > now) return "cooldown";
    this.write(kind + "_attempts", String(attempts + 1));
    // Keep the cooldown even on timeouts: GitHub/the hook may have accepted
    // the request although the response was lost.
    this.write(kind + "_next", String(now + 30 * 60_000));
    return "claimed";
  }
}
