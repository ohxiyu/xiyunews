import {editionContextFor, fetchWorkflowRuns} from './lib';

export interface AlertEnv extends Env {
  DAILY_TELEGRAM_BOT_TOKEN?: string;
  TELEGRAM_ALERT_CHAT_ID?: string;
}

export async function sendPrivateAlert(env: AlertEnv, key: string, text: string): Promise<string> {
  const token=env.DAILY_TELEGRAM_BOT_TOKEN, chat=env.TELEGRAM_ALERT_CHAT_ID;
  if (!token || !chat || !/^[1-9][0-9]*$/.test(chat)) return 'not_configured';
  const gate=env.RECOVERY_GATE.getByName('daily-private-alerts');
  try {
    const result=await fetch(`https://api.telegram.org/bot${token}/getChat`, {
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:chat}),
      redirect:'manual',signal:AbortSignal.timeout(10_000),
    });
    const data=await result.json() as {ok?:boolean;result?:{id:number;type:string}};
    if (!result.ok || data.ok!==true || data.result?.type!=='private' || String(data.result.id)!==chat) return 'destination_unverified';
  } catch {return 'destination_unverified';}
  // Commit unknown before HTTP; an ambiguous send is never attempted again.
  if (!await gate.alertClaim(key)) return 'already_attempted';
  let status='unknown';
  try {
    const response=await fetch(`https://api.telegram.org/bot${token}/sendMessage`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({chat_id:chat,text,link_preview_options:{is_disabled:true}}),
      redirect:'manual',signal:AbortSignal.timeout(10_000),
    });
    const data=await response.json() as {ok?:boolean;result?:{message_id?:number}};
    if (response.ok && data.ok===true && data.result?.message_id) status='sent';
    else if (response.status>=400 && response.status<500 && data.ok===false) status='failed';
  } catch { /* preserve unknown without logging credential-bearing URLs */ }
  await gate.alertStatus(key,status);
  return status;
}

export async function checkPrivateAlerts(env: AlertEnv, now: number): Promise<void> {
  if (!env.DAILY_TELEGRAM_BOT_TOKEN || !env.TELEGRAM_ALERT_CHAT_ID) return;
  const gate=env.RECOVERY_GATE.getByName('daily-private-alerts');
  const runs=await fetchWorkflowRuns(env,'feed-collection.yml');
  const successful=runs.filter(r=>r.headBranch===env.GITHUB_REF && r.conclusion==='success');
  const newest=Math.max(0,...successful.map(r=>r.startedAt.getTime()));
  if (now-newest>30*60_000) {
    // Incident generation changes only on recovery, never on each failed tick.
    const generation=await gate.alertGeneration();
    await sendPrivateAlert(env,'collection:'+generation,'xiyu.news 后台采集已落后超过30分钟，请检查 runner 和采集任务。');
  } else {await gate.alertRecover();}
  const context=editionContextFor(now,env.EDITION_TIMEZONE,Number(env.EDITION_CUTOFF_HOUR));
  if (now-context.cutoffUtc.getTime()<45*60_000) return;
  const response=await fetch(env.PUBLIC_SITE_URL.replace(/\/+$/,'')+'/api/latest.json?alert='+now,{
    redirect:'manual',signal:AbortSignal.timeout(10_000),headers:{'Cache-Control':'no-cache'},
  });
  if (!response.ok) return; // transport uncertainty is not proof of a missing edition
  const data=await response.json() as {date?:string;items?:unknown[]};
  if (data.date!==context.date || !Array.isArray(data.items) || data.items.length===0) {
    await sendPrivateAlert(env,'overdue:'+context.date,`xiyu.news ${context.date} 在07:45后仍未检测到当期日报。`);
  }
}
