# 旧品牌资源清理与运行依赖核验

Issue: https://github.com/ohxiyu/xiyunews/issues/193

运营者授权清理确实无用的旧 FomoBTC/BMTNews 资源，并报告 Telegram Bot 已换、仍用原频道且频道已改名。本次删除的是停用的 Pages 项目 `horizon-ohxiyu`，不是承载新站的 `bmtnews`；后者、日报调度器、实时看门狗、旧实时仓和 API 域名均有实际依赖，继续保留。详见 [资源清单](../legacy-resources.md)。

## 删除记录与恢复边界

旧 Horizon 项目没有自定义域，连接不可访问旧仓，最近生产更新为 2026-08-21。因 323 个部署触发 `8000076`，按 Cloudflare 官方已知问题流程仅删除该项目 Preview，再删除项目；一次网络中断后重新查询剩余目标继续，不碰新站或其他项目。CLI 最终返回 `Successfully deleted horizon-ohxiyu`，项目列表确认旧项目不存在、生产 `bmtnews` 仍在。

项目配置和公开首页保存在本机 `/tmp/xiyunews-legacy-pages-backup.n1NmPl`，不是完整站点备份，不能直接恢复历史部署。旧域三条 CNAME 的观察快照也在该目录；完整区域导出未完成。`bmt.news`、`www.bmt.news`、`next.bmt.news` 三个 Pages 绑定及 DNS 区域尚未删除，浏览器最终操作等待操作时确认；不删除域名注册或新域区域。

## 线上复核与未完成事项

2026-10-02，新域 latest JSON 为 2026-10-02、14 条，生成时间 `2026-10-01T23:29:37.357545Z`；生产 gh-pages 为 `31a0cba37ae643962e26ee4c3d8497e88a0f2e1e`，对应 Pages `07cdba23-711f-4172-92da-1862a24f6e65`。自然 Feed Collection `36956023986`、Schedule Watchdog `36956275851` 和 X/Square 分发记录均 success，未人为重跑 AI 或发测试消息。独立调度器健康指向新仓和新域；实时服务仍是 2.6.0、旧 source_commit `b226b625cf3875b6693e0768d75d88d50b33c08d`，三个现货分片 live、Telegram enabled，不能宣称已从新仓部署。

远端 main 仍无 `realtime/`；本地阶段 3 完整历史仍因旧 Token 撤销未确认而禁止上传，可信 SSH 入口也未恢复。更换 Bot 不等于撤销旧 Token；实时仓、看门狗及 `api.fomobtc.com` 不得提前删除。首次快照三分片 live，随后第三分片出现 warming，不能将瞬时快照当成持续就绪；本次没有重启或修改实时服务。既有 Hyperliquid 降级并未由清理修复，不将健康响应写成全功能 ready。Quick Post 登录后的读写及新 Bot 的自然发送回执仍未独立验收。

编辑前完整 942 项 pytest 通过；文档编辑后品牌扫描把内部资源记录误当公开页面，出现 941 项通过、1 项失败。修正扫描边界，仅排除不会公开部署的 project-docs，保留网站、代码、workflow 和 README 覆盖并增加边界回归；不绕过许可检查，不模糊实际删除资源的名称。

Source commit: 2858290a6db7ec5f6eb38dc5fd30689bbfa90b14（本次文档基线及当前主站生成源）。
Worker version: 日报调度器 9774435b-1c72-4dad-9552-0440e2ab574f，未部署新 Worker；Pages 07cdba23-711f-4172-92da-1862a24f6e65 为核验快照。
Deployment: 实际删除旧 Horizon Pages，已回读；文档无需单独生产部署，旧域 UI 清理和实时迁移尚未执行。
Verification: 旧项目列表与新站/API/调度/实时健康分别核验；普通 xiyu.news 首页 200。扫描边界修复后完整 943 项 pytest、治理与 diff 检查通过，changed-range 和远端检查随 PR 记录，不把运营者报告写成独立回执。
Rollback: 未执行回滚、强推、手工状态分支写入或密钥修改。被删旧项目及部署历史不能自动恢复；现役服务未删除，迁移历史与服务器备份仍保留，不以清理之名扩大删除范围。
