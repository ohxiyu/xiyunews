import {env} from 'cloudflare:test';
import {expect,it} from 'vitest';
import {legacyRoute} from '../src/legacy';
const request=(path:string,method='GET')=>new Request('https://xiyu.news'+path,{method});
it('retires every live write without reading input or invoking storage',async()=>{
  const e={RECOVERY_GATE:{getByName:()=>{throw Error('must not access storage')}}} as unknown as Env;
  expect((await legacyRoute(request('/api/live.json','POST'),e))!.status).toBe(410);
  expect((await legacyRoute(request('/api/live.json'),e))!.headers.get('location')).toBe('https://xiyu.news/api/latest.json');
});
it('keeps old story bookmarks useful without retaining a live publishing API',async()=>{
  const id='a'.repeat(32);
  expect((await legacyRoute(request('/story/'+id+'/'),env))!.headers.get('location')).toBe('https://xiyu.news/history/');
  const fake={RECOVERY_GATE:{getByName:()=>({legacyStory:async()=>JSON.stringify({url:'https://example.com/original'})})}} as unknown as Env;
  expect((await legacyRoute(request('/story/'+id+'/'),fake))!.headers.get('location')).toBe('https://example.com/original');
  const unsafe={RECOVERY_GATE:{getByName:()=>({legacyStory:async()=>JSON.stringify({url:'javascript:alert(1)'})})}} as unknown as Env;
  expect((await legacyRoute(request('/story/'+id+'/'),unsafe))!.headers.get('location')).toBe('https://xiyu.news/history/');
});
