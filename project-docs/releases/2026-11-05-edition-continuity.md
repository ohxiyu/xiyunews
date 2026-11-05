# 2026-11-05 历史漏期与跨日静态恢复

[Issue319](https://github.com/ohxiyu/xiyunews/issues/319)，唯一编辑/生产整合负责人为当前会话，agent/edition-continuity，独立work/xiyunews-edition-continuity。用户授权补齐漏发日报并防复发；不重新选稿、不补历史消息，不改信源、时区窗口、Cron、密钥、套餐、实时规则或资源上限。

## 核查结果与根因

以当前main ffc4dc2464f955ff644798bc38effbdb728b3aaa和出版e1bb91986515eb4fa95bc23330c5c3c17ff37333为基线，近14天出版目录仅2026-11-03缺失。11月1日13条、2日12条、4日11条、5日13条都有JSON/双语片段。原3日生成41545473461于11月2日23:26:41Z启动，23:33Z在Deploy to GitHub Pages失败；内部报告已生成14条、560候选且双语生成完成。两次补跑41549660919/41553340493内部识别已保存14条，旧代码因edition_already_published直接跳过页面；任务失败但没有静态恢复。首次底层部署日志因服务读取失败暂不能获取，不凭推测声称AI失败或特定文件系统错误。

PR314修复了本期“有选稿但没产物”的重试，PR316修复了事件目录被旧快照覆盖；它们不保存所有历史刊期。daily文档被下一期覆盖，恢复门控只关心当前日期，因而3日留作永久缺口。此次增加按刊期保存选稿，并在现有生产发布前检查和恢复历史，不接入新定时系统。

## 数据恢复依据和限制

delivery-20261105T031411Z的只读SQLite备份保留4日daily，其dedup_history中14条恰落在3日固定窗口。14条均有完整中文/英文正文和背景；数量、完整来源分布与分类分布和原3日报告完全吻合。Telegram显示名中的@仅做比较时的规范化，不改来源。当前较新备份只剩9条，未将不足集合当成完整选稿。

旧选稿通过只读校验后进入新刊期日志，再通过正常Actions生成页面。原同分条目的相对排名已丢失，采用保留分数及去重记录顺序，明确不声称原始排名完全还原；正文、来源、发生/采集时间不重写，原窗口不改。已有12个事件引用中9个缺节点也用已合并的稳定ID恢复机制补齐，分类未知保持保守标记，不重新做AI关联。未保存的原行情/今日脉络省略，不用现在行情冒充历史。

## 修复设计

publication_editions独立保存每次选稿的规范JSON和SHA-256，当前daily替换和旧/新刊期记账在同一SQLite事务完成；升级也捕获当前选稿。历史选稿不会随工作区清理、72小时原稿保留或两天去重窗口消失，校验和纳入完整性检查。没有删除既有表、队列、回执或整库恢复。

日报、采集、Deploy Docs在正常publish前执行edition_recovery：恢复Git中已存在的历史入口文件，导入受校验的历史选稿日志，逐个检查JSON、双语Markdown、双语片段、条数/原文指纹与索引。只渲染已保存但缺产物的刊期，不访问AI、信源、行情或消息渠道，历史恢复不改current daily或X队列。晚补的旧版API不会覆盖更新的latest.json；索引/feed/sitemap从全部已有归档重建。选稿日志同时导出到Git出版快照，便于服务器丢失后的恢复。

旧数据的一次性兼容只接受现役或已有备份中的完整留存记录，要求唯一候选集合、固定窗口、原报告数量/来源/分类一致；缺事实或歧义直接停止，不猜稿、不降低门槛。未来原始生成失败且根本没有选稿仍由原当日恢复预算处理，这个补偿器不会无限重跑付费AI；其保证范围是“已生成选稿持久保存并在下次正常publisher补齐缺失静态产物”，并非平台永不故障。

## 五阶段与验收

- 代码：已实现。
- 测试：最终完整Python1182 passed/4既有skipped，8项定向真实CLI/跨日、幂等、真实Git、latest保护及构建退出回归通过；治理、编译和差异检查通过。最终head bda3a950614dc8018d20801240f651d8c7ad937a的[CI42061327289](https://github.com/ohxiyu/xiyunews/actions/runs/42061327289)全部通过，包括test/web/edge-build和realtime双Python兼容性检查。edge-build下载期间记录了early EOF并由既有动作重试恢复，最终26分20秒成功；没有跳过检查或放宽时限。
- 合并：[PR320](https://github.com/ohxiyu/xiyunews/pull/320)于2026-11-05T17:25:36Z合并，88da72c5465a223160a51c805a7d3ce7ec4fbae8；合并树与已检查head一致，且为origin/main祖先。
- 部署：待正常Deploy Docs，不手写gh-pages。
- 生产验收：待3日14条、近14天连续性、双语页面/日期选择/加载更早、事件锚点及5日正文/消息队列不变验证。

## 正常发布的恢复证据

[Deploy Docs42074503443](https://github.com/ohxiyu/xiyunews/actions/runs/42074503443)第一次执行在2026-11-05T17:40:11Z输出：从delivery-20261105T031411Z导入3日14条、补齐五个入口文件，ai_calls=0、channel_calls=0。它已成功提交出版快照c23e9014ee7ea3bde869e5066aa82e0628dce65b，但在最后确认检查点时达到20分钟时限，整个任务cancelled，不能记为完整成功。随后仅重试该正常发布任务；另外启动现有统一Cloudflare工作流发布已经完整校验的快照，没有手写出版分支或从本地上传产物。

第一次执行后的只读核对：主数据库和写入前备份integrity_check均为ok，publication_editions包含3日14条、5日13条且摘要校验通过；daily、x_queue、square_queue三份规范JSON与恢复前字节一致。新出版快照中12个事件引用及HTML节点全部存在，api/latest.json与基线e1bb9198及前一出版fdf5107f逐字节一致，完整文件SHA256仍为abf1cef3296611beb4f50510a79467080fa6b06e5c27faa8ee226ffd887e99ce。临时验收脚本最初混用了Python默认空格与JavaScript紧凑JSON的items摘要，已改为对照原始快照独立计算的紧凑摘要；文件逐字节比较也独立通过，没有把脚本断言失败算作通过。

部署入口适配：Deploy Docs已将出版快照检出到current-site，应用根不一定有origin/gh-pages；恢复器使用该独立检出的准确HEAD读取历史，日报/采集则固定origin/gh-pages SHA。只恢复近期15天及日志所需日期，避免逐个下载整站多年历史；不覆盖本轮已生成文件。真实独立Git仓库回归覆盖根目录无远端ref、第二checkout读取和日期过滤。

真实出版输入在服务器隔离目录完成完整静态渲染：仅修复3日5个缺失入口文件、14条正文，API latest字节保持不变（SHA256 abf1cef3296611beb4f50510a79467080fa6b06e5c27faa8ee226ffd887e99ce）；主数据库以mode=ro/query_only读取，选稿日志仅内存实现，外部调用均设为失败断言。没有向生产或渠道写入该演练输出。

中间head02eb7ea1的web检查达到15分钟总时限。日志确认npm audit通过、类型检查完成、135项Worker测试全部通过；wrangler types从15:46:22到15:51:46才退出，最终dry-run在15:52:41测试后到15:58:18取消仍未退出。检查锁定Wrangler代码发现匿名统计请求和banner版本提示请求都会创建网络连接，后者的Promise.race只限制显示等待，并不取消底层请求。只关闭统计的本机实测仍有退出延迟，不能把原因全归于统计；同时设置进程内WRANGLER_SEND_METRICS=false及WRANGLER_HIDE_BANNER=true，避免这两类非必要请求。只影响构建CLI，不修改systemd环境、Worker vars、业务健康/费用统计，不删减任何安全检查或测试，不放宽时限。最终完整CI须重新通过；不将中间取消状态当通过。新增检查断言最初未包含既有npm run audit写法，已修正后重跑，未将失败断言视作通过。

Source commit: 88da72c5465a223160a51c805a7d3ce7ec4fbae8（PR320）；基线ffc4dc2464f955ff644798bc38effbdb728b3aaa。

Worker version: not changed；只读基线ba1bf907-6399-476b-b437-a8bcda0ef199，正常部署后回读。

Deployment: 合并后由正常Deploy Docs写出版分支，再自动统一Cloudflare发布，不重跑历史采集或渠道。

Verification: 2026-11-05已完成真实备份只读恢复演练；写入前online backup edition-20261105T151912Z完整性ok，daily散列0b73b6d5b4f3b094830b044dfb51be2f2d07dda59ac7cd99217e138c4ea8fd39、X散列12ff4d09a4cd4bea74562979b7e101b946b5996ec712fc5975b8adc598dae5ee、Square散列8ba81d5d2cba01ec0565358679079e6d410bf106c86cf8703824ab9b95194d55。正式补齐尚待。

Rollback: 不自动回滚或恢复整库；保留online backup和Git历史，冲突保留双方并停止，不清回执、不重发消息。
