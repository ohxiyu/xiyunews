import {env} from "cloudflare:test";
import {afterEach,beforeAll,expect,it,vi} from "vitest";
import {identity,publicationRoute} from "../src/publication-state";
import unified from "../src/unified";

const owner="123:1:"+"a".repeat(32);
const other="124:1:"+"b".repeat(32);
function gate(){return env.RECOVERY_GATE.get(env.RECOVERY_GATE.idFromName(crypto.randomUUID()));}
async function page(n=0){
  const raw=new Uint8Array(512).fill(42);
  return {n,hash:Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",raw)),n=>n.toString(16).padStart(2,"0")).join(""),data:btoa(String.fromCharCode(...Array.from(raw)))};
}
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});

it("requires initial migration, fences competing writers and atomically commits complete pages",async()=>{
  const g=gate();
  expect((await g.publicationState("acquire",{owner},false)).status).toBe(503);
  expect((await g.publicationState("acquire",{owner},true)).status).toBe(200);
  expect((await g.publicationState("acquire",{owner:other},true)).status).toBe(423);
  expect((await g.publicationState("commit",{owner,version:0,size:512,hashes:["a".repeat(64)]},true)).status).toBe(409);
  const p=await page();
  expect((await g.publicationState("upload",{owner,version:0,pages:[p]},true)).status).toBe(200);
  const commit=await g.publicationState("commit",{owner,version:0,size:512,hashes:[p.hash]},true);
  expect(await commit.json()).toMatchObject({version:1,ready:true,size:512});
  expect((await g.publicationState("upload",{owner,version:0,pages:[p]},true)).status).toBe(409);
  expect(await (await g.publicationState("download",{owner,version:1,start:0},false)).json()).toEqual({pages:[p]});
  expect((await g.publicationState("release",{owner},false)).status).toBe(200);
  expect((await g.publicationState("upload",{owner,version:1,pages:[p]},true)).status).toBe(409);
  expect(await (await g.publicationState("acquire",{owner:other},false)).json()).toMatchObject({version:1,ready:true});
});

it("rejects checksum corruption and clears abandoned uploads on release",async()=>{
  const g=gate(),p=await page();
  await g.publicationState("acquire",{owner},true);
  expect((await g.publicationState("upload",{owner,version:0,pages:[{...p,hash:"0".repeat(64)}]},true)).status).toBe(400);
  await g.publicationState("upload",{owner,version:0,pages:[p]},true);
  await g.publicationState("release",{owner},true);
  await g.publicationState("acquire",{owner:other},true);
  expect((await g.publicationState("commit",{owner:other,version:0,size:512,hashes:[p.hash]},true)).status).toBe(409);
});

it("fences expired owners before handing state to another job",async()=>{
  const g=gate(),p=await page(),now=Date.now();
  await g.publicationState("acquire",{owner},true);
  vi.spyOn(Date,"now").mockReturnValue(now+41*60_000);
  expect((await g.publicationState("upload",{owner,version:0,pages:[p]},true)).status).toBe(409);
  expect((await g.publicationState("acquire",{owner:other},true)).status).toBe(200);
  expect((await g.publicationState("release",{owner},true)).status).toBe(409);
});

let pair:CryptoKeyPair,jwk:JsonWebKey;
beforeAll(async()=>{
  pair=await crypto.subtle.generateKey({name:"RSASSA-PKCS1-v1_5",modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:"SHA-256"},true,["sign","verify"]) as CryptoKeyPair;
  jwk=await crypto.subtle.exportKey("jwk",pair.publicKey) as JsonWebKey;
});
function enc(value:unknown){return btoa(JSON.stringify(value)).replaceAll("+","-").replaceAll("/","_").replaceAll("=","");}
async function token(extra:Record<string,unknown>={}){
  const raw=enc({alg:"RS256",kid:"state-test"})+"."+enc({
    iss:"https://token.actions.githubusercontent.com",aud:"https://xiyu.news/internal/publication-state",
    repository:"ohxiyu/xiyunews",repository_id:"1341754381",ref:"refs/heads/main",
    sub:"repo:ohxiyu/xiyunews:ref:refs/heads/main",workflow_ref:"ohxiyu/xiyunews/.github/workflows/feed-collection.yml@refs/heads/main",
    event_name:"workflow_dispatch",run_id:"123",run_attempt:"1",exp:Math.floor(Date.now()/1000)+120,nbf:Math.floor(Date.now()/1000)-1,...extra});
  const sig=await crypto.subtle.sign("RSASSA-PKCS1-v1_5",pair.privateKey,new TextEncoder().encode(raw));
  return raw+"."+btoa(String.fromCharCode(...Array.from(new Uint8Array(sig)))).replaceAll("+","-").replaceAll("/","_").replaceAll("=","");
}
function mockKeys(){vi.stubGlobal("fetch",vi.fn(async()=>Response.json({keys:[{...jwk,kid:"state-test"}]})));}

it("uses signed short-lived GitHub main identity, with repository ID and workflow allowlist",async()=>{
  mockKeys();
  expect(await identity(await token())).toMatchObject({run_id:"123",migration:false});
  for(const claims of [{repository_id:"1"},{ref:"refs/pull/1/merge"},{event_name:"pull_request_target"},
    {aud:"wrong"},{exp:0},{sub:"repo:ohxiyu/fork:ref:refs/heads/main"},
    {workflow_ref:"ohxiyu/xiyunews/.github/workflows/ci.yml@refs/heads/main"}]){
    await expect(identity(await token(claims))).rejects.toThrow("identity rejected");
  }
});

it("never exposes state through anonymous or static-asset fallback",async()=>{
  const assets={fetch:vi.fn(async()=>new Response("public"))};
  const e={...env,ASSETS:assets} as unknown as Parameters<typeof unified.fetch>[1];
  const ctx={waitUntil:vi.fn()} as unknown as ExecutionContext;
  expect((await unified.fetch(new Request("https://xiyu.news/internal/publication-state/download"),e,ctx)).status).toBe(405);
  expect((await unified.fetch(new Request("https://xiyu.news/internal/publication-state/download",{method:"POST",body:"{}"}),e,ctx)).status).toBe(401);
  expect(assets.fetch).not.toHaveBeenCalled();
  mockKeys();
  const r=await publicationRoute(new Request("https://xiyu.news/internal/publication-state/acquire",{method:"POST",
    headers:{Authorization:"Bearer "+await token()},body:JSON.stringify({owner:other})}),env);
  expect(r.status).toBe(403);expect(r.headers.get("Cache-Control")).toBe("no-store");
});
