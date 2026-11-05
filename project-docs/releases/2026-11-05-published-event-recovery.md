# 2026-11-05 已发布事件节点与持久确认恢复

[Issue315](https://github.com/ohxiyu/xiyunews/issues/315)，串行依赖 [PR314](https://github.com/ohxiyu/xiyunews/pull/314) 已合并。当前会话唯一编辑/生产整合负责人，分支 agent/published-event-recovery，复用独立 worktree xiyunews-delivery-recovery。用户授权继续修复、正常合并部署；不改费用、密钥、DNS、Cron、来源、实时规则或渠道，不手写产物/队列分支、不重发消息。

## 发现与范围

前置 PR314 已恢复 2026-11-05 的 13 条正文、X 第一条 HTTP201、SQLite/Git 回执一致、磁盘和统一发布。后续公开 URL 验收发现 9 个事件节点不在目录，其中 5 个事件 JSON404；SQLite、mirror 和 Git 均缺失，不能归因于 CDN。原稿、选稿正文与稳定 event/update 编号仍在，原 41964081010 报告记录 6 个新事件、3 个新进展、1 个事件归并；07:13:11Z 的新 online backup 完整性通过，未恢复整库或改写回执。

PublicationState.load_document 曾将 incoming==current 自动当成 Git 追上，清 dirty 并推进 source_digest。生成后本地去重/归档读取自己的导出也满足此条件，实际 push 随后失败，下一次旧 Git 恢复因 dirty 已清而覆盖目录。修复删除这种隐式确认；本地同值读取不确认任何持久性。四个实际目录发布工作流只在 actions-gh-pages 成功之后调用远端精确回读：刷新 origin/gh-pages、固定完整 SHA，比较本次实际导出与远端 JSON，再对现有 SQLite 文档执行一笔整批 payload/digest CAS。任何内容不符或并发变化均回滚确认，失败发布不会清 dirty，X/Square 既有成功 push ACK 不变。

正常日报的已保存刊期重试会先核对公开归属，再恢复缺失节点，随后重建双语页面/API/归档。只接受已保存的稳定身份、原文和来源，不重新做语义归类；缺父事件只能使用与原稿匹配的稳定新事件 ID，归并节点需保留原始稳定 update ID。其他归属冲突、无法证明的 ID、缺原文、已有节点中的不明重复来源均停止整批，不半写。

恢复保留正文、背景、资料、来源和原时间。已丢失的既有事件进展分类/模型置信度不能从公开编号还原：只用保守“确认”节点，置信度0明确未知，保持父事件原状态及状态描述；不虚构“升级/修复/解决”。目录 published_link_recoveries 逐条记录刊期、编号、公开输入 SHA-256 与分类恢复限制。五个新事件按原稳定身份及已保存公开文字生成初始节点；不宣称与已丢失内部分类逐字段相同。

真实 SQLite 只读演练（无 active_store、禁止写入）在 2275 个事件上恢复9节点/5事件，9个公开引用全部匹配，输入散列31e52278c783a0d1ae6c3868802c86ad32db4ec6da53f5a2fdf045d99499bb2d保持，第二次恢复0变化。未调用 AI/来源/行情或渠道。原关系缓存只能精确重放7/9，原归并分类没有持久记录，因此未用模型猜另外两条。

补充发布失败后的第二次重试保护：四个目录发布入口在渲染前先将已协调的持久文档物化到工作区；否则渲染器虽已读取新SQLite，源JSON仍可能是旧Git，导致再次发布旧目录。恢复导出先校验所有输入、再写工作区，不清dirty；发布成功后仍须远端字节核对与整批CAS。新增回归覆盖重试导出、重复读取、第二个文档冲突时不半写工作区。

## 验证与五阶段

本地回归覆盖本地反复读取后重启、失败 push 的旧快照、独立写入冲突、整批确认回滚、真实 bare Git 远端字节核对、后续新状态保护；事件恢复覆盖稳定初始/进展/归并 ID、原文及资料、父状态保留、错误整批失败、无网络正常日报重试和字节幂等。

- 代码：已实现。
- 测试：最终完整Python1174 passed/4既有skipped；18项恢复/真实Git定向回归、治理、编译与差异检查通过。远端最终head774df80d9e94efdffdb5acd8e07086772ed74e50的完整CI41986971783、Cloudflare预览全部通过，realtime3.11/3.12、网页与正式构建均成功。
- 合并：PR316于2026-11-05 07:35:29Z合并，准确SHAe70b686b0d77ee146a4dbfa5abe610de00f96b8a；与最终head的tree均为3a874f78d14cfffa6a2ec572734b26a33100087d，合并SHA为origin/main祖先。前一次CI41986468603被新head替代，曾请求取消时已结束，未取消生产任务。
- 部署：Deploy Docs41988314544成功；已有刊期正常恢复41988451745于07:36:42–07:38:53Z成功，未使用force_publish。Cloudflare41988491961于07:37:02–07:51:56Z成功，实际上传1239个变更文件、复用8758个既有文件，上传371.34秒；无网络错误。
- 生产验收：2026-11-05正式域普通URL验证通过，今日13条、9个事件JSON与准确update_id及HTML锚点全部可达；中英×1440/390四组首页均13条、canonical正确、无横向溢出/脚本错误。数据库与出版、普通公共API一致，五阶段完成。

## 实际恢复与完整性证据

Deploy Docs在07:36:01Z导出持久事件目录，07:36:50Z成功回读并确认artifact07fda760d521c2492554fde1b78cb8405249b9c0。日报恢复在07:37:31Z导出daily/event_urls/events，07:38:43Z回读准确artifact6b26e0e45b3113ea221cdb001c0f97cf1f7e9712并整批确认。出版目录由2275增至2280个事件，恢复审计恰为9条、均属2026-11-05；原4493条报道归属全部保留，恰新增9条归属。日报与X队列payload均逐字等于07:13:11Z online backup，原选稿updated_at04:41:35.962958Z未变。daily/events/event_urls/x_queue的dirty均0，quick_check为ok。

首条X回执仍为2118229625906348151，第二条planned、due_at11:22:26.370779Z（上海19:22）；本次未变更正文、计划或发送回执。Git与SQLite队列canonical散列均373f064819a68de89d1f6f6b68b10e054c7c7a99dbf69746b32330c8d9497319。未人为发送第二条或补旧消息。生产构建时磁盘50%、约19GiB空余；新增构建工作区会由现有hook清理，不将临时增长解释为再次写满。

后续独立自然运行：Feed Collection41990054741成功，新增100条原稿、3个实质进展、1个补充来源和9个新事件。08:09:16Z正常远端回读并确认daily/event_urls/events，后续自然产物1e50c8330fb4df428bd085ab55ca00c55008f80c。发布中只读观察events.digest不等于source_digest且dirty1，旧远端仍6b；成功push后才确认新基线，实际证明本地读取不再提前清除待保存状态。该运行由原定时系统派发，未额外手动采集或为测试调用AI。本次9节点恢复的正式验收版本为前述6b/52bb，后续自然内容继续按原流程发布。

Source commit: e70b686b0d77ee146a4dbfa5abe610de00f96b8a。

Worker version: 52bb9281-597f-4db6-98cd-812fc67efe8f；普通/health准确回读source e70b686b0d77ee146a4dbfa5abe610de00f96b8a、artifact6b26e0e45b3113ea221cdb001c0f97cf1f7e9712、build key47df55b0f4afeef9449738cffaac457d24ae91641e57bd919f3f2aafa3019512。

Deployment: [正常日报41988451745](https://github.com/ohxiyu/xiyunews/actions/runs/41988451745)与[Cloudflare41988491961](https://github.com/ohxiyu/xiyunews/actions/runs/41988491961)成功；[PR316](https://github.com/ohxiyu/xiyunews/pull/316)已合并。

Verification: 2026-11-05普通正式域首页/API/ready/feed/sitemap/双语刊期、9事件JSON/HTML锚点及4组浏览器阅读通过；/api/latest.json为2026-11-05/13条、generated_at07:37:56.199782Z，items canonical散列0e2b243844cf202fecff3d6592c7001ad27aec2fee95e2bbe6d43f5a32d30e10与修复前完全相同。服务器选稿原updated_at仍04:41:35.962958Z，未混用为重刊时间。第一条X回执已验证，第二条仍待19:22自然到期，不人为提前发帖验证未来调度。

Rollback: 不自动回滚或恢复整库；保留online backup与Git历史，任何冲突停止并保留双方，不清队列或重复发消息。
