// Private, fenced SQLite-page transport. No public runtime data or credentials.
// Reuses the existing RecoveryGate namespace; this is live state, not backups.
const AUDIENCE = "https://xiyu.news/internal/publication-state";
const WORKFLOWS = new Set(["feed-collection.yml", "daily-summary.yml", "daily-telegram.yml",
  "x-distribution.yml", "cloudflare-unified.yml", "publication-runtime.yml"]);
const PAGE = 65536, MAX_SIZE = 128 * 1024 * 1024, LEASE = 40 * 60_000;
const headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"};
const result = (body: unknown, status = 200) => Response.json(body, {status, headers});
function decode(value: string): Uint8Array {
  return Uint8Array.from(atob(value.replaceAll("-", "+").replaceAll("_", "/")), c => c.charCodeAt(0));
}
async function digest(bytes: Uint8Array): Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), n => n.toString(16).padStart(2,"0")).join("");
}
let keys: {expires: number; values: (JsonWebKey & {kid?: string})[]} | undefined;
export async function identity(token: string, now = Date.now()): Promise<Record<string, unknown>> {
  const parts = token.split(".");
  if (parts.length !== 3 || token.length > 20000) throw new Error("identity rejected");
  const head = JSON.parse(new TextDecoder().decode(decode(parts[0]!)));
  if (head.alg !== "RS256" || typeof head.kid !== "string") throw new Error("identity rejected");
  if (!keys || keys.expires < now) {
    const response = await fetch("https://token.actions.githubusercontent.com/.well-known/jwks", {signal: AbortSignal.timeout(5000)});
    if (!response.ok) throw new Error("identity unavailable");
    const value = await response.json() as {keys: (JsonWebKey & {kid?: string})[]};
    keys = {expires: now + 300_000, values: value.keys};
  }
  const jwk = keys.values.find(k => k.kid === head.kid);
  if (!jwk) throw new Error("identity rejected");
  const key = await crypto.subtle.importKey("jwk", jwk, {name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"}, false, ["verify"]);
  if (!await crypto.subtle.verify("RSASSA-PKCS1-v1_5",key,decode(parts[2]!),new TextEncoder().encode(parts[0]+"."+parts[1]))) throw new Error("identity rejected");
  const c = JSON.parse(new TextDecoder().decode(decode(parts[1]!)));
  const prefix = "ohxiyu/xiyunews/.github/workflows/";
  const workflow = typeof c.workflow_ref === "string" && c.workflow_ref.startsWith(prefix) && c.workflow_ref.endsWith("@refs/heads/main")
    ? c.workflow_ref.slice(prefix.length, -"@refs/heads/main".length) : "";
  if (c.iss !== "https://token.actions.githubusercontent.com" || c.aud !== AUDIENCE ||
      c.repository !== "ohxiyu/xiyunews" || c.repository_id !== "1341754381" || c.ref !== "refs/heads/main" ||
      c.sub !== "repo:ohxiyu/xiyunews:ref:refs/heads/main" || !WORKFLOWS.has(workflow) ||
      !["schedule","workflow_dispatch","workflow_run","push"].includes(c.event_name) ||
      !Number.isFinite(c.exp) || c.exp * 1000 <= now || !Number.isFinite(c.nbf) || c.nbf * 1000 > now + 30000 ||
      !/^\d+$/.test(c.run_id) || !/^\d+$/.test(c.run_attempt)) throw new Error("identity rejected");
  return {...c, migration: workflow === "publication-runtime.yml"};
}

export async function publicationRoute(request: Request, env: Env): Promise<Response> {
  if (request.method !== "POST") return result({error:"method"},405);
  const bearer = request.headers.get("Authorization") ?? "";
  let c: Record<string, unknown>;
  try { c = await identity(bearer.startsWith("Bearer ") ? bearer.slice(7) : ""); }
  catch { return result({error:"unauthorized"},401); }
  if (Number(request.headers.get("Content-Length")) > 2 * 1024 * 1024) return result({error:"too_large"},413);
  const raw = await request.text();
  if (raw.length > 2 * 1024 * 1024) return result({error:"too_large"},413);
  let body: Record<string, unknown>;
  try {body = JSON.parse(raw);} catch {return result({error:"invalid"},400);}
  if (typeof body.owner !== "string" || !body.owner.startsWith(c.run_id+":"+c.run_attempt+":") ||
      !/^\d+:\d+:[a-f0-9]{32}$/.test(body.owner)) return result({error:"owner"},403);
  const action = new URL(request.url).pathname.split("/").at(-1)!;
  const gate = env.RECOVERY_GATE.get(env.RECOVERY_GATE.idFromName("publication-state-v1"));
  return gate.publicationState(action, body, Boolean(c.migration));
}

export interface PageInput extends Record<string, SqlStorageValue> {n:number; hash:string; data:string}
interface Manifest {version:number; size:number; hashes:string[]; ready:boolean}
export async function stateOperation(ctx: DurableObjectState, action: string, b: Record<string, unknown>, migration: boolean, now = Date.now()): Promise<Response> {
  const sql = ctx.storage.sql;
  sql.exec("CREATE TABLE IF NOT EXISTS publication_control (key TEXT PRIMARY KEY, value TEXT NOT NULL)");
  sql.exec("CREATE TABLE IF NOT EXISTS publication_pages (n INTEGER PRIMARY KEY, hash TEXT NOT NULL, data TEXT NOT NULL)");
  sql.exec("CREATE TABLE IF NOT EXISTS publication_pending (n INTEGER PRIMARY KEY, hash TEXT NOT NULL, data TEXT NOT NULL)");
  const read = (k:string) => sql.exec<{value:string}>("SELECT value FROM publication_control WHERE key=?",k).toArray()[0]?.value;
  const write = (k:string,v:string) => {sql.exec("INSERT OR REPLACE INTO publication_control VALUES(?,?)",k,v);};
  const manifest = JSON.parse(read("manifest") ?? '{"version":0,"size":0,"hashes":[],"ready":false}') as Manifest;
  const owns = () => read("owner") === b.owner && Number(read("until")) > now;
  if (action === "acquire") {
    if (!manifest.ready && !migration) return result({error:"not_initialized"},503);
    if (Number(read("until")) > now && read("owner") !== b.owner) return result({error:"busy"},423);
    if (read("owner") !== b.owner) sql.exec("DELETE FROM publication_pending");
    write("owner",b.owner as string); write("until",String(now+LEASE));
    return result({...manifest,until:now+LEASE});
  }
  if (!owns()) return result({error:"lease_lost"},409);
  if (action === "release") {
    write("until","0");sql.exec("DELETE FROM publication_pending");return result({released:true});
  }
  if (b.version !== manifest.version) return result({error:"version_conflict"},409);
  if (action === "download") {
    const start = Number(b.start);
    if (!Number.isInteger(start) || start < 0) return result({error:"invalid_page"},400);
    return result({pages:sql.exec<PageInput>("SELECT n,hash,data FROM publication_pages WHERE n>=? ORDER BY n LIMIT 8",start).toArray()});
  }
  if (action === "upload") {
    if (!Array.isArray(b.pages) || b.pages.length > 8) return result({error:"invalid_pages"},400);
    for (const p of b.pages as PageInput[]) {
      if (!Number.isInteger(p.n) || p.n < 0 || p.n >= MAX_SIZE/PAGE || !/^[a-f0-9]{64}$/.test(p.hash) || typeof p.data !== "string" || p.data.length > 100000) return result({error:"invalid_page"},400);
      if (await digest(decode(p.data)) !== p.hash) return result({error:"checksum"},400);
    }
    // Digest verification awaits; recheck fencing after yielding to other RPCs.
    if (!owns() || JSON.parse(read("manifest") ?? '{"version":0}').version !== b.version) return result({error:"lease_lost"},409);
    ctx.storage.transactionSync(() => {
      for (const p of b.pages as PageInput[]) sql.exec("INSERT OR REPLACE INTO publication_pending VALUES(?,?,?)",p.n,p.hash,p.data);
    });
    return result({uploaded:(b.pages as unknown[]).length});
  }
  if (action === "commit") {
    const size = Number(b.size), hashes = b.hashes;
    if ((!manifest.ready && !migration) || !Number.isInteger(size) || size < 512 || size > MAX_SIZE ||
        !Array.isArray(hashes) || hashes.length !== Math.ceil(size/PAGE) || hashes.some(h=>typeof h !== "string" || !/^[a-f0-9]{64}$/.test(h))) return result({error:"invalid_manifest"},400);
    const available = new Map(sql.exec<{n:number;hash:string}>("SELECT n,hash FROM publication_pages").toArray().map(p=>[p.n,p.hash]));
    for (const p of sql.exec<{n:number;hash:string}>("SELECT n,hash FROM publication_pending").toArray()) available.set(p.n,p.hash);
    if (hashes.some((hash,n)=>available.get(n)!==hash)) return result({error:"incomplete"},409);
    const next = {version:manifest.version+1,size,hashes,ready:true};
    ctx.storage.transactionSync(()=>{
      sql.exec("INSERT OR REPLACE INTO publication_pages SELECT n,hash,data FROM publication_pending");
      sql.exec("DELETE FROM publication_pages WHERE n>=?",hashes.length);
      sql.exec("DELETE FROM publication_pending");
      write("manifest",JSON.stringify(next));write("until",String(now+LEASE));
    });
    return result({...next,until:now+LEASE});
  }
  return result({error:"not_found"},404);
}
