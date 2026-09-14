# CoinSignal Agent 规则

## 项目与边界
- Python 3.11/3.12，asyncio + aiohttp，Binance REST 行情，Telegram 通知；Redis 可选，PM2 单进程。无网页、Node package 或 Cloudflare Worker。
- 保持现有公共行情来源和可选 Redis，不擅自引入付费 API、基础设施或交易执行功能。收费能力需用户明确授权。
- 密钥只放服务器环境或平台安全配置；不提交 .env、token、chat ID 或包含凭据的日志。登录权限不会随文档继承。
- 本轮授权为仓库文档与检查，交付到 Draft PR；不自动合并、部署或发送 Telegram 消息。后续沿用会话内明确授权，并在交接记录授权范围，不从历史发布记录推断授权。
- 生产只允许一位整合负责人操作。`scripts/reload_pm2.sh` 会删除两个旧 PM2 服务，运行前核对部署授权、进程影响和回退方案。

## 信息唯一来源
- 本文件：长期规则；[agent.md](agent.md)、[CLAUDE.md](CLAUDE.md)、[GEMINI.md](GEMINI.md)：入口。
- [当前交接](docs/handoff.md)：唯一 Current execution pointer 与当前状态。
- [待办](docs/backlog.md)：优先级、范围、验收；Issue：认领、文件边界和讨论。
- [呈现规则](docs/ui-rules.md)：Telegram 排版；[数据契约](docs/data-contract.md)：来源与口径。
- [发布记录](docs/releases/README.md)：不可覆盖的历史与验证证据；PR：交付差异及检查链接。

## 开工与协作
1. 阅读本文件、入口、交接、当前 Issue 及涉及模块规范。
2. 检查 `git status --short`、`git fetch origin`、远端 main、开放 Issue/PR 和认领。不要覆盖他人未提交修改。
3. 有生产访问权限时核对服务器源码 SHA、PM2 进程与日志；没有权限就记录未核验，不能把 main 或 CI 成功当作生产版本。
4. 简短说明当前状态、下一步、授权边界，然后执行。文档冲突先查证再修正；新任务先更新交接指针。
5. 并行时每个 Agent 认领独立 Issue、分支/worktree 和文件范围；重叠修改先协调。整合负责人负责合并及部署，禁止同时更新生产。

## 完成与交接
- 代码完成、测试通过、PR 合并、部署成功、线上验收通过必须分别记录。
- 运行 README 的验证命令和仓库检查；应用变更同时更新交接与一份验证记录。
- 版本仅在实际发布版本变化时更新；`VERSION`、`pyproject.toml` 与对应版本说明一致。没有 package.json，不创建虚假 package 文件。
- 中途交接也应提交有效代码并推送任务分支，保留 Draft PR；不能为交接强行合并。
- 结束时填写交接全部字段，历史状态移至 releases；提交/PR 自引用用可解析的父提交或 PR head 描述，并在 PR 记录最终提交，避免循环修改 SHA。
- CI 检查结构与变更范围，不证明文档内容真实，也不证明通知送达或线上健康。
