import assert from 'node:assert/strict';
import {mainBody,marketLine} from './src/event-copy.js';
assert.equal(mainBody('新增ABC，开盘时间17:00。\n这是一般性公告，此处提及的产品和服务可能不适用于您所在的地区。\n其他说明'),'新增ABC，开盘时间17:00。');
assert.equal(mainBody('此为一般性公告，代币可用性可能因地区而异。\n上线ABC。\n保证金要求：10%。\n欧易团队'),'上线ABC。\n保证金要求：10%。');
assert.equal(mainBody('暂停提现，恢复时间待定。'),'暂停提现，恢复时间待定。');
assert.equal(marketLine({symbol:'LSKUSDT',signal:{change:-6.04}}),'LSK 币约 2–3 分钟内下跌 6.04%');
assert.equal(marketLine({symbol:'BTCUSDT',title:'BTCUSDT +2.51% · spot'}),'BTC 币约 2–3 分钟内上涨 2.51%');
console.log('Event copy checks passed');

assert.equal(mainBody('这是一般性币安交易所公告，地区说明。\n亲爱的用户：\n交易时段改为24/5。\n英文原版公告可能存在差异。'),'交易时段改为24/5。');

const {marketBody}=await import("./src/event-copy.js");
assert.match(marketBody({body:"Minute-bar reference (not rolling 180s). 24h quote volume: 12345678 USDT; group: MID"}),/12,345,678 USDT · 中成交额组/);
const {announcementBrief,announcementCoins}=await import('./src/event-copy.js');
assert.deepEqual(announcementCoins({title:'欧易关于上线 PONS/USDT (Pons Family) 现货交易的公告'}),['PONS']);
assert.deepEqual(announcementCoins({title:'支持Vana（VANA）升级'}),['VANA']);
assert.deepEqual(announcementCoins({title:'关于 API 与 ETF 更新 (UTC)',body:'API supports UTC'}),[]);
assert.deepEqual(announcementCoins({title:'MINIMAXUSD X-合约上线'}),['MINIMAX']);
assert.deepEqual(announcementCoins({title:'调整多个交易对',body:'交易对 BTC/USDT、ETH/USDT'}),['BTC','ETH']);
assert.equal(announcementBrief({body:'此为一般性公告。本文所述产品与服务可能无法在您的地区提供。亲爱的用户：\n币安将于9月18日移除ABC/USDT交易对。\n感谢您的支持。'}),'币安将于9月18日移除ABC/USDT交易对。');
assert.ok(announcementBrief({body:'平台将上线ABC。'.repeat(100)}).length<=180);

assert.deepEqual(announcementCoins({title:'欧易关于 AKE 永续合约正式上线的公告'}),['AKE']);

const trendTitle='ZEC 持续走强，24 小时上涨 9.10%，突破 24 小时新高';
assert.equal(marketLine({title:trendTitle,signal:{policy_version:2}}),trendTitle);
assert.equal(marketLine({title:'BTC 1 分钟内下跌 1.60%',signal:{policy_version:2}}),'BTC 1 分钟内下跌 1.60%');

const burst={symbol:'ONEUSDT',title:'ONE 1 分钟内下跌 2.77%',signal:{policy_version:2,components:[{type:'burst',direction:-1,change:-2.77,window_seconds:60}]}};
assert.equal(marketLine(burst,'en'),'ONE down 2.77% in 1 min');
assert.equal(marketLine(burst),'ONE 1 分钟内下跌 2.77%');
const trend={symbol:'ZECUSDT',title:trendTitle,signal:{policy_version:2,components:[{type:'trend',direction:1,change:9.1,window_seconds:86400,breakout:true}]}};
assert.equal(marketLine(trend,'en'),'ZEC strengthening, up 9.10% over 24h, new 24h high');
const {localized}=await import('./src/event-copy.js');
const both={title:'x',url:'https://www.bitget.com/en/a',i18n:{en:{title:'Bitget to delist ABC',summary:'S',points:'P',url:'https://www.bitget.com/en/a'},zh:{title:'Bitget 将下架 ABC',summary:'摘',points:'点',url:'https://www.bitget.com/zh-CN/a'}}};
assert.deepEqual(localized(both,'zh'),{title:'Bitget 将下架 ABC',summary:'摘',points:'点',url:'https://www.bitget.com/zh-CN/a',original:false,alt:'Bitget to delist ABC'});
assert.equal(localized(both,'en').title,'Bitget to delist ABC');
const koOnly={title:'k',url:'u',i18n:{ko:{title:'만트라 출금 중지',summary:'',points:'',url:'u'}}};
assert.equal(localized(koOnly,'zh').original,true);assert.equal(localized(koOnly,'en').title,'만트라 출금 중지');
console.log('Bilingual selection and English market line checks passed');
assert.deepEqual(announcementCoins({title:'Bybit Odds launch with a 17,000 USDT total prize pool'}),[]);
console.log('Numeric amounts are not coin tags');
