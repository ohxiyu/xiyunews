# 完整历史整合恢复与项目统一

Issue: https://github.com/ohxiyu/xiyunews/issues/172

运营者于2026-10-02确认原Bot Token已经撤销，并要求两个仓库和项目统一为xiyunews。之前保留历史的上传门槛已解除；不输出、不调用已撤销凭据，不重写或压缩原历史。原仓main `7807126d8c7cdb51e18f0b91ba27f500271f9f08` 已通过 unsquashed subtree 导入本地，本次同步前序主仓 `3e7885ac5fba2354adaa65abd2e05e2d14aa5b98`，以 merge commit 合并 PR，随后验证旧仓祖先。

根 AGENTS 优先，主应用与 realtime 仍独立依赖、src、数据库、运行进程、Telegram 目的地。版本保持2.6.0，不改阈值、地址簿、systemd、nginx或信源；主站 UI 不变。项目管理名称统一为xiyunews，内部服务路径与Python命令不是本阶段改名范围。Cloudflare最终单项目需要迁移到具备静态资源和Cron的Worker，不把仓库合并当成已经完成网站/调度/看门狗切换。

运营者同时确认旧域三绑定和DNS区域删除，已执行Cloudflare区域删除；三个Pages绑定及列表回读正在进行，最终实际状态另行补充。没有删现役Pages、调度器、看门狗、旧实时仓或服务器。原可信SSH入口尚缺；新仓实际服务器SHA、三分片、自然message_id和看门狗都尚未验收，旧仓不得提前退役。

Source commit: 3e7885ac5fba2354adaa65abd2e05e2d14aa5b98（同步的远端主仓基线）；旧仓祖先7807126d8c7cdb51e18f0b91ba27f500271f9f08。
Worker version: not changed；日报调度器9774435b-1c72-4dad-9552-0440e2ab574f，实时看门狗最近记录55671d87-29c2-4225-8bdf-176cb4712ed3，本次未部署。
Deployment: 阶段3仅代码与完整历史整合，尚未服务器发布或Cloudflare统一切换。
Verification: 根943项pytest和治理通过；实时首次各60项通过/1项失败，独立仓夹具缺合并后共享部署清单，修正为monorepo布局后Python3.11/3.12各61项、ruff/mypy/compileall/契约及3项看门狗Node均通过。src、config、requirements.lock、systemd和nginx的Git对象与旧main完全相同，远端CI及新main祖先仍须实际PR核验。
Rollback: 未执行回滚、强推、清数据库或生产状态分支写入；旧运行服务及备份继续保留。
