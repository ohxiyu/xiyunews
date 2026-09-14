import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
let requests=0, next=1;
const timers=new Map(), elements=new Map(), listeners=new Map();
const context={
  window:{FOMOBTC_CONFIG:{apiOrigin:'https://api.example.com'}},
  location:{hostname:'example.com'}, URLSearchParams, URL,
  document:{querySelectorAll:()=>[],getElementById(id){
    if(!elements.has(id))elements.set(id,{value:'',textContent:''});
    return elements.get(id);
  }},
  fetch(){requests++;return new Promise(()=>{});},
  AbortSignal:{timeout:()=>undefined},
  EventSource:class {addEventListener(name,fn){listeners.set(name,fn);} close(){}},
  setTimeout(fn){const id=next++;timers.set(id,fn);return id;},
  clearTimeout(id){timers.delete(id);}, setInterval(){},
};
runInNewContext(readFileSync(new URL('./public/app.js',import.meta.url),'utf8'),context);
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
