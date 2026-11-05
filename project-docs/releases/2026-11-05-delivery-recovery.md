# 2026-11-05 自动发推与磁盘恢复

任务：[Issue313](https://github.com/ohxiyu/xiyunews/issues/313)，唯一编辑及整合负责人为当前会话，分支 agent/delivery-recovery。用户授权清理并继续修复、部署既有系统，不增加服务、费用、并行、密钥或更改发送规则。

## 根因和修复边界

系统盘被 actions-gh-pages 在专用 home 中留下的部署 Git 副本占满，执行器日志出现 No space left on device 并离线；196 个超过一天、无进程引用的已核实副本约 20.83 GiB 已清理，磁盘从 100% 降到 44%，约 22 GB 可用，执行器上线并继续积压任务。没有将数据库、AI 缓存、凭据、实时业务目录列为删除目标。

另一个独立故障是成功 Git 检查点没有确认推进 SQLite 的 source_digest，而不是 save_document 丢失该字段。X Queue gate 遇到本地新回执和远端中间 pending 快照后判为冲突并停止，未调用 X。比对证实两份队列仅 10 月 27 日同一任务的 status/detail/tweet_id 三字段不同：本地保留 HTTP 201 成功回执和 tweet_id 2114869539422998782，Git 仍是 pending。其余正文、哈希、任务身份、尝试时间、计划及 10 月 20–26 日的十四条 sent 记录完全一致。

成功普通 Git push 后用精确 payload/digest CAS 确认检查点，失败 push 不确认；X 无文件差异时仍执行普通 push，防止把上次未发布 commit 当成已完成。仅同一任务、同次尝试、正文哈希正确的远端 pending → 本地 sent 数字 ID 允许领域恢复；未知、失败、更换正文/计划/尝试、矛盾 ID 仍保留双方并停止。其他文档不自动合并。Square 共享检查点也补成功确认，不增加回执自动合并。

部署回收模块只匹配专用 home 中 actions_github_pages_13位时间戳，默认保留最近 24 小时；核对目录归属、设备、真实 .git、非挂载点、进程 cwd/fd、锁和 inode，拒绝软链接根与不明目录。合法任务即使业务快照损坏也执行有界清理，同时保留损坏工作区供排查。维护 timer 与每任务 hooks 共用锁。脚本刷新采用已安装 drop-in 核对及原子替换，不重启忙碌执行器，不改运行环境或资源限制。

## 生产备份与验收计划

补充顺序保护：门控发现本地恢复状态尚未进入 Git 时也唤醒正常流程，在任何新计划与七天历史清理之前先检查点保存；确认的旧成功 ID 因而先进入 Git 可追溯历史，再按原规则正常归档。新增回归验证门控唤醒、先审计后归档且不发送消息；最终 X/Square/恢复定向 78 项通过。取消两次尚未进入发送步骤、仍用旧冲突代码的 X 积压运行 41959357534 / 41961757577；未取消采集、日报或网站发布。

恢复前已用 SQLite online backup 生成一致备份并检查完整性：/home/xiyunews-runner/state/recovery-backups/delivery-20261105T031411Z/publication.sqlite3，目录 0700、文件 0600。不手写 x-queue 或其他产物分支，不清空历史回执；通过合并后的正常 X Distribution 工作流恢复，仅允许今天按原门控到期的自然任务，不补过期历史、不发测试、不重试 unknown/failed，不为验收真实调用 AI。

## 五阶段状态

- 代码：已实现，待提交与远端检查。
- 测试：完整 Python 1139 passed / 4 个既有 skipped；Square 无差异推送补充后，88 项最终定向回归通过，治理、shell 语法、差异检查通过。真实本地 bare Git/SQLite 验证失败 push 保留 dirty、无差异重推及成功确认；坏业务快照保留而旧副本仍维护。远端完整 CI（包括 realtime 双 Python、网页和构建）待执行。
- 合并：待 PR 检查通过且同步 main。
- 部署：一次性清理已完成，新代码与维护脚本尚未部署。
- 生产验收：执行器恢复在线、备份完整；新队列恢复、自动清理与最新网站待验收。

Source commit: 当前基线 f493c4340b45bced5c75fff6ebcae4c3c78ee9c9，修复合并 SHA 待记录。

Worker version: 待刷新，本次不直接修改 Worker。

Deployment: 合并后通过既有正常工作流运行；仅将准确合并 SHA 的受审维护脚本原子刷新到原服务器。

Verification: 不把执行器在线当成已恢复发推；后续记录正常工作流、队列回执、SQLite/Git 一致性、磁盘和公开页面实际结果。

Rollback: 不自动回滚；失败保留本地与 Git 双方及备份，禁止通过重置队列重发未知结果。
