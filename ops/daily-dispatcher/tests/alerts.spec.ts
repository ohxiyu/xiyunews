import {env} from 'cloudflare:test';
import {afterEach,expect,it,vi} from 'vitest';
import {checkTopicAlerts,sendTopicAlert,type AlertEnv} from '../src/alerts';
const fixture=()=>({...env,DAILY_TELEGRAM_BOT_TOKEN:'fixture-bot',TELEGRAM_ALERT_CHAT_ID:'-100123',TELEGRAM_ALERT_THREAD_ID:'42'}) as AlertEnv;
afterEach(()=>{vi.unstubAllGlobals();});
it('rejects non-forum destinations before sending',async()=>{
  const call=vi.fn(async()=>Response.json({ok:true,result:{type:'channel',id:-100123}}));
  vi.stubGlobal('fetch',call);
  expect(await sendTopicAlert(fixture(),'channel-test','test')).toBe('destination_unverified');
  expect(call).toHaveBeenCalledTimes(1);
});
it('persists unknown before send and never retries it',async()=>{
  const calls:string[]=[];
  vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL)=>{
    const url=String(input);calls.push(url);
    if(url.endsWith('getChat'))return Response.json({ok:true,result:{type:'supergroup',is_forum:true,id:-100123}});
    throw new Error('timeout');
  }));
  expect(await sendTopicAlert(fixture(),'unknown-test','test')).toBe('unknown');
  expect(await sendTopicAlert(fixture(),'unknown-test','test')).toBe('already_attempted');
  expect(calls.filter(url=>url.endsWith('sendMessage'))).toHaveLength(1);
});
it('latches stale collection until recovery and sends overdue once per date',async()=>{
  let fresh=false;const sent:string[]=[];
  const now=Date.parse('2026-11-09T08:00:00+08:00');
  vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
    const url=String(input);
    if(url.includes('api.github.com'))return Response.json({workflow_runs:fresh?[{id:-100123,status:'completed',conclusion:'success',head_branch:'main',run_started_at:new Date(now).toISOString(),created_at:new Date(now).toISOString(),html_url:'https://github.com/test'}]:[]});
    if(url.endsWith('getChat'))return Response.json({ok:true,result:{type:'supergroup',is_forum:true,id:-100123}});
    if(url.endsWith('sendMessage')){sent.push(JSON.parse(String(init?.body)).text);return Response.json({ok:true,result:{message_id:1}});}
    return Response.json({date:'2026-11-08',items:[{}]});
  }));
  await checkTopicAlerts(fixture(),now);
  await checkTopicAlerts(fixture(),now+1000);
  expect(sent).toHaveLength(2);
  fresh=true;await checkTopicAlerts(fixture(),now+2000);
  fresh=false;await checkTopicAlerts(fixture(),now+3000);
  expect(sent).toHaveLength(3);
});
