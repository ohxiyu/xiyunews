# 🔥 QwePolymarket (V73)

**Multi-Platform Trending Top20 - 自动化预测市场情报机器人**

QwePolymarket 是一个全自动化的多平台预测市场热榜监控系统，每日推送 Polymarket 和 Opinion 的 Top20 热门市场，提供基于赔率的专业中文分析。

---

## 📋 目录

- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [运行方式](#运行方式)
- [版本演进](#版本演进)

---

## 🚀 核心功能

### 1. 📊 Multi-Platform Trending Top20 日报

**支持平台**
- **Polymarket**: 最大的去中心化预测市场
- **Opinion**: 新兴预测市场平台

**数据源**
- Polymarket: Gamma API (`/markets` endpoint), 排序: `volume24hr`
- Opinion: Opinion API, 排序: `volume_24h`
- 限制: 每平台 Top 20 市场
- 去重: 智能去重（同一事件多个市场只保留流动性最好的）

**推送时间**
- **Polymarket**: 每日 08:00 北京时间 (**UTC 00:00**)
- **Opinion**: 每日 20:00 北京时间 (**UTC 12:00**)

**内容格式**
```
🔥 **Polymarket 热榜 Top20** 🔥
📍 平台：Polymarket
⏰ UTC 2026-01-28 00:00
实时赔率 · 专业解读

**#1** 🗳️ **[特朗普会在2月1日就任总统吗？]**
📊 赔率：Yes 98% / No 2%
💰 24h交易量：$1.5M
💡 98%的极端赔率表明市场已形成压倒性共识，认为事件几乎必然发生，需警惕极小概率的黑天鹅风险。
🔗 https://polymarket.com/event/xxx

[... 19条类似内容 ...]
```

### 2. 🧠 DeepSeek AI 专业分析

**引擎**: DeepSeek Chat API (`deepseek-chat`)

**分析维度**
- 赔率解读：从概率数值解读市场情绪和共识
- 极端赔率 (>95% 或 <5%): 强调共识，警示黑天鹅
- 分歧赔率 (40-60%): 分析多空分歧，指出关键变量
- 错价信号：识别市场定价偏差和套利机会

**处理流程**
- 批量处理：每批 5 个市场并行调用 AI
- 超时保护：45 秒超时，2 次重试
- 降级处理：AI 失败时使用基础格式（保证推送不中断）

### 3. ⚡️ 实时监控 (可选)

**波动率检查** (每 2 分钟)
- 监控特定市场的赔率变化
- 触发阈值：5% 变化
- 推送到 Telegram admin

**心跳机制** (每小时)
- 发送系统状态到 Telegram admin
- 确认服务正常运行

### 4. 📱 Telegram 通知

**推送目标**
- 主频道：日报推送
- Admin：心跳、警报、测试消息

**消息格式**
- Markdown 格式
- 支持粗体、链接、emoji
- 自动处理特殊字符转义

### 5. 🌐 Web API (HTTP 接口)

**API 版本**: v1

**数据持久化**
- 每次生成日报后自动保存到 SQLite
- 支持 latest（最新） + history（7天历史）

**端点列表**

```bash
# 获取最新报告
GET /v1/reports/latest?platform=polymarket|opinion

# 获取历史报告（最近N天）
GET /v1/reports/history?platform=polymarket|opinion&days=7

# 获取指定报告
GET /v1/reports/{report_id}

# 健康检查
GET /health
```

**响应格式** (latest)
```json
{
  "platform": "polymarket",
  "updated_at": "2026-01-28T00:00:00+00:00",
  "title": "Trending Top20",
  "items": [
    {
      "rank": 1,
      "market_id": "...",
      "title": "...",
      "yes": 0.65,
      "no": 0.35,
      "volume_24h": 123456.78,
      "liquidity": 23456.78,
      "url": "https://...",
      "summary": "AI一句话摘要（可空）"
    }
  ]
}
```

**运行 Web API**
```bash
# 启动 API 服务器 (端口 8000)
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 后台运行
nohup python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &

# 使用 PM2 管理 (推荐)
pm2 start "uvicorn src.api.main:app --host 0.0.0.0 --port 8000" --name QwePolymarket-API
```

**API 文档**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 6. 🌐 Web Frontend (网页前端)

**项目路径**: `web/`

**技术栈**
- **框架**: Next.js 14 (App Router)
- **UI**: React 18 + TypeScript
- **样式**: Tailwind CSS
- **部署**: Vercel (推荐)

**核心功能**
- 🔄 平台切换：Polymarket / Opinion
- 👁️ 视图模式：Compact（摘要1行） / Full（摘要2-3行）
- ⏱️ 自动刷新：60秒间隔（可切换）
- 🕐 实时时钟：UTC 时间 + 更新时间
- 📱 响应式设计：支持桌面和移动端
- 🎨 Pump 风格：极简、高对比、暗色主题

**页面布局**
```
┌─────────────────────────────────────────┐
│ TopNav: Logo | Platform Tabs | UTC Time │
├─────────────────────────────────────────┤
│ Hero: "Trending" + Subtitle             │
├─────────────────────────────────────────┤
│ Control: View Mode + Auto-refresh       │
├─────────────────────────────────────────┤
│ List: 20 Market Cards                   │
│  - Rank + Title                         │
│  - Yes/No Odds                          │
│  - 24h Volume + Liquidity               │
│  - AI Summary (1-3 lines)               │
│  - Open Button → Market URL             │
└─────────────────────────────────────────┘
```

**本地开发**
```bash
cd web/
npm install
npm run dev  # http://localhost:3000
```

**部署到 Vercel**
```bash
# 方法1: Vercel CLI
cd web/
npm install -g vercel
vercel

# 方法2: Vercel Dashboard
# 1. 将项目推送到 GitHub
# 2. 在 Vercel Dashboard 导入仓库
# 3. Root Directory 设为 "web"
# 4. 一键部署
```

**环境变量**
```bash
# web/.env.local
NEXT_PUBLIC_API_BASE=https://your-api-domain.com
```

**详细文档**: 参考 `web/README.md`

---

## 🏗️ 技术架构

### 技术栈

**后端**
- **语言**: Python 3.10+
- **异步框架**: asyncio + aiohttp
- **进程管理**: PM2
- **定时任务**: apscheduler (AsyncIOScheduler)
- **Web API**: FastAPI + Uvicorn
- **数据存储**: SQLite3

**前端**
- **框架**: Next.js 14 (App Router)
- **UI**: React 18 + TypeScript
- **样式**: Tailwind CSS
- **部署**: Vercel
- **API 集成**:
  - Polymarket Gamma API (REST)
  - Opinion API (REST)
  - DeepSeek Chat API (OpenAI-compatible REST)
  - Telegram Bot API (REST)

### 架构特点

**纯异步设计**
- 所有 I/O 操作使用 asyncio
- HTTP 请求使用 aiohttp.ClientSession
- 支持并发批量处理

**分层架构**
- **Services**: PolymarketAPI / OpinionAPI / AIService / TelegramService
- **Storage**: SQLiteReportRepository (数据持久化)
- **Scheduler**: 定时任务管理 (Telegram 推送)
- **API**: FastAPI Web 服务 (HTTP 接口)

**数据流**
```
fetch -> normalize -> persist (SQLite) -> telegram push
                          ↓
                      Web API (latest/history)
```

**容错机制**
- API 重试机制（可配置次数）
- 超时保护（防止长时间等待）
- 降级处理（AI 失败时使用基础格式）
- 异常捕获和日志记录

---

## 📂 项目结构

```
QwePolymarket/
├── src/
│   ├── scheduler.py          # 主调度器（多平台定时任务）
│   ├── config.py             # 配置文件（API密钥、提示词、平台配置）
│   ├── services/
│   │   ├── api.py            # Polymarket API 封装
│   │   ├── opinion_api.py    # Opinion API 封装
│   │   ├── ai.py             # DeepSeek AI 服务
│   │   └── telegram.py       # Telegram 推送服务
│   └── tools/
│       └── test_daily.py     # 测试工具（手动触发日报）
├── run.py                    # 程序入口
├── .env                      # 环境变量（密钥配置）
├── ecosystem.config.js       # PM2 配置文件
├── CLAUDE.md                 # 技术文档（给 AI 阅读）
└── README.md                 # 项目说明（本文件）
```

### 核心文件说明

**main.py**
- 程序入口，启动调度器
- 加载环境变量
- 异常处理和优雅退出

**src/scheduler.py**
- 多平台定时任务管理
- `_run_polymarket_daily_report()`: Polymarket 日报 (UTC 00:00)
- `_run_opinion_daily_report()`: Opinion 日报 (UTC 12:00)
- `_process_markets_with_ai()`: 统一的 AI 处理流水线
- `_check_volatility()`: 波动率检查
- `_send_heartbeat()`: 心跳推送

**src/config.py**
- 全局配置常量
- 多平台配置（POLYMARKET_ENABLE, OPINION_ENABLE）
- 分平台推送时间（POLYMARKET_DAILY_REPORT_TIME, OPINION_DAILY_REPORT_TIME）
- API 密钥管理
- AI 提示词模板（支持平台识别）

**src/services/api.py**
- `PolymarketAPI.get_trending_markets(limit)`: 获取 Polymarket 热门市场
- 返回格式化的市场数据（rank, title, prices, url, volume_24h）

**src/services/opinion_api.py**
- `OpinionAPI.get_trending_markets(limit)`: 获取 Opinion 热门市场
- 数据格式对齐 Polymarket，统一接口
- 支持多种 API 响应格式解析

**src/services/ai.py**
- `rewrite_trending_report(items, platform)`: AI 改写市场列表
- 支持多平台（platform 参数）
- 批量处理，错误处理，超时控制

**src/services/telegram.py**
- `push(message, target)`: 推送消息
- 支持多目标（channel/admin）
- Markdown 格式处理

**src/tools/test_daily.py**
- 手动测试工具
- 支持测试不同平台 (--platform polymarket/opinion)
- 支持 dry-run 模式（不发送 Telegram）

---

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# Telegram 配置
TELEGRAM_BOT_TOKEN=8362423319:AAGql2IONE30XFJJd4jsmQY4-lCUpgawS2g
TELEGRAM_CHAT_ID=-1002259680787          # 主频道
TELEGRAM_ADMIN_ID=5026152284             # 管理员

# AI 配置
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx        # DeepSeek API 密钥

# Opinion 配置（可选）
OPINION_API_KEY=xxxxxxxxxxxxx            # Opinion API 密钥（如需要）

# Polymarket 配置 (可选)
POLYROUTER_API_KEY=pk-xxxxxxxxxxxxx      # 波动率检查用（可选）
```

### 定时任务配置

在 [src/config.py](src/config.py) 中修改：

```python
# Polymarket 配置
POLYMARKET_ENABLE = True
POLYMARKET_TRENDING_LIMIT = 20
POLYMARKET_DAILY_REPORT_TIME = "00:00"  # UTC (北京时间 08:00)

# Opinion 配置
OPINION_ENABLE = True
OPINION_TRENDING_LIMIT = 20
OPINION_DAILY_REPORT_TIME = "12:00"  # UTC (北京时间 20:00)

# 波动率检查（保持原有逻辑）
VOLATILITY_THRESHOLD = 0.05  # 5% 变化
```

### AI 提示词定制

在 [src/config.py](src/config.py) 中修改 `PROMPT_TRENDING_REWRITE`：

```python
PROMPT_TRENDING_REWRITE = """
你是专业的预测市场分析师，擅长从赔率中解读市场情绪和隐含信息。

【输入数据】
{data_json}

【输出格式】
每条前加 "ITEM_START"。

ITEM_START
**#[排名]** [Emoji] **[中文标题]**
📊 赔率：[主要选项概率]
💰 24h交易量：[格式化金额]
💡 [基于赔率的专业分析，20-35字]
🔗 [url]

【分析要点】
- 极端赔率(>95%或<5%)：强调共识，警示黑天鹅
- 分歧赔率(40-60%)：分析多空分歧，指出关键变量
- 交易量放大：解读背后驱动因素
- 赔率错位：识别市场定价偏差

【要求】
- 必须全中文输出
- 标题简洁，专业术语到位
- 分析基于数据，不做主观预测
- 保持客观中立，避免煽动情绪
"""
```

---

## 🚀 运行方式

### 开发环境

```bash
# 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入密钥

# 运行
python main.py
```

### 生产环境 (PM2)

```bash
# 启动服务
pm2 start ecosystem.config.js

# 查看状态
pm2 status QwePolymarket

# 查看日志
pm2 logs QwePolymarket

# 重启服务
pm2 restart QwePolymarket

# 停止服务
pm2 stop QwePolymarket
```

### 手动测试

使用内置测试工具进行端到端测试：

```bash
# 测试 Polymarket 日报（3条，dry-run）
python -m src.tools.test_daily --platform polymarket --limit 3 --dry-run

# 测试 Opinion 日报（5条，dry-run）
python -m src.tools.test_daily --platform opinion --limit 5 --dry-run

# 测试 Polymarket 并发送到 Telegram admin
python -m src.tools.test_daily --platform polymarket --limit 3

# 测试 Opinion 并发送到 Telegram admin
python -m src.tools.test_daily --platform opinion --limit 5
```

测试工具会：
1. 获取指定平台的 trending markets
2. 调用 AI 进行改写
3. 输出完整报告到终端
4. 可选：推送到 Telegram admin（非 dry-run 模式）

---

## 📚 版本演进

### V1-V20: Homepage-First 时代
- 使用 Polymarket Trending API
- 过滤体育/娱乐内容
- 最多 10 条市场
- 使用 Gemini → DeepSeek 转型

### V73: Multi-Platform Trending Top20 (Current)

**重大变更**
- ✅ **多平台支持**: 增加 Opinion.trade 平台
- ✅ **时间拆分**: Polymarket (UTC 00:00) / Opinion (UTC 12:00)
- ✅ 数据源：从 Trending API 切换到 `/markets` + `volume24hr` 排序
- ✅ 内容策略：移除所有过滤，包含所有类型市场
- ✅ 数量：每平台 Top 20 条
- ✅ AI 提示词：重写为基于赔率的专业分析，支持平台识别
- ✅ 推送格式：完全中文化，聚焦赔率解读，平台标识清晰

**架构优化**
- 新增 `OpinionAPI` 服务，数据格式对齐 Polymarket
- Scheduler 拆分为两个独立 job（`_run_polymarket_daily_report`, `_run_opinion_daily_report`）
- 统一的市场处理流水线 `_process_markets_with_ai()`
- AI 改写支持 `platform` 参数
- 批量 AI 处理（5个/批）
- 超时保护（45s）+ 降级策略
- 测试工具 `src/tools/test_daily.py` 支持手动测试

**为什么改变**
1. **覆盖面**: 多平台覆盖更多市场动态
2. **分时推送**: 不同时间推送不同平台，避免信息过载
3. **专业性**: DeepSeek 中文分析，深度解读赔率
4. **可扩展性**: 架构支持快速增加新平台

---

## 🐛 已知问题

### 1. Opinion API 适配
- **现状**: Opinion API 封装基于假设的接口设计
- **影响**: 需要根据实际 API 文档调整 `opinion_api.py`
- **解决方案**: 获取 Opinion 官方 API 文档后更新 `OpinionAPI` 类
- **当前策略**: 支持多种响应格式解析，兼容性较好

### 2. Polyrouter 429 错误
- **现象**: 波动率检查频繁遇到 API 限流
- **影响**: 不影响日报推送，只影响实时监控
- **临时方案**: 可以禁用波动率检查
- **长期方案**: 需要申请更高的 API 配额或优化请求频率

### 3. AI 偶尔返回空
- **现象**: DeepSeek API 偶尔超时或返回空内容
- **影响**: 触发降级格式（基础版推送）
- **缓解措施**: 已增加到 45s 超时和 2 次重试

---

## 📝 开发指南

### 添加新的定时任务

在 [src/scheduler.py](src/scheduler.py) 中：

```python
def _schedule_jobs(self):
    # 添加新任务
    self.scheduler.add_job(
        self._your_new_task,
        trigger='cron',
        hour='*/6',  # 每6小时
        minute='0'
    )

async def _your_new_task(self):
    """您的新任务"""
    print("🔔 Running your new task...")
    # 实现逻辑
```

### 自定义 AI 分析逻辑

修改 [src/services/ai.py](src/services/ai.py) 的 `rewrite_trending_report()` 方法：

```python
async def rewrite_trending_report(self, items):
    # 自定义提示词
    custom_prompt = f"自定义分析: {items}"

    # 调用 AI
    response = await self._call_deepseek(
        custom_prompt,
        retries=2,
        timeout=45
    )

    # 自定义解析逻辑
    return self._custom_parse(response)
```

---

## 🔒 安全注意事项

1. **不要提交 .env 文件** - 包含敏感密钥
2. **不要提交 data/ 和 logs/** - 包含用户数据
3. **定期轮换 API 密钥** - 降低泄露风险
4. **使用私有 Telegram 频道** - 避免信息泄露

---

## 📄 License

MIT License

---

## 👨‍💻 Maintainer

Project by **Antigravity**

Co-developed with **Claude Opus 4.5** (Anthropic)

---

## 🔗 相关链接

- [Polymarket](https://polymarket.com/)
- [DeepSeek API](https://platform.deepseek.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [PM2 Documentation](https://pm2.keymetrics.io/)

---

**最后更新**: 2026-01-28 (V73)
