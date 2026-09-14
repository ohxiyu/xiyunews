import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
let requests=0, next=1;
const timers=new Map(), elements=new Map(), listeners=new Map();
const buttons=['','market','announcement'].map(kind=>({dataset:{kind},classList:{toggle(){}}}));
const urls=[];
const context={
  window:{FOMOBTC_CONFIG:{apiOrigin:'https://api.example.com'}},
  location:{hostname:'example.com'}, URLSearchParams, URL,
  document:{querySelectorAll:selector=>selector==='[data-kind]'?buttons:[],getElementById(id){
    if(!elements.has(id))elements.set(id,{value:'',textContent:'',setAttribute(){}});
    return elements.get(id);
  }},
  fetch(url){urls.push(url);requests++;return new Promise(()=>{});},
  AbortSignal:{timeout:()=>undefined},
  EventSource:class {addEventListener(name,fn){listeners.set(name,fn);} close(){}},
  setTimeout(fn){const id=next++;timers.set(id,fn);return id;},
  clearTimeout(id){timers.delete(id);}, setInterval(){},
};
runInNewContext(readFileSync(new URL('./src/controller.js',import.meta.url),'utf8').replace(/^import .*;\n/,''),context);
assert.equal(requests,2); // initial feed + health
for(let i=0;i<10000;i++)listeners.get('refresh')();
assert.equal(timers.size,1);
assert.equal(requests,2); // no per-message health requests
const [id,callback]=timers.entries().next().value;
timers.delete(id);callback();
assert.equal(requests,3);
for(let i=0;i<10000;i++)listeners.get('refresh')();
assert.equal(timers.size,1); // next batch is allowed, no starvation
console.log('Burst refresh checks passed');

elements.get('follow').onclick();
const beforePause=requests;
for(const callback of timers.values())callback();
assert.equal(requests,beforePause);
listeners.get('refresh')();
assert.equal(requests,beforePause);
elements.get('follow').onclick();
assert.equal(requests,beforePause+1);
console.log('Pause and resume checks passed');

const source=elements.get('source');
source.options=['','binance_spot','binance_futures','binance','okx','hyperliquid'].map(value=>({value}));
source.value='binance_spot';buttons[2].onclick();
assert.equal(source.value,'');
assert.equal(new URL(urls.at(-1)).searchParams.get('kind'),'announcement');
assert.equal(new URL(urls.at(-1)).searchParams.get('source'),'');
assert.equal(source.options[1].disabled,true);
source.value='okx';buttons[1].onclick();assert.equal(source.value,'');
assert.equal(source.options[4].disabled,true);
buttons[0].onclick();assert.ok(source.options.every(o=>!o.disabled));
console.log('Cross-category source filter checks passed');
