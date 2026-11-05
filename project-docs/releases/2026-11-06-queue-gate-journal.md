# 2026-11-06 刊期日志与轻量门控兼容性

[Issue325](https://github.com/ohxiyu/xiyunews/issues/325)，唯一编辑/生产整合负责人为当前会话，复用work/xiyunews-edition-continuity，agent/queue-gate-journal分支。前置PR320/323已恢复3日14条、持久刊期和完整正常发布；证据PR324转为Draft，待本回归修好后统一归档。

## 问题与修改

正常发布42089412376成功后，下游X42093318742/job127476765584与Square42093318787/job127476765746均在安装依赖前的轻量gate报ModuleNotFoundError:pydantic，发送步骤没有执行。原因是PR320的PublicationState构造器捕获当前daily时，_remember_edition导入DailyFeedState，间接加载Pydantic。先前完整环境回归通过，但遗漏了这些明确声明stdlib-only的真实入口环境。

存储层现在仅使用标准库校验规范日期、JSON条目列表及可规范序列化的JSON，并保存已经由producer验证的原始快照及摘要；恢复消费者继续完整DailyFeedState验证。没有删减恢复校验、改写原稿或为轻量gate增加全套依赖，也不改workflow发送策略、凭据、来源、Cron、资源上限或实时服务。

新增两个真实python -S子进程回归，分别执行X/Square门控，关闭site-packages且不继承私密运行环境；使用隔离的升级前SQLite（预存完整daily/队列但无刊期表），验证构造器能创建日志、保留原始JSON和全部当期/回执。两个用例在修复前失败，修复后与原持久状态/跨日恢复定向用例共20项通过；不真实调用模型或消息渠道。

## 五阶段

- 代码：完成，移除存储层对领域模型库的反向依赖。
- 测试：20项定向及完整Python1184 passed/4既有skipped通过，治理与差异检查通过；适用远端CI待完成。
- 合并：待同步main且必需检查通过后正常合并。
- 部署：合并后正常workflow读取新main验证轻量gate；不直接改服务器环境或安装系统依赖。
- 生产验收：待真实gate通过及原稿/日志/回执保护核对，不发送测试新闻或补发历史。

Source commit: 基线dca841fd0e112cbec3917f382682acb41fb800bf；本修复合并后回读实际runtime代码SHA。

Worker version: 网站当前05b8d129-2253-4759-b4ef-441bc6bc9708、artifact82929893a36f9e1a4dfde5c9b6df2f8048df3cb9；本次仅Python运行入口兼容，不修改Worker或网页资产。

Deployment: 仅正常main工作流，不手写生成分支、手改回执或持久运行Secrets。

Verification: 日报与完整publisher已经恢复；不能把本次渠道门控依赖回归留作完成状态。

Rollback: 不自动回滚或整库恢复，保留已有刊期/回执及Git历史，不重发历史消息。
