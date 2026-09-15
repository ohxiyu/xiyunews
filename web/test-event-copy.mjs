import assert from 'node:assert/strict';
import {mainBody,marketLine} from './src/event-copy.js';
assert.equal(mainBody('新增ABC，开盘时间17:00。\n这是一般性公告，此处提及的产品和服务可能不适用于您所在的地区。\n其他说明'),'新增ABC，开盘时间17:00。');
assert.equal(mainBody('此为一般性公告，代币可用性可能因地区而异。\n上线ABC。\n保证金要求：10%。\n欧易团队'),'上线ABC。\n保证金要求：10%。');
assert.equal(mainBody('暂停提现，恢复时间待定。'),'暂停提现，恢复时间待定。');
assert.equal(marketLine({symbol:'LSKUSDT',signal:{change:-6.04}}),'LSK 币约 2–3 分钟内下跌 6.04%');
assert.equal(marketLine({symbol:'BTCUSDT',title:'BTCUSDT +2.51% · spot'}),'BTC 币约 2–3 分钟内上涨 2.51%');
console.log('Event copy checks passed');

assert.equal(mainBody('这是一般性币安交易所公告，地区说明。\n亲爱的用户：\n交易时段改为24/5。\n英文原版公告可能存在差异。'),'交易时段改为24/5。');
