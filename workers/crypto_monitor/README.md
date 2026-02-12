# Headless Crypto Market Monitor 🚀

> **"No UI, Pure Signal"** - A 7x24 Python daemon for detecting smart money flow.

本项目是一个基于 Python 的**无头 (Headless) 加密货币市场监控系统**。它抛弃了繁杂的前端交互，作为一个纯粹的后台守护进程，全天候通过 WebSocket 扫描币安 (Binance) 全市场数据，并通过 Telegram 推送高价值的交易信号。

---

## 📚 核心文档 (Documentation)

请参考以下文档以了解更多细节：

*   **📄 [项目白皮书 (Whitepaper)](WHITEPAPER.md)**: 详细的技术架构、产品定位与未来路线图。
*   **🐦 [一分钟介绍 (Social Summary)](WHITEPAPER_SOCIAL.txt)**: 适合社交媒体分享的精简纯文本介绍。
*   **📊 [推送指标指南 (Metrics Guide)](TELEGRAM_METRICS.md)**: 详细解释 Telegram 报警消息中各个字段 (24h Vol, Tds, Pos, etc.) 的含义。

---

## 🔥 核心策略 (Core Strategies)

系统内置三大策略，只抓真机会，拒绝垃圾噪音：

1.  **🌊 动能暴涨 (Momentum Pump)**: 5分钟内涨幅超过 **10%** 且成交量达标。
2.  **🐋 巨鲸挂单 (Whale Wall)**: 盘口前20档出现 **>50万U** 且 **>10倍失衡** 的巨额挂单。
3.  **⚠️ 期现价差 (Spread Arbitrage)**: 捕捉期货与现货价格脱钩 (**>5%**) 的套利机会。

---

## ⚡ 快速开始 (Quick Start)

### 1. 环境准备
确保已安装 Python 3.9+ 及 Redis。

```bash
# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 (Configuration)
创建或修改 `.env` 文件，填入你的 Telegram Bot 信息：

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ADMIN_ID=your_admin_id
```

### 3. 启动系统 (Start)
使用一键启动脚本 (基于 Systemd)：

```bash
./start.sh
```

### 4. 查看日志 (Logs)
```bash
./log.sh
```

---

## 🛠️ 架构概览
*   **数据源**: Binance WebSocket (Spot + Futures)
*   **后端**: Python (Asyncio) + Redis
*   **通知**: Telegram Bot API
*   **运维**: Systemd + Healthchecks.io

---
(C) 2026 Headless Crypto Monitor Team
