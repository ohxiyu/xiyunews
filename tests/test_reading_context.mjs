import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

// Tiny offline DOM double; execute the production controller, not a copy.
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
  get textContent() { return this.ownText + this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this.ownText = value; this.children = []; }
  appendChild(child) {
    if (child.parent) child.parent.children = child.parent.children.filter(node => node !== child);
    child.parent = this; this.children.push(child); return child;
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  focus() { this.focused = true; }
  matches(selector) {
    return selector.startsWith('.') ? this.classList.contains(selector.slice(1)) : this.tagName === selector.toUpperCase();
  }
  querySelectorAll(selector) {
    const descendants = this.children.flatMap(child => [child, ...child.querySelectorAll('*')]);
    if (selector === '*') return descendants;
    if (selector === 'li a') return descendants.filter(child => child.tagName === 'A' && child.parent.tagName === 'LI');
    return descendants.filter(child => child.matches(selector));
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  replaceWith(other) {
    const index = this.parent.children.indexOf(this); other.parent = this.parent;
    this.parent.children[index] = other;
  }
  insertAdjacentElement(position, other) {
    assert.equal(position, 'afterend');
    other.parent.children = other.parent.children.filter(node => node !== other);
    const index = this.parent.children.indexOf(this); other.parent = this.parent;
    this.parent.children.splice(index + 1, 0, other);
  }
}

const source = await readFile(new URL('../docs/assets/js/bmtnews-ui.js', import.meta.url), 'utf8');
const controller = source.slice(source.indexOf('  function contextKind('), source.indexOf('  var CATEGORY_ORDER'));
const context = {document: {createElement: tag => new Node(tag)}, textOf: node => node ? node.textContent.trim() : ''};
vm.runInNewContext('var contextSequence = 0;\n' + controller + '\nthis.enhance = enhanceReadingContext;', context);

function fixture({event = false, background = true, discussion = true, impact = true, refs = true} = {}) {
  const host = new Node('article', event ? 'event-feed-item' : 'digest-item');
  host.appendChild(new Node('h2')); host.appendChild(new Node('p'));
  const details = host.appendChild(new Node('details', 'story-more'));
  const content = details.appendChild(new Node('div', 'story-more-content'));
  for (const [enabled, title, text] of [[impact, '市场影响', '完整影响内容'], [background, '背景', '长背景'.repeat(100)], [discussion, '社区讨论', '真实讨论内容']]) {
    if (!enabled) continue;
    const section = content.appendChild(new Node('section'));
    section.appendChild(new Node('h3')).textContent = title;
    section.appendChild(new Node('p')).textContent = text;
  }
  if (refs) {
    const section = content.appendChild(new Node('section'));
    section.appendChild(new Node('h3')).textContent = '参考链接';
    section.appendChild(new Node('ul')).appendChild(new Node('li')).appendChild(new Node('a')).textContent = '完整参考标题';
  }
  return {host, content};
}

test('context moves above body, defaults to background, preserves all export text', () => {
  const {host, content} = fixture(); context.enhance(host, 'zh');
  assert.equal(host.children[1].className, 'reading-context is-enhanced');
  const tabs = host.querySelector('.reading-context-tabs').children;
  assert.deepEqual(tabs.map(tab => tab.textContent), ['背景', '讨论与影响', '参考资料 1']);
  assert.equal(tabs[0].attributes['aria-selected'], 'true');
  assert.equal(content.attributes.role, 'tabpanel');
  assert.equal(content.children.find(section => section.dataset.contextKind === 'background').hidden, false);
  assert.ok(content.textContent.includes('完整影响内容') && content.textContent.includes('完整参考标题'));
  assert.equal(content.querySelector('p').textContent, '完整影响内容');
  tabs[2].listeners.click();
  assert.equal(content.children.find(section => section.dataset.contextKind === 'references').hidden, false);
  assert.equal(tabs[2].attributes['aria-selected'], 'true');
});

test('keyboard switches tabs and full background expands without losing text', () => {
  const {host, content} = fixture(); context.enhance(host, 'zh');
  const tabs = host.querySelector('.reading-context-tabs').children;
  let prevented = false;
  tabs[0].listeners.keydown({key: 'ArrowRight', preventDefault() { prevented = true; }});
  assert.ok(prevented && tabs[1].focused);
  assert.equal(tabs[1].tabIndex, 0); assert.equal(tabs[0].tabIndex, -1);
  const background = content.children.find(section => section.dataset.contextKind === 'background');
  const expand = background.querySelector('button'); expand.listeners.click();
  assert.equal(expand.attributes['aria-expanded'], 'true');
  assert.ok(background.classList.contains('is-expanded'));
  assert.equal(background.querySelector('p').textContent, '长背景'.repeat(100));
});

test('missing background and discussion do not produce empty or mislabeled tabs', () => {
  const {host} = fixture({background:false, discussion:false}); context.enhance(host, 'en');
  assert.deepEqual(host.querySelector('.reading-context-tabs').children.map(tab => tab.textContent), ['Impact analysis', 'References 1']);
});

test('event context retains its place after current state and setup is idempotent', () => {
  const {host} = fixture({event:true}); context.enhance(host, 'zh');
  assert.equal(host.children[1].tagName, 'P');
  assert.equal(host.children[2].className, 'reading-context is-enhanced');
  context.enhance(host, 'zh');
  assert.equal(host.querySelectorAll('.reading-context').length, 1);
});

test('separate cards get unique accessible tab and panel IDs', () => {
  const first = fixture(), second = fixture(); context.enhance(first.host, 'zh'); context.enhance(second.host, 'zh');
  assert.notEqual(first.content.id, second.content.id);
  for (const card of [first, second]) {
    const tab = card.host.querySelector('.reading-context-tabs').children[0];
    assert.equal(tab.attributes['aria-controls'], card.content.id);
    assert.equal(card.content.attributes['aria-labelledby'], tab.id);
  }
});
