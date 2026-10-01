# 剩余迁移准备与到期分发验证

Issue: https://github.com/ohxiyu/xiyunews/issues/189

本次仅修改过程文档，不上传实时历史、不部署服务器、不改账号权限或 Telegram 群名称。当前 main 为 99594ac28b5918f3192bc62501469bb01c66e802，网站产品来源仍为 PR186 的 3b8f2b5cd82e257783c99501e6494e495bb20ca7，后续文档提交不冒充新生产版本。

20:05 workflow_dispatch 36859488592 的 Square 任务 success，日志 attempted=1、sent=11、remaining=3、attention=0。队列回执 post_id=372593244617888，attempted_at=2026-10-01T20:05:45.314008+08:00，status=sent。到期任务不是仅 health/idle 成功，已经有实际发送和持久化回执；没有人为发送测试内容。

本地实时分支已 merge 最新 main，保存提交 a7edea4b1edfa34ba5fdb7abc3502ca3c1b873fc，旧仓 main 与最新主仓都是祖先。根 942 项 pytest、实时 Python 3.11/3.12 各 61 项、ruff/mypy/compileall/仓库契约及 3 项看门狗 Node 通过。操作清单只在根 project-docs 维护，模块 deployment 作为链接入口，避免两份互相冲突；完整历史仍因疑似旧凭据撤销未确认而禁止推送，原阈值、地址簿、服务单元、nginx 与依赖锁未改。

新增 [服务器迁移清单](../realtime-server-migration.md)，提供原 SSH 与完整 SHA 校验、独立打包/venv、停止唯一实例、SQLite 与环境备份、仅 SOURCE_COMMIT 变更、原子切换、自然回执只读查询、三分片/看门狗验收及经授权回退。Bash 与嵌入 Python 语法通过，没有在服务器执行；[Telegram 品牌草案](../telegram-brand-migration.md) 只提供名字、简介、运维告警对比，等待运营者确认。修正架构中不存在的 src/publishers/ 入口。

Safari 新域 /s/ 仍是原账号验证码登录页，不获取邮件、验证码或私有 cookie；未验证登录后管理操作。已知两份 SSH 配置路径仍不存在，默认 known_hosts 没有目标主机匹配，未猜用本机其他私钥、未关闭主机验证。Access 显示名仍是已准备未确认保存；未伪造完成，也不因为继续执行请求而取消旧历史安全门控。

Source commit: 99594ac28b5918f3192bc62501469bb01c66e802（本次文档基线）；实时本地 a7edea4b1edfa34ba5fdb7abc3502ca3c1b873fc（未推送）。
Worker version: not changed；最近已验证独立调度器 9774435b-1c72-4dad-9552-0440e2ab574f，站点 Pages 216fd183-cd53-4140-a744-ff6b48ff1bd6。
Deployment: 本次无需部署，前序 PR186/188 的生产版本不变；Square 36859488592 为实际到期分发。
Verification: 本次文档分支重新跑完整 942 项 pytest 和治理通过，操作清单 7 个 Bash 代码块及嵌入 Python 语法通过；双版本实时测试如上。精确 changed-range 和远端 CI 随 PR 核验。服务器新仓 SHA、自然 Telegram 回执、看门狗无新增告警和旧仓归档尚未完成。
Rollback: 未回滚、强推、手写生产分支、删除资源或更换密钥；清单的回退命令只有确认后才能执行。
