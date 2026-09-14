# 当前交接

## Current execution pointer
当前目标：继续 Issue #4，完成 fomobtc.com / api.fomobtc.com 接入、HTTPS 与推送验收。
任务 Issue / 负责人：[Issue #4](https://github.com/ohxiyu/fomobtc/issues/4) / Codex 实施，ohxiyu 认领。
工作分支 / 最后提交 / PR：deploy/tokyo-domain，父提交 fe829b4b96002351c8237255bd96b02714d4d124；本次配置与证据提交以 PR head 为准；实现 PR #5 和前端证据 PR #6 已合并。
已经完成：仓库已改名 fomobtc；2.0 实现与前端已部署；东京 VPS 专用 SSH、Python venv、SQLite、systemd 服务及内存限制已配置，后台行情与 OKX 采集运行；nginx/Certbot 已安装；Cloudflare Free 区域和 api A 记录已创建。
尚未完成：Dynadot 名称服务器切换、停放记录移除、域名 TLS、前端 API_ORIGIN 与自定义域名发布；Telegram 与 Binance 公告凭据、真实推送和完整业务验收；Issue #4 保持开放。
已运行的验证及结果：既有 34 项测试与实现 PR #5 四项 CI 通过；本次实际 SSH、systemd 开机启动与进程、loopback 健康 API 200、8 个行情分片 live 检查通过；nginx TLS 模板离线语法及证书续期 systemd 单元校验通过；详细观测见东京发布记录。
尚未验证的内容：公网 TLS/API/SSE、证书续期、域名前端、24 小时稳定性、端到端 P95/P99、Binance 公告鉴权、Hyperliquid 客户端授权、Telegram API 回执及手机收件。
线上版本 / 对应源码提交：东京后台 2.0.0 / fe829b4b96002351c8237255bd96b02714d4d124；前端仍为 https://fomobtc.drminutes.workers.dev / 206c616aa56971f9331f8b1c84f7d52b6deec4ef / Worker f1ae7fad-3b5e-449e-ada4-054fb57c2b62，API_ORIGIN 为空；fomobtc.com 尚未切换。
阻塞与所需权限：已获 SSH、合并部署授权；等待用户打开 Dynadot DNS 表单（电脑坐标工具报 noWindowsAvailable，菜单未暴露独立选项），以及确认删除 3 条停放记录；Telegram/Binance 凭据位置仍未提供。密钥不进聊天或仓库。
下一步具体动作：仅针对 fomobtc.com 设置 ignat.ns.cloudflare.com / shaz.ns.cloudflare.com；确认后清理停放记录并接入 Worker 自定义域名；DNS 生效后签发 api TLS、启用代理和自动续期，构建并发布连接 API 的前端；再配置凭据并验收通知。不要把 DNS 计划写成已生效。

## 五项状态
- 代码完成：2.0 实现完成；本次新增部署模板与证据。
- 测试通过：实现本地 34/34、远端 CI 已通过；部署模板验证如上。
- PR 合并：#3、#5、#6 已合并；本次 PR 状态见 GitHub。
- 部署成功：东京后台采集进程和旧 Worker 前端已部署；新域名与公网 API 尚未完成。
- 线上验收通过：服务器本地采集部分通过；公网接入及推送未通过完整验收。

历史记录：[2026-09-08 交接](releases/handoff-20260908.md)、[首次前端部署](releases/deploy-20260914-frontend.md)、[东京部署](releases/deploy-20260914-tokyo.md)。
