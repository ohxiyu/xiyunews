# 使用 PR #306 恢复整站及东京执行器

## 源码和依赖

按运营者选定的 [PR #306](https://github.com/ohxiyu/xiyunews/pull/306) 合并提交 `0291c7ff86b56847ffbde20e756561bce381a242` 恢复。恢复提交的 Git tree 为 `4c5ac2a784e6898f1aaad207ee992c337b87a5af`，与基线完全一致。随后单独应用草稿已有的 Soup Sieve 4.0 安全修复及 Python 3.11.5 最低版本要求。生产路径要求 `XIYUNEWS_RUNTIME_MODE=tokyo`，当前设置为 `hosted`。公开仓库的普通 CI 沿用 GitHub 托管执行，退役的自动备份工作流不参与上线。

基线 Python 测试 1,120 项通过、4 项既有跳过，应用依赖修复后结果相同。Worker 135 项、网页 Node 118 项、TypeScript 检查通过。最初 Python all-extras 审计有 4 条 Soup Sieve 告警，修复后为零。Node 审计为零。11 月 21 日公开快照在本地通过 Jekyll 构建和群组消息包生成。基线模型读取了当期 12 条、100 个已出版日期、1,164 条归档记录及 2,357 个追踪事件，X 队列两期计划可解析。构建和检查没有模型调用和外部发送。

## 当前生产记录与切换条件

- 11 月 21 日已发布 12 条，生产构建输入为 `155cf1f7` 与 [gh-pages 70979f0c](https://github.com/ohxiyu/xiyunews/commit/70979f0ce64ceceb0b1a7b33ec20bb06570c7f7c)。[Cloudflare 发布运行](https://github.com/ohxiyu/xiyunews/actions/runs/44837387186)成功，正式域健康端点显示托管执行和 Cloudflare 私有状态。
- [现行账本校验](https://github.com/ohxiyu/xiyunews/actions/runs/44869611115)通过并释放状态租约。Cloudflare SQLite 中有 13 期选稿快照、4,003 条 AI 缓存以及 1 条日报 Telegram 回执。[当天 Telegram 运行](https://github.com/ohxiyu/xiyunews/actions/runs/44837779298)日志记录了 `sent`。东京已停用 SQLite 的只读 `quick_check` 通过，存在 11 月 9、14、15、16、17 日的 5 条已发送回执。两边必须按期与目的地核对，完整性检查本身不能证明历史回执齐全。
- 东京主机可用 SSH 严格指纹访问，实时服务运行中。旧执行器停止且已注销，二进制已清理。实测可用内存 459 至 494 MiB，原安装脚本要求至少 600 MiB。重新注册前需要满足原容量检查，并验证生产任务实际负载。现有 DeepSeek 密钥名存在，账号与模型是否可用仍待验证。
- 旧版 Worker 发布会丢失私有状态接口，旧版日报可直接发送 Telegram，X 也走旧发送路径。现有 `SQUARE_ENABLED` 仍为 true，恢复其工作流会重新接入发送触发。切换需要先恢复对现行账本和投递凭证的连续访问，按逐期回执证明已发送及未知状态不会被再发送。使用当前公开归档完成一次无 AI 代码部署后，分别验收真实的自然出刊和渠道状态。

当前保存于草稿 PR。保留正在运行的生产任务、生成分支、Cloudflare 私有状态与东京实时服务。
