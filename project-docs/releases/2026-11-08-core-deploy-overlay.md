# 核心站生产素材覆盖修复

Issue: https://github.com/ohxiyu/xiyunews/issues/345
Depends on: https://github.com/ohxiyu/xiyunews/pull/344

唯一编辑与整合负责人为本聊天Codex；分支 agent/core-deploy-overlay，从2694f7d创建。用户明确授权整站精简后直接上线。

主应用完整CI42471824413通过：1243 passed/4既有skipped；审计、135个Worker测试、Node、3.11/3.12独立服务、真实Jekyll渲染90期和部署dry-run通过。PR344已合并2694f7d，Deploy Docs42472757852成功。生产覆盖循环遗漏 `_sass` 可选目录判断，CI原循环带判断；上线前复核发现此差异，尚未宣称新站上线。

本修复将CI和生产的素材覆盖收敛为同一个标准库函数。先验证必需目录和页面，再复制；可选_sass缺失允许，存在时复制；保留快照的API/历史，不读取AI或发送渠道。新增四项回归覆盖缺失/存在可选目录、必需输入缺失及同一调用路径。Deploy Docs监听该脚本改动，合并后自动重新触发完整发布链。

Code: complete
Tests: complete — CI42473135016, 1247 passed / 4 existing skipped
PR merged: complete — PR347 / eeeae8b
Deployed: complete
Production verified: complete

Source commit: eeeae8bf067accfe16be0341559cc2c50eab5777
Worker version: cf14285d-6216-479b-91a3-d3f2a731351f
Deployment: https://github.com/ohxiyu/xiyunews/actions/runs/42474636511 — success
Verification: 2026-11-08T11:21:35.625Z; shared overlay executed in production and source/artifact/Worker match
Rollback: 按用户授权通过同一流水线切换到已验证源提交；不手改生成分支、回执或realtime。

最终范围、正式截图、状态未改动证明和验证边界见[核心站上线记录](2026-11-08-core-site.md)。
