# 2026-11-05 自动发推与磁盘恢复

任务：[Issue313](https://github.com/ohxiyu/xiyunews/issues/313)，唯一编辑及整合负责人为当前会话，分支 agent/delivery-recovery。用户授权清理并继续修复、部署既有系统，不增加服务、费用、并行、密钥或更改发送规则。

## 根因和修复边界

系统盘被 actions-gh-pages 在专用 home 中留下的部署 Git 副本占满，执行器日志出现 No space left on device 并离线；196 个超过一天、无进程引用的已核实副本约 20.83 GiB 已清理，磁盘从 100% 降到 44%，约 22 GB 可用，执行器上线并继续积压任务。没有将数据库、AI 缓存、凭据、实时业务目录列为删除目标。

另一个独立故障是成功 Git 检查点没有确认推进 SQLite 的 source_digest，而不是 save_document 丢失该字段。X Queue gate 遇到本地新回执和远端中间 pending 快照后判为冲突并停止，未调用 X。比对证实两份队列仅 10 月 27 日同一任务的 status/detail/tweet_id 三字段不同：本地保留 HTTP 201 成功回执和 tweet_id 2114869539422998782，Git 仍是 pending。其余正文、哈希、任务身份、尝试时间、计划及 10 月 20–26 日的十四条 sent 记录完全一致。

成功普通 Git push 后用精确 payload/digest CAS 确认检查点，失败 push 不确认；X 无文件差异时仍执行普通 push，防止把上次未发布 commit 当成已完成。仅同一任务、同次尝试、正文哈希正确的远端 pending → 本地 sent 数字 ID 允许领域恢复；未知、失败、更换正文/计划/尝试、矛盾 ID 仍保留双方并停止。其他文档不自动合并。Square 共享检查点也补成功确认，不增加回执自动合并。

部署回收模块只匹配专用 home 中 actions_github_pages_13位时间戳，默认保留最近 24 小时；核对目录归属、设备、真实 .git、非挂载点、进程 cwd/fd、锁和 inode，拒绝软链接根与不明目录。合法任务即使业务快照损坏也执行有界清理，同时保留损坏工作区供排查。维护 timer 与每任务 hooks 共用锁。脚本刷新采用已安装 drop-in 核对及原子替换，不重启忙碌执行器，不改运行环境或资源限制。

## 生产备份与验收计划

补充顺序保护：门控发现本地恢复状态尚未进入 Git 时也唤醒正常流程，在任何新计划与七天历史清理之前先检查点保存；确认的旧成功 ID 因而先进入 Git 可追溯历史，再按原规则正常归档。新增回归验证门控唤醒、先审计后归档且不发送消息；最终 X/Square/恢复定向 78 项通过。取消两次尚未进入发送步骤、仍用旧冲突代码的 X 积压运行 41959357534 / 41961757577；未取消采集、日报或网站发布。

X 的 workflow_run 入口补齐 success 条件，避免失败/取消的采集或出版任务继续派生无用分发；与现有 Square 入口保持一致。原五分钟 Worker、小时备份和手动正常入口不变，不放宽门控或截止时间。最终应用完整 Python 为 1140 passed / 4 个既有 skipped。

生产旧任务日志还证明源码 fetch 用时 8 分 34 秒，挤满原 X 十分钟总时限；X 总时限改为二十分钟，仅增加下载/检查点余量，不变更业务时限与 CPU/内存。读取日报改用已认证 GitHub API 获取 gh-pages 单个状态 JSON，避免为一个文件下载整个出版分支。实际私库只读请求通过；真实工作流 shell 的合法/坏 JSON、错误结构和 API 失败回归均须通过，失败保留原文件并停止，不能当作空刊期。

恢复前已用 SQLite online backup 生成一致备份并检查完整性：/home/xiyunews-runner/state/recovery-backups/delivery-20261105T031411Z/publication.sqlite3，目录 0700、文件 0600。不手写 x-queue 或其他产物分支，不清空历史回执；通过合并后的正常 X Distribution 工作流恢复，仅允许今天按原门控到期的自然任务，不补过期历史、不发测试、不重试 unknown/failed，不为验收真实调用 AI。

## 五阶段状态

恢复中的生产者/消费者边界：SQLite 已保存今日日报，但 Git 快照尚为昨天。X 生产投递改为只解码本轮经 GitHub 鉴权恢复的出版文件，不从生产者 SQLite 合并未发布选稿或修订；队列回执仍保留其独立持久状态。真实 SQLite + mock publisher 回归验证：昨天的 Git/今天的本地草稿不发帖，同日 Git 旧修订/本地新草稿仅发送 Git 已发布原文，生产者草稿保持原样；不改变编辑、生成和去重规则。

下载反复重来原因已确证：本轮 web job 在 05:20:17Z 报 RPC failed; curl 92 HTTP/2 stream ... CANCEL、unexpected disconnect、early EOF，随后等待 11 秒重新下载，遗留两个各约 15 MB 未完成 pack。七份相关工作流通过进程级 GIT_CONFIG_COUNT/KEY/VALUE 固定 http.version=HTTP/1.1，避免该 HTTP/2 路径；不写系统/global Git 配置，不改变鉴权、TLS 验证或凭据。仍保留正常下载失败与超时防护，实际远端结果待验收。

HTTP/1.1 仍在 governance127069138126 的完整文档 checkout 中出现 curl18 transfer closed / early EOF，治理校验尚未执行；协议切换不能当作解决了全部下载故障。完整 CI checkout 因此先读取应用目录，再以每批四个 Git blob、单次 180 秒、最多三次重试恢复 project-docs，最后 disable sparse-checkout，保持同一 HEAD 与完整真实文件/权限/符号链接，之后才执行所有原检查。文档对象缓存按 Git blob SHA 校验后导入 Git，128 MiB 上限，坏对象/不安全路径停止；重复任务无需再次下载相同截图。仅此步骤短时提供只读 job token，经进程环境传给 Git，不进入命令参数、缓存文件、日志或后续测试。真实 bare Git 回归验证一次失败重试、完整工作树、第二次全缓存、坏缓存拒绝与 commit 不变。

最初的显式 Git blob fetch 未设置 fetch.negotiationAlgorithm=noop，在 GitHub 的 promisor remote 上立即失败；本地 bare 仓库测试不能覆盖此服务端差异。已用真实公开 actions/checkout 部分克隆复现：默认协商报 bad revision / did not send all necessary objects，改为与 Git 内部按需对象读取一致的 noop 协商后成功。增加该参数，错误输出仅分类固定标记，不打印原始 Git stderr 或凭据。实际私库完整 CI 仍须重新通过。

私库 web127076190367 的完整工作树恢复已在 05:49:51–05:50:26Z 成功并进入 npm 检查；全历史 governance 仍在对象批次失败。批次读取进一步采用与 Git 内部按需读取一致的协议 v2/noop/--stdin 路径，并避免自动后台维护；真实 GitHub 全历史公开部分克隆的四对象 stdin 读取通过。错误只保留末尾有界诊断，先移除原令牌、Basic 编码、所有 URL 和 Authorization 文本，避免隐藏实际兼容问题或暴露凭据。最终完整私库 CI 待通过。

有界诊断确证 governance 失败是 HTTP400 Duplicate header: authorization：checkout 默认已保留鉴权，恢复步骤重复注入了第二份头。governance/test/realtime 步骤改为不注入令牌，直接使用该 job 的 checkout 凭据；web 的 persist-credentials:false 保持不变，只有其恢复步骤短时注入只读令牌。测试同时覆盖空令牌与显式短时令牌两种路径。此处为新增恢复脚本的适配缺陷，不能归因于原业务或网络。

今日日报41964081010 的内容生成与 Telegram 正常发送已 success，但 Git 出版步骤在 04:53Z 触及旧三十分钟时限；Git 快照仍为 11 月 4 日，不能把生成成功当成网站更新。复查发现重试因本地已有选稿而直接跳过页面，工作区清理后无法恢复丢失静态产物。重复出刊路径因此增加缺失产物恢复：完整保留已有正文/顺序/时间/回执，复用持久报告中的原候选统计，仅以现有模板恢复双语页面/API/归档及事件页，不调用信源、AI、行情或任何推送渠道。已丢失且未持久保存的行情/今日脉络不重新生成、不虚构；有完整产物时仍完全跳过。新增真实文件回归验证两种语言、完整正文、状态字节不变、第二次重试不修改产物，所有外部调用均设为失败断言。

正常 Cloudflare41959357519 在 2026-11-05 03:35–04:05Z 达到三十分钟总时限。两次 checkout 已完成，npm 安全审计通过；Ruby 缓存下载始终 0 字节后放弃，转在线 bundle install 又触及总时限，未进入生产替换。不能将其描述为页面代码失败或已部署成功。CI edge 与正式发布改用既有服务器的 Ruby 工具依赖缓存，按 ci/producer、Ruby 3.3 ABI 和锁文件 SHA 分路径，冻结依赖、优先离线安装；GitHub 托管环境仍保留原缓存方式。不修改 Gemfile/Gemfile.lock、CPU/内存、套餐或发布内容，不复用 PR 的渲染缓存作为生产输出。

主仓库受跟踪内容约 28.48 MB，其中 project-docs 约 22.57 MB；运行任务无需下载这些截图。X 只下载 src/data，watchdog 只下载 src；CI 路径判断保留完整 Git 历史/差异元数据，仅下载 scripts；CI edge 与 Cloudflare 下载全部实际构建输入目录。完整 Python、网页、realtime 和治理检查的 checkout 范围不减，出版快照仍完整且固定 SHA，安全审计和渲染检查不跳过。

同样缩小 Square 与采集后恢复检查的源码下载；Square 仅需同步刊期时通过已认证 API 读取单个 JSON（今日/指定刊期均保持原语义），坏数据或接口失败保留旧快照并停止。X/Square 总时限二十分钟、两个恢复检查十分钟，为下载提供余量但不改变 Cron、恢复宽限或发送截止。治理仍完整读取仓库及截图链接，因保留完整下载给予二十分钟上限，构建本身仍为三十分钟。已用原锁文件下载 99 个 Linux gem 归档，分别校验 99 项 SHA-256 并预热工具缓存；这不能代替 Linux 的实际安装/构建验收。

日报及实际采集任务也保留全部运行输入目录，仅省去不会被应用读取的内部截图与独立 realtime 目录，固定窗口、来源、内容生成及部署逻辑不变。完整测试中的已有工作流结构断言随单文件读取和新任务时限同步，仍验证先门控、再读刊期、再安装依赖；新的真实 shell 回归覆盖合法数据、坏 JSON、错误结构与接口失败。

今日日报 41959914727 在等待同一并发组时被后续采集替换取消；原调度已重新派发 41964081010。旧采集 41945229392 的 collect 已 success，仅 recover-daily 仍排队且因 always 条件普通取消无效；确认未执行后使用 workflow force-cancel 结束剩余检查，成功采集结果保留。昨日 watchdog41857789335 也在未执行时取消。此操作不涉及强推、回滚或状态分支写入。另取消未进入发送步骤的旧 X41962554645 / 41964088322，等待修复代码后经正常入口恢复，不测试发帖。

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
