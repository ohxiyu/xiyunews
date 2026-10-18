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

## 上线与待办

- 本次合并时令牌为空，线上页面不变。
- 运营者在 Cloudflare 后台 Web Analytics 添加 xiyu.news，选择手动 JS 片段，并提供站点令牌，避免和自动注入重复计数；随后用一个单行 PR 写入令牌，按既有 Deploy Docs → cloudflare-unified 路径上线。
- 生产验收：主域 HTML 含 beacon，Cloudflare 后台出现访问数据。本环境的代理无法访问 xiyu.news，需由运营者在后台确认。

Source commit: 现役 51acae41533fe1279715318db1acec1d54cb80a5，本改动未合并。
Worker version: d7e2c610-2b5d-4c76-beca-8f4df2bf2390，不改动。
Deployment: pending（合并后走既有自动路径）。
Verification: 仅离线测试与模板渲染。
Rollback: 令牌改回空字符串即可停用，不涉及状态或数据。
