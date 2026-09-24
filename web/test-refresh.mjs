import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
let requests=0, next=1;
const timers=new Map(), elements=new Map(), listeners=new Map();
const button=data=>({dataset:data,active:false,classList:{toggle(name,on){if(name==='active')this.owner.active=on;}},setAttribute(){}});
const buttons=['','market','announcement'].map(kind=>button({kind}));
const chips=['','binance','okx','upbit'].map(source=>button({source}));
for(const b of [...buttons,...chips])b.classList.owner=b;
const urls=[];
const context={
  window:{FOMOBTC_CONFIG:{apiOrigin:'https://api.example.com'}},
  location:{hostname:'example.com'}, URLSearchParams, URL,
  document:{querySelectorAll:selector=>selector==='[data-kind]'?buttons:selector==='[data-source]'?chips:[],getElementById(id){
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

const param=name=>new URL(urls.at(-1)).searchParams.get(name);
buttons[2].onclick();
assert.equal(elements.get('exchanges').hidden,false);
assert.equal(param('kind'),'announcement');assert.equal(param('source'),'');
chips[3].onclick();
assert.equal(param('kind'),'announcement');assert.equal(param('source'),'upbit');assert.ok(chips[3].active&&!chips[0].active);
buttons[1].onclick();
assert.equal(elements.get('exchanges').hidden,true);
assert.equal(param('kind'),'market');assert.equal(param('source'),'');assert.ok(chips[0].active&&!chips[3].active);
buttons[2].onclick();assert.equal(param('source'),'');
console.log('Category and exchange filter checks passed');
