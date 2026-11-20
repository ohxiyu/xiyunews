# PyJWT / urllib3 依赖安全修复

任务：[Issue164](https://github.com/ohxiyu/bmtnews-standalone/issues/164)。Owner: Codex / security-deps；分支 agent/security-deps；基线 9ba3df1c15dee517779c5780c9d0c37fd1806f1d。用户明确授权先独立处理这两个依赖，再继续 Logo PR163。仅修改依赖约束、锁文件、安全回归测试及交接记录；不修改认证方案、Worker、Secrets、调度、模型或费用。

## 修复依据及范围

Logo PR163 的 CI 报告 PyJWT 2.13.0 的 13 条漏洞、urllib3 2.7.0 的 3 条漏洞；这不是已经证明生产系统遭到利用。PyJWT 为 MCP / 可选 OpenBB 的传递依赖，urllib3 为 Requests / Google GenAI / 可选抓取依赖的传递依赖。

升级 PyJWT 至 2.15.1、urllib3 至 2.8.0。在 tool.uv.constraint-dependencies 设置对应最低版本及 <3 上界，只约束已有传递依赖，不添加新直接依赖，也不覆盖上游依赖要求。定向 uv lock 仅升级这两个包，应用版本仍为 0.2.0。

[PyJWT 官方变更日志](https://github.com/jpadilla/pyjwt/blob/2.15.1/CHANGELOG.rst) 与 [urllib3 2.8.0](https://github.com/urllib3/urllib3/releases/tag/2.8.0) 记录相关安全修复。[CVE-2026-103001 公告](https://github.com/advisories/GHSA-gvp8-978c-rx2q) 的 first_patched_version 未填写，但受影响范围为 >=2.11.0、<=2.13.0。不能仅凭空白字段推断所有新版仍受影响；新增回归测试验证未验签读取不会修改调用者 options，复用并启用验签后过期 / 未生效声明仍被拒绝。

其他测试覆盖有效 JWT 解码、错误签名拒绝、锁文件与约束的安全下限、普通 chunked 响应兼容、超长 chunk-size 行拒绝。保持现有完整 all-extras 审计，不忽略 CVE，不降低检查要求。

## 验证与发布

本地验证：8 项安全回归通过，全量 pytest 925 项通过，治理与 diff 检查通过，61 项 Node 前端测试通过，Worker 61 项测试 / 类型检查 / 部署 dry-run 通过。CI 同参数导出全部 extras，pip-audit 2.10.1 / PyPI 完整审计报告 No known vulnerabilities found（未忽略任何漏洞）。urllib3 测试夹具最初错误传递 HTTPMessage，改为正常 headers 映射后回归及全量检查通过，未改动实际依赖行为。

npm ci 另报告 Worker 开发依赖树中 7 项告警（2 moderate / 5 high）；本任务未评估或修复该独立 npm 范围，不执行 npm audit fix --force，也不将 Python 审计成功描述为所有技术栈无漏洞。[PR165](https://github.com/ohxiyu/bmtnews-standalone/pull/165) 已提交；远端 CI、合并与生产部署尚未完成。

本安全 PR 合并后，Logo PR163 必须同步新 main 并重新通过全部检查，才能合并及发布。依赖修复会由后续采集 / 日报 Actions 的 frozen sync 使用；静态 Pages 部署不会安装 Python 服务。不得为了验证依赖重跑 AI 或推送外部消息。

## 正式合并及实际执行证据

[PR165](https://github.com/ohxiyu/bmtnews-standalone/pull/165) 于 2026-10-01T04:13:34Z 合并，merge commit 84c93d9962a8bfb042a6f37b71816dd556250513。新 HEAD 20bca9f99122d8e4ebe8d601018d4307041d56f5 的 [CI 36813910166](https://github.com/ohxiyu/bmtnews-standalone/actions/runs/36813910166) / CodeQL / Pages 分支检查全部通过，远端 pytest 925 项、完整 all-extras 审计无已知漏洞。

Logo PR163 同步后全部检查通过并合并。实际 [Deploy Docs 36814384490](https://github.com/ohxiyu/bmtnews-standalone/actions/runs/36814384490) 于 2026-10-01T04:17:25Z 成功；其 Install dependencies 日志明确为 pyjwt==2.15.1 / urllib3==2.8.0，随后实体重建与无 AI Quick Post 渲染通过。这是修复后冻结依赖实际被自动任务使用的证据；未手动重跑 AI / 日报或外部推送。所有未来任务是否成功仍取决于各自运行，不保证尚未发生的采集。

Source commit: 84c93d9962a8bfb042a6f37b71816dd556250513; actual deployed source fa50a0fd95619db4ccd46cc056105925df294466 includes this fix
Worker version: unchanged; no Worker deployment authorized or performed
Deployment: Deploy Docs 36814384490 succeeded 2026-10-01T04:17:25Z; frozen sync used PyJWT 2.15.1 / urllib3 2.8.0
Verification: CI 36813910166 passed, all-extras pip-audit clean; actual automated install and no-AI render succeeded
Rollback: requires separate authorization; reverting the dependency PR would restore known vulnerable versions and is not an acceptable routine fallback
