import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

// Execute the real controller against an offline DOM; no network or source calls.
class Node {
  constructor(tag, classes = '') {
    this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {};
    this.attributes = {}; this.listeners = {}; this.ownText = ''; this.hidden = false;
    this.className = classes;
    this.classList = {contains: value => this.className.split(' ').includes(value),
      toggle: value => {
        const present = this.classList.contains(value);
        this.className = present ? this.className.split(' ').filter(v => v !== value).join(' ') : this.className + ' ' + value;
        return !present;
      }};
  }
  get parentElement() { return this.parent; }
  get textContent() { return this.ownText + this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this.ownText = value; this.children = []; }
  appendChild(child) {
    if (child.parent) child.parent.children = child.parent.children.filter(node => node !== child);
    child.parent = this; this.children.push(child); return child;
  }
  insertBefore(child, reference) {
    if (child.parent) child.parent.children = child.parent.children.filter(node => node !== child);
    const index = this.children.indexOf(reference); assert.ok(index >= 0);
    child.parent = this; this.children.splice(index, 0, child); return child;
  }
  remove() {
    this.parent.children = this.parent.children.filter(child => child !== this); this.parent = null;
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  hasAttribute(key) { return key in this.attributes; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  matches(selector) {
    return selector.startsWith('.') ? this.classList.contains(selector.slice(1)) : this.tagName === selector.toUpperCase();
  }
  querySelectorAll(selector) {
    const descendants = this.children.flatMap(child => [child, ...child.querySelectorAll('*')]);
    if (selector === '*') return descendants;
    return descendants.filter(child => child.matches(selector));
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  insertAdjacentElement(position, other) {
    assert.equal(position, 'afterend');
    if(other.parent) other.parent.children = other.parent.children.filter(node => node !== other);
    const index = this.parent.children.indexOf(this); other.parent = this.parent;
    this.parent.children.splice(index + 1, 0, other);
  }
}
const source = await readFile(new URL('../docs/assets/js/bmtnews-ui.js', import.meta.url), 'utf8');
const controller = source.slice(source.indexOf('  function contextKind('), source.indexOf('  var CATEGORY_ORDER'));
const context = {document: {createElement: tag => new Node(tag)}, textOf: node => node ? node.textContent.trim() : ''};
vm.runInNewContext('var contextSequence = 0;\n' + controller + '\nthis.enhance = enhanceReadingContext;', context);

function fixture({event=false, background=true, discussion=true, impact=true, refs=true}={}) {
  const host=new Node('article',event?'event-feed-item':'digest-item');
  host.appendChild(new Node('h2')).textContent='新闻标题';
  if(event) {
    host.appendChild(new Node('p','event-focus-state')).textContent='当前已报道状态';
    host.appendChild(new Node('section','event-focus-developments')).appendChild(new Node('p')).textContent='三条完整进展';
    host.appendChild(new Node('p','event-next-watch')).textContent='下一关注点';
  } else host.appendChild(new Node('div','story-summary-body')).appendChild(new Node('p')).textContent='完整新闻事实';
  host.appendChild(new Node('p','source-line')).textContent='原始报道来源';
  const details=host.appendChild(new Node('details','story-more'));
  const content=details.appendChild(new Node('div','story-more-content'));
  for(const [enabled,title,text] of [[impact,'市场影响','完整影响内容'],[background,'背景','长背景'.repeat(100)],[discussion,'社区讨论','真实讨论内容']]) {
    if(!enabled) continue;
    const section=content.appendChild(new Node('section'));
    section.appendChild(new Node('h3')).textContent=title;
    section.appendChild(new Node('p')).textContent=text;
  }
  if(refs) {
    const section=content.appendChild(new Node('section'));
    section.appendChild(new Node('h3')).textContent='参考链接';
    section.appendChild(new Node('ul')).appendChild(new Node('li')).appendChild(new Node('a')).textContent='完整参考标题';
  }
  return {host,content,details};
}

test('legacy context keeps full evidence in a closed native disclosure after the report',()=>{
  const {host}=fixture();context.enhance(host,'zh');
  assert.deepEqual(host.children.map(n=>n.className||n.tagName),
    ['H2','reading-context reading-context-background is-enhanced','story-summary-body','source-line','reading-context reading-context-after is-enhanced']);
  assert.equal(host.querySelector('.reading-context-tabs'),null);
  const after=host.querySelector('.reading-context-after');
  assert.equal(after.tagName,'DETAILS');
  assert.equal(after.hasAttribute('open'),false);
  assert.equal(after.querySelector('summary').textContent,'影响分析 · 讨论焦点 · 参考资料');
  assert.deepEqual(after.querySelectorAll('h3').map(h=>h.textContent),['影响分析','讨论焦点','参考资料']);
  assert.ok(after.querySelectorAll('section').every(s=>!s.hidden));
  for(const text of ['长背景'.repeat(100),'完整新闻事实','完整影响内容','真实讨论内容','完整参考标题']) assert.ok(host.textContent.includes(text));
});
test('keyboard-operable background control owns a unique paragraph and preserves full text',()=>{
  const one=fixture(),two=fixture();context.enhance(one.host,'zh');context.enhance(two.host,'en');
  const block=one.host.querySelector('.reading-context-background'),p=block.querySelector('p'),button=block.querySelector('button');
  assert.equal(button.attributes['aria-controls'],p.id);assert.equal(button.attributes['aria-expanded'],'false');
  button.listeners.click();assert.equal(button.attributes['aria-expanded'],'true');
  assert.ok(block.querySelector('section').classList.contains('is-expanded'));
  assert.equal(p.textContent,'长背景'.repeat(100));
  assert.notEqual(p.id,two.host.querySelector('.reading-context-background').querySelector('p').id);
});
test('missing fields do not create empty panels or label impact as community discussion',()=>{
  const {host}=fixture({background:false,discussion:false});context.enhance(host,'en');
  assert.equal(host.querySelector('.reading-context-background'),null);
  assert.deepEqual(host.querySelectorAll('h3').map(h=>h.textContent),['Impact analysis','References']);
  assert.equal(host.querySelector('summary').textContent,'Impact analysis · References');
});
test('event background precedes state while analysis and evidence follow full developments',()=>{
  const {host}=fixture({event:true});context.enhance(host,'zh');
  assert.deepEqual(host.children.map(n=>n.className||n.tagName),['H2','reading-context reading-context-background is-enhanced',
    'event-focus-state','event-focus-developments','event-next-watch','reading-context reading-context-after is-enhanced','source-line']);
  context.enhance(host,'zh');assert.equal(host.querySelectorAll('.reading-context').length,2);
});
test('already split new markup is normalized once without duplicate or dropped sections',()=>{
  const {host,content}=fixture();
  const background=content.children.find(s=>s.querySelector('h3').textContent==='背景');
  const split=new Node('details','story-more');split.appendChild(new Node('div','story-more-content')).appendChild(background);
  host.insertBefore(split,host.querySelector('.story-summary-body'));
  context.enhance(host,'zh');context.enhance(host,'zh');
  assert.equal(host.querySelectorAll('.reading-context').length,2);
  assert.equal(host.querySelectorAll('.story-more').length,0);
  assert.equal(host.querySelectorAll('h3').filter(h=>h.textContent==='背景').length,1);
  assert.ok(host.textContent.includes('完整影响内容'));
});
