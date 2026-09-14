# 数据契约

## 来源与计算
实现来源：[REST 客户端](../src/binance_rest_client.py)、[分组](../src/volume_grouper.py)、[计算器](../src/change3m_calculator.py)、[引擎](../src/alert_engine.py)。
Binance USDT 现货和 USD-M 合约行情；24h ticker 的 quoteVolume 是报价资产成交量（USDT），并非经过汇率换算的美元价值。展示中的 $ 是近似标签。
每 600 秒更新成交额分组，每 60 秒扫描，取 4 根 1m K 线。
公式 `(最后一根 close / 倒数第四根 close - 1) * 100`；没有排除未收盘的最后一根，不能称为“三根已收盘 K 线涨幅”。绝对变化达到阈值触发，阈值来自 [配置](../config/thresholds.yaml)。

| 市场 | 最小成交额 | MID 起点 | HIGH 起点 |
| --- | ---: | ---: | ---: |
| spot | 500,000 | 10,000,000 | 100,000,000 |
| futures | 500,000 | 10,000,000 | 200,000,000 |

## 字段
日志事件包含 ts（生成时间，Unix 秒）、market（spot/futures）、symbol、quoteVolume24h、volumeGroup（HIGH/MID/LOW）、thresholdPct、change3mPct（两位小数）、direction（UP/DOWN/FLAT）、triggered（布尔）。ts 不是 K 线时间。Redis 事件另含 deliverySucceeded，保存 3600 秒。

## 缺失与可靠性
K 线不足四条、价格解析失败或历史价格非正时跳过；畸形 ticker 跳过。不得把数据请求失败解释成零涨幅或零成交额。
当前实现尚未完整检查非有限浮点数与 K 线时间连续性；连续相同舍入涨幅的抑制只是启发式，不能证明数据新鲜。修复列入 [待办](backlog.md)。Telegram 格式化器对缺失数值有零默认值，这是现存局限，不是数据完整性的保证。
冷却键为 market + symbol + 3m，默认 7200 秒。Telegram 开启时确认发送成功后记录冷却；明确关闭时日志处理成功也记录冷却。Redis 不可用时继续运行，但重启持久化不保证。日志有事件、进程 online、API 返回成功、用户实际收件应分别举证。
