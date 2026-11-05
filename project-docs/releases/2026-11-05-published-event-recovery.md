# 2026-11-05 已发布事件节点与持久确认恢复

[Issue315](https://github.com/ohxiyu/xiyunews/issues/315)，串行依赖 [PR314](https://github.com/ohxiyu/xiyunews/pull/314) 已合并。当前会话唯一编辑/生产整合负责人，分支 agent/published-event-recovery，复用独立 worktree xiyunews-delivery-recovery。用户授权继续修复、正常合并部署；不改费用、密钥、DNS、Cron、来源、实时规则或渠道，不手写产物/队列分支、不重发消息。

## 发现与范围

前置 PR314 已恢复 2026-11-05 的 13 条正文、X 第一条 HTTP201、SQLite/Git 回执一致、磁盘和统一发布。后续公开 URL 验收发现 9 个事件节点不在目录，其中 5 个事件 JSON404；SQLite、mirror 和 Git 均缺失，不能归因于 CDN。原稿、选稿正文与稳定 event/update 编号仍在，原 41964081010 报告记录 6 个新事件、3 个新进展、1 个事件归并；07:13:11Z 的新 online backup 完整性通过，未恢复整库或改写回执。

PublicationState.load_document 曾将 incoming==current 自动当成 Git 追上，清 dirty 并推进 source_digest。生成后本地去重/归档读取自己的导出也满足此条件，实际 push 随后失败，下一次旧 Git 恢复因 dirty 已清而覆盖目录。修复删除这种隐式确认；本地同值读取不确认任何持久性。四个实际目录发布工作流只在 actions-gh-pages 成功之后调用远端精确回读：刷新 origin/gh-pages、固定完整 SHA，比较本次实际导出与远端 JSON，再对现有 SQLite 文档执行一笔整批 payload/digest CAS。任何内容不符或并发变化均回滚确认，失败发布不会清 dirty，X/Square 既有成功 push ACK 不变。

正常日报的已保存刊期重试会先核对公开归属，再恢复缺失节点，随后重建双语页面/API/归档。只接受已保存的稳定身份、原文和来源，不重新做语义归类；缺父事件只能使用与原稿匹配的稳定新事件 ID，归并节点需保留原始稳定 update ID。其他归属冲突、无法证明的 ID、缺原文、已有节点中的不明重复来源均停止整批，不半写。

恢复保留正文、背景、资料、来源和原时间。已丢失的既有事件进展分类/模型置信度不能从公开编号还原：只用保守“确认”节点，置信度0明确未知，保持父事件原状态及状态描述；不虚构“升级/修复/解决”。目录 published_link_recoveries 逐条记录刊期、编号、公开输入 SHA-256 与分类恢复限制。五个新事件按原稳定身份及已保存公开文字生成初始节点；不宣称与已丢失内部分类逐字段相同。

真实 SQLite 只读演练（无 active_store、禁止写入）在 2275 个事件上恢复9节点/5事件，9个公开引用全部匹配，输入散列31e52278c783a0d1ae6c3868802c86ad32db4ec6da53f5a2fdf045d99499bb2d保持，第二次恢复0变化。未调用 AI/来源/行情或渠道。原关系缓存只能精确重放7/9，原归并分类没有持久记录，因此未用模型猜另外两条。

## 验证与五阶段

本地回归覆盖本地反复读取后重启、失败 push 的旧快照、独立写入冲突、整批确认回滚、真实 bare Git 远端字节核对、后续新状态保护；事件恢复覆盖稳定初始/进展/归并 ID、原文及资料、父状态保留、错误整批失败、无网络正常日报重试和字节幂等。

- 代码：已实现。
- 测试：完整Python1172 passed/4既有skipped，最终追加合法归并别名回归后17项定向通过；治理、编译与差异检查通过，远端CI待完成。
- 合并：待当前PR检查通过且同步main。
- 部署：当前事件恢复未部署；前置PR314已部署。
- 生产验收：9个缺失节点仍待正常恢复与逐个在线核对；不声称浏览器已通过。

Source commit: 前置准确SHA 35f8db4f22ace7c73fc235dca4dd7afaf2d4286d；本PR待合并。

Worker version: not changed；前置已验证8cc86cf1-3abf-4320-af86-8d918931a5d3，后续正常统一发布待核对。

Deployment: 正常日报已有刊期重试恢复，不使用force_publish；Cloudflare自动接收gh-pages并发布。

Verification: 2026-11-05只读真实演练成功；正式9节点、HTML锚点、中英桌面/手机和回执待验收。

Rollback: 不自动回滚或恢复整库；保留online backup与Git历史，任何冲突停止并保留双方，不清队列或重复发消息。
