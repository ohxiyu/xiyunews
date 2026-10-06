import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(new URL('../docs/assets/js/story-card.js', import.meta.url), 'utf8');
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const card = await import(moduleUrl);

test('image clipboard writes only the generated PNG blob', async () => {
  const blob = {type: 'image/png'};
  const writes = [];
  class MockClipboardItem {
    constructor(data) {
      this.data = data;
    }
  }

  await card.copyImageToClipboard(
    blob,
    {write: async (items) => writes.push(items)},
    MockClipboardItem,
  );

  assert.equal(writes.length, 1);
  assert.equal(writes[0].length, 1);
  assert.deepEqual(Object.keys(writes[0][0].data), ['image/png']);
  assert.equal(writes[0][0].data['image/png'], blob);
});

test('Chinese closing punctuation is not orphaned on a new line', () => {
  const context = {
    measureText: (value) => ({width: Array.from(value).length * 10}),
  };

  assert.deepEqual(card.wrapText(context, '甲乙。', 20, 'zh'), ['甲乙。']);
});

test('card titles balance the final line without adding a line', () => {
  const context = {
    measureText: (value) => ({width: Array.from(value).length * 10}),
  };

  assert.deepEqual(
    card.wrapBalancedText(context, 'ABCDEFGHIJ', 60, 'en'),
    ['ABCDE', 'FGHIJ'],
  );
});

test('card palette follows the current site tokens with a safe light fallback', () => {
  assert.equal(card.cardPalette().background, '#f5f6f8');
  assert.equal(card.cardPalette().surface, '#ffffff');
  const palette = card.cardPalette({getPropertyValue: name => ({
    '--bg': ' #17181b ', '--surface': '#202226', '--surface-soft': '#26292f',
    '--text': '#edf0f5', '--text-soft': '#c4cbd6', '--accent': '#a0baf1',
  }[name] || '')});
  assert.equal(palette.background, '#17181b');
  assert.equal(palette.detail, '#26292f');
  assert.equal(palette.text, '#edf0f5');
  assert.equal(palette.accent, '#a0baf1');
  assert.equal(palette.border, '#e6e9ee');
});

test('rendered card retains every paragraph, analysis, reference and tag in bounded panels', async () => {
  const texts = [], panels = [];
  const context = new Proxy({
    font: '400 15px sans-serif',
    measureText(value) { return {width: Array.from(value).length * 7}; },
    fillText(text, x, y) { texts.push({text, x, y, font: this.font}); },
    roundRect(x, y, width, height, radius) { panels.push({x, y, width, height, radius}); },
  }, {get(target, key) { return key in target ? target[key] : () => {}; }});
  const previous = globalThis.document;
  globalThis.document = {
    querySelectorAll: () => [],
    createElement: () => ({getContext: () => context, setAttribute() {}}),
  };
  try {
    const story = {language:'zh', rank:'#01', date:'2026-10-06', title:'测试标题',
      category:'政策', categoryKey:'policy', priority:'本期重点', score:'8.5', scoreTier:'good',
      summaryParagraphs:['第一段正文', '第二段正文'],
      sourceParts:{type:'rss', outlet:'a'.repeat(160), published:'10月6日 07:00', provenance:'单一来源'},
      sections:[{title:'市场影响',text:'完整影响内容'},{title:'背景',text:'完整背景内容'}],
      references:['完整参考标题'], tags:['#完整标签']};
    const canvas = await card.renderStoryCard(story);
    assert.equal(canvas.width, 1320);
    for (const text of ['第一段正文','第二段正文','完整影响内容','完整背景内容','完整参考标题','#完整标签'])
      assert.ok(texts.some(entry => entry.text.includes(text)), text);
    assert.equal(texts.filter(entry => entry.text === 'xiyu.news').length, 1);
    assert.ok(texts.some(entry => entry.text === ' · '));
    assert.equal(panels.length, 2);
    for (const panel of panels) {
      assert.ok(panel.width > 0 && panel.height > 0);
      assert.ok(panel.y + panel.height <= canvas.height / 3);
    }
    for (const entry of texts) assert.ok(entry.y < canvas.height / 3);
    const sourceRows = texts.filter(entry => /^a+$/.test(entry.text));
    assert.ok(sourceRows.length > 1);
    assert.equal(sourceRows.map(entry => entry.text).join(''), 'a'.repeat(160));
    for (const entry of sourceRows) assert.ok(entry.x + context.measureText(entry.text).width <= 414);
    const paragraphs = texts.filter(entry => /段正文/.test(entry.text));
    assert.ok(paragraphs[1].y > paragraphs[0].y + 27.75);
    assert.match(paragraphs[0].font, /15px/);
    assert.match(texts.find(entry => entry.text === '完整影响内容').font, /12.8px/);
    assert.ok(!texts.some(entry => entry.text.includes('127.0.0.1') || entry.text === '分享'));
  } finally { globalThis.document = previous; }
});
