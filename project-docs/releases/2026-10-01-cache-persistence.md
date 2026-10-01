# 迁移验收补充：缓存持久化权限失败

Issue: https://github.com/ohxiyu/xiyunews/issues/177

2026-10-01 14:30（上海）调度器自然触发 Feed Collection 36825148528，事件 workflow_dispatch；采集、分析缓存备份和事件产物发布步骤成功，但 Persist staging cache to branch 失败，因此整个运行为 failure，不记为全链路成功。原因是原脚本 checkout -B 从 main 生成提交，带入更改后的 .github/workflows/deploy-docs.yml；GITHUB_TOKEN 没有 workflow 写权限，远端拒绝该推送。不是私有仓库的 Contents 读取或 Actions 派发失败。

改为独立临时 Git index，从 staging-cache 原有树生成只更改 data/staging-items.json 和 data/analysis-cache.json 的子提交，保留所有其他文件及父历史；不存在远端分支时生成仅含缓存文件的根提交。缺少可选分析缓存保留原值，缺少 staging 文件跳过；无法读取远端和并发非快进推送明确失败，不 force、不扩大权限、不手动改生成分支、不改变主工作树、不运行 AI。

离线真实裸仓 6 项测试验证旧 workflow 不变、父历史保持、新建仅数据分支、幂等、缺少缓存和远端错误；完整 937 项 pytest、治理、bash 语法与 diff 检查通过。远端 CI 结果待 PR 最终补充。合并后等待下一次自然运行，不用带真实 AI 的手动重跑充当测试。

品牌 XML PR176 已合并为 d115e7debbf70e8d4dfe6629592f283f5783e746，Deploy Docs 36825452488 成功，产物 09a14bf7c435a915f911c57e0b5f280331d446a9；Pages 与线上 sitemap/feed 仍待最终回读。主站已上线，301 和新域后台仍未完成，realtime 历史疑似凭据撤销未确认，不推送历史、不归档旧仓。

Source commit: 待本修复合并；现主站品牌 XML 源为 d115e7debbf70e8d4dfe6629592f283f5783e746。
Worker version: dd126dda-3c13-4e8d-b582-e2550c08cb98，独立调度器保持。
Deployment: 缓存修复待正常 main workflow；不手动写 gh-pages 或 staging-cache。
Verification: 6 项离线回归、完整 937 项 pytest 与治理通过，生产自然缓存成功尚未验证。
Rollback: 未执行回滚，未删除缓存和既有资源。
