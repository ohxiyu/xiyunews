# 2026-11-06 刊期日志与轻量门控兼容性

[Issue325](https://github.com/ohxiyu/xiyunews/issues/325)，唯一编辑/生产整合负责人为当前会话，复用work/xiyunews-edition-continuity，agent/queue-gate-journal分支。前置PR320/323已恢复3日14条、持久刊期和完整正常发布；证据PR324转为Draft，待本回归修好后统一归档。

## 问题与修改

正常发布42089412376成功后，下游X42093318742/job127476765584与Square42093318787/job127476765746均在安装依赖前的轻量gate报ModuleNotFoundError:pydantic，发送步骤没有执行。原因是PR320的PublicationState构造器捕获当前daily时，_remember_edition导入DailyFeedState，间接加载Pydantic。先前完整环境回归通过，但遗漏了这些明确声明stdlib-only的真实入口环境。

存储层现在仅使用标准库校验规范日期、JSON条目列表及可规范序列化的JSON，并保存已经由producer验证的原始快照及摘要；恢复消费者继续完整DailyFeedState验证。没有删减恢复校验、改写原稿或为轻量gate增加全套依赖，也不改workflow发送策略、凭据、来源、Cron、资源上限或实时服务。

新增两个真实python -S子进程回归，分别执行X/Square门控，关闭site-packages且不继承私密运行环境；使用隔离的升级前SQLite（预存完整daily/队列但无刊期表），验证构造器能创建日志、保留原始JSON和全部当期/回执。两个用例在修复前失败，修复后与原持久状态/跨日恢复定向用例共20项通过；不真实调用模型或消息渠道。

## 五阶段

- 代码：完成，移除存储层对领域模型库的反向依赖。
- 测试：20项定向及完整Python1184 passed/4既有skipped通过，治理与差异检查通过；最终head fab84cd637996859efe5ddcca48ce6af4da30fd2的[CI42098874279](https://github.com/ohxiyu/xiyunews/actions/runs/42098874279)所有适用检查通过，其余按路径正常跳过。
- 合并：PR326于2026-11-05T20:08:52Z合并cf878a8cc9023c7aec17e9050f293e368fe14afb；合并树与检查head相同且为origin/main祖先。
- 部署：两个正常workflow均实际checkout新main cf878a8c并成功执行；没有直接修改服务器环境或给系统Python安装依赖。
- 生产验收：两真实gate、原稿/日志/回执保护均通过；X发送步骤跳过、Square实际attempted=0/sent=0，没有发送测试新闻或补发历史。五阶段完成。

Source commit: runtime cf878a8cc9023c7aec17e9050f293e368fe14afb；基线dca841fd0e112cbec3917f382682acb41fb800bf。

Application PR: [PR326](https://github.com/ohxiyu/xiyunews/pull/326)。

Worker version: 网站当前05b8d129-2253-4759-b4ef-441bc6bc9708、artifact82929893a36f9e1a4dfde5c9b6df2f8048df3cb9；本次仅Python运行入口兼容，不修改Worker或网页资产。

Deployment: 仅正常main工作流，不手写生成分支、手改回执或持久运行Secrets。

Verification: 日报、完整publisher和两个真实轻量门控均已恢复并分别验收，详见下文。

## 真实运行证据

仅重试前述两个失败job，保留原workflow及输入。两个workflow都显式checkout main，实际日志中均为cf878a8cc9023c7aec17e9050f293e368fe14afb；不把原run.head_sha仍为dca841fd误当作旧代码仍在运行。

- X42093318742新job127502370202，2026-11-05T20:09:21Z–20:12:29Z成功；20:10:52Z回读新代码SHA，20:12:21Z轻量gate为work=false、attention=0，Plan and send with remote checkpoints为skipped，未加载发送依赖或调用渠道。
- Square42093318787新job127502372211，20:12:32Z–20:14:00Z成功；20:13:44Z回读新代码SHA，gate为sync=true/due=false/remaining=0/attention=0/unscheduled=0，正常上游触发要求同步，但旧5日期号不冒充本日6日。最终报告status=ok、date=2026-11-06、attempted=0、sent=0，没有发布历史内容。

运行后只读核对主库及备份integrity_check=ok，刊期3日14条/5日13条摘要有效；daily、X、Square三份规范JSON与恢复前仍逐字节一致，已确认X回执2条、Square回执697条全部不变，无新增确认或状态变更。网站仍为dca841fd/82929893、Worker05b8d129-2253-4759-b4ef-441bc6bc9708：该标记描述网页/Worker构建输入，本修复是独立Python工作流入口，未为无变化的网页强制重发版本。下一次自然定时日报及实际当日渠道发送尚未发生，不当作本次已验证。

Rollback: 不自动回滚或整库恢复，保留已有刊期/回执及Git历史，不重发历史消息。
