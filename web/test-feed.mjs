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
 console.log('Compact announcement, coin labels, market-only title and minute time checks passed');
}finally{await server.close();}
