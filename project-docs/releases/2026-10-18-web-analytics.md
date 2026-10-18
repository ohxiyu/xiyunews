# Cloudflare Web Analytics 访问统计

Issue: https://github.com/ohxiyu/xiyunews/issues/290；branch agent/web-analytics，当前会话唯一 owner。运营者要求接入 Cloudflare Web Analytics，在 Cloudflare 后台查看访问量与热门页面，不做站内数据页。

PR: https://github.com/ohxiyu/xiyunews/pull/291

## 改动

- `docs/_config.yml` 新增 `cloudflare_web_analytics_token`。站点令牌本身会出现在每个页面里，属于公开值、不是密钥；为空时页面不输出任何统计脚本。
- `docs/_includes/head-custom.html`：令牌非空时加载官方 `https://static.cloudflareinsights.com/beacon.min.js`（defer）。来源控制台页面（page_type=source_console）不加载；后台 /s/ 使用 layout:null，本来就不经过该模板。接口、RSS 和订阅文件不是 HTML 页面，不受影响。
- `/legal/` 中英文补充访问统计说明：不设置 Cookie，不靠浏览器存储识别访客，不做跨站追踪或画像。
- 公开页面当前没有 CSP（只有 /admin/* 有），因此不用修改 CSP。Service Worker 只处理同源请求，统计脚本和上报请求都不会进入离线缓存。

不改 Worker、Cron、DNS、Access、密钥、AI、评分、分发、数据或状态分支。Cloudflare Web Analytics 在所有套餐下免费，没有新增费用。

## 验证

- 新增 `tests/test_web_analytics.py`，4 项：令牌只能为空或 32 位十六进制；脚本只在令牌非空且不是来源控制台时输出；页面上唯一的第三方脚本是官方 beacon，令牌经 jsonify 转义；法律页有说明。
- 用 Ruby Liquid 4.0.4 渲染片段：令牌为空、令牌缺失、来源控制台三种情况都不输出；有效令牌只输出一个 beacon 标签。
- `uv run pytest`：1118 passed，4 skipped（既有条件跳过）。`scripts/check_governance.py` 通过。

## 依赖安全修复（CI 发现）

PR291 首次 CI 的 test 任务里，pip-audit 报告 mcp 1.28.1 存在 CVE-2026-59951（修复版本 1.30.0 / 2.2.0）。这与本次改动无关，main 上任何 PR 都会因此失败。直接升级会跳到 mcp 2.3.0 的大版本，所以没有采用；改为 `uv lock --upgrade-package 'mcp<2'`，只把 uv.lock 里的 mcp 升到 1.30.0（3 行改动，pyproject 约束不变，其他包不变）。升级后本地 pytest 1118 passed / 4 skipped，pip-audit 结果为 No known vulnerabilities found。

## 上线与待办

- 本次合并时令牌为空，线上页面不变。
- 运营者在 Cloudflare 后台 Web Analytics 添加 xiyu.news，选择手动 JS 片段，并提供站点令牌，避免和自动注入重复计数；随后用一个单行 PR 写入令牌，按既有 Deploy Docs → cloudflare-unified 路径上线。
- 生产验收：主域 HTML 含 beacon，Cloudflare 后台出现访问数据。本环境的代理无法访问 xiyu.news，需由运营者在后台确认。

## 合并与部署证据

- PR291 于 2026-10-18 05:38Z 合并为 d22034fe02be77bc07f351762c179d35556dd71c，合并前全部适用检查通过（governance、realtime-paths、test、web、edge-build）。
- Deploy Docs 39101269168 success（05:40:49Z），gh-pages a76d9082 含新的 head-custom 令牌判断、`cloudflare_web_analytics_token: ""` 和法律页统计说明（从 gh-pages 回读确认）。
- xiyunews Cloudflare 统一部署 163（39101320453）与 164（39101378884）均 success（05:45–05:46Z）。
- 令牌为空，因此线上页面不输出统计脚本，只多了法律页说明，符合预期。

Source commit: d22034fe02be77bc07f351762c179d35556dd71c。
Artifact commit: gh-pages a76d9082。
Worker version: 未改动 Worker 代码；统一部署只运送静态资产。
Deployment: complete（令牌为空）。
Verification: 主域页面回读未进行（本环境代理无法访问 xiyu.news）；统计生效需站点令牌。
Rollback: 令牌改回空字符串即可停用，不涉及状态或数据。
