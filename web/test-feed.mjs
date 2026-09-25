import assert from 'node:assert/strict';
import {createServer} from 'vite';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
const server=await createServer({server:{middlewareMode:true},appType:'custom'});
try{
 const {EventFeed}=await server.ssrLoadModule('/src/tape.jsx');
 const render=row=>renderToStaticMarkup(React.createElement(EventFeed,{rows:[row]}));
 const row={id:'evt-1',kind:'announcement',source:'binance',title:'上线代币（ABC）<img src=x onerror=alert(1)>',body:'平台将于明日上线 ABC/USDT。<script>alert(1)</script>',detected:1700000000,status:'unknown',url:'https://evil.example/phishing'};
 const html=render(row);
 assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<script>'));assert.ok(!html.includes('https://evil.example'));assert.ok(html.includes('送达未知'));assert.ok(!html.includes('#01'));assert.ok(html.includes('ABC'));assert.ok(!html.includes('<details>'));
 const official=render({...row,url:'https://www.okx.com/help/test'});assert.ok(official.includes('https://www.okx.com/help/test'));assert.ok(official.includes('noopener noreferrer'));
 const market=render({...row,kind:'market',symbol:'BTCUSDT',title:'BTC +2.50%',body:'SHOULD_NOT_APPEAR',notification_status:'sent',notification_sent:1700000030,sent:null});assert.ok(market.includes('上涨 2.50%'));assert.ok(!market.includes('SHOULD_NOT_APPEAR'));assert.ok(!market.includes('event-meta'));assert.ok(market.includes(new Date(1700000030000).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false})));
 const bi=render({...row,url:'https://www.bitget.com/en/a',i18n:{en:{title:'Bitget to delist ABC',summary:'Trading ends soon.',points:'2026-10-01 08:00 UTC',url:'https://www.bitget.com/en/a'},zh:{title:'Bitget 将下架 ABC',summary:'交易即将结束。',points:'2026-10-01 08:00 UTC',url:'https://www.bitget.com/zh-CN/a'}}});
 assert.ok(bi.includes('Bitget 将下架 ABC')&&bi.includes('Bitget to delist ABC')&&bi.includes('交易即将结束')&&bi.includes('key-points')&&bi.includes('要点')&&bi.includes('https://www.bitget.com/zh-CN/a'));
 const en=renderToStaticMarkup(React.createElement(EventFeed,{rows:[{...row,i18n:{zh:{title:'仅中文',summary:'',points:'',url:''}}}],lang:'en'}));assert.ok(en.includes('仅中文')&&en.includes('Original')&&en.includes('Unknown'));
 const flow=render({...row,kind:'flow',source:'binance',category:'inflow',symbol:'USDT',url:'https://etherscan.io/tx/0xaa',i18n:{zh:{title:'币安大额流入 12,000,000 USDT（$12.00M）',summary:'链：Ethereum\n来源：0x1111…1111\n去向：币安热钱包（0x28c6…1d60）',points:'',url:'https://etherscan.io/tx/0xaa'},en:{title:'Binance inflow 12,000,000 USDT ($12.00M)',summary:'Chain: Ethereum',points:'',url:'https://etherscan.io/tx/0xaa'}}});
 assert.ok(flow.includes('币安大额流入')&&flow.includes('flow-in')&&flow.includes('流入')&&flow.includes('>USDT<')&&flow.includes('https://etherscan.io/tx/0xaa')&&flow.includes('去向：币安热钱包'));
 console.log('Compact announcement, coin labels, market-only title and minute time checks passed');
}finally{await server.close();}
