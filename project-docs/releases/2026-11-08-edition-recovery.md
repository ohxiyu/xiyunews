# 2026-11-08 当期日报补跑

[Issue333](https://github.com/ohxiyu/xiyunews/issues/333)，本聊天Codex唯一执行与整合负责人，
分支agent/edition-20261108-recovery-evidence，隔离快照work/edition-20261108-recovery-evidence。
用户明确要求“补上今天的日报”，授权补跑当前刊期及既有正常发布/分发流程。

## 运行范围

2026-11-08 14:05 Asia/Shanghai核对：main7ffe3ebceddf6e026da4d5eddbe3bb9a4dec8f14
已启用硅基流动Qwen/Qwen3.5-27B并完成真实Actions连通验证；gh-pages状态与正式域首页
仍为2026-11-05，没有今日已发布刊期。未把health/ready或诊断成功当作日报恢复。

通过现有main工作流启动
[Daily42453408651](https://github.com/ohxiyu/xiyunews/actions/runs/42453408651)，
daily-summary job128647225233，显式参数：

- edition_date=2026-11-08，窗口[2026-11-07 07:00，2026-11-08 07:00)，Asia/Shanghai。
- cutoff_hour=7；diagnostic_only=false；force_publish=false。
- trigger_source=manual-siliconflow-recovery。

没有把下午的执行时间当作新闻时间，没有强制重复发布、降低质量门槛、扩大并发/预算、
重建6/7日刊期或手改gh-pages/状态分支/发送回执。正常渠道沿既有幂等路径执行；
超过渠道既有延迟或过期限制时据实报告，不擅自放宽。

## 当前验证

首轮补跑已在30分钟边界终止，尚未出刊；详见下方修复记录。
PR334现包含完成补刊所需的评分任务策略、请求总时限和进度日志修复，须跑完整适用应用CI。

Source commit: 7ffe3ebceddf6e026da4d5eddbe3bb9a4dec8f14。

Worker version: pending，待自动部署与正式域验收，不手工部署。

Deployment: pending，首轮终止，修复和补跑验收中。

Verification: pending，公开首页补跑前仍为11月5日；不能宣称11月8日已出刊。

Rollback: 不自动回滚、重置状态或发送回执；如需另按授权处理。

## 首轮失败与修复

[首轮42453408651](https://github.com/ohxiyu/xiyunews/actions/runs/42453408651)
从2026-11-08约14:07至14:37运行，daily-summary在既有30分钟边界终止；日志
06:08:36Z最后记录281个固定窗口候选，06:37:11Z记录operation canceled。
没有run-report.json、摘要生成、Telegram发送或gh-pages发布日志。既有always缓存保存
步骤执行，但不能据此断言有效评分已保存。没有手动取消或提高时限。

代码可确认的配置问题是：ContentAnalyzer按固定刊期添加窗口说明后，提示词不再与静态
CONTENT_ANALYSIS_SYSTEM相等。SF请求策略使用精确prompt_stage，动态评分被当作other，
经济模式反而使用开启思考和8192最终输出预算。静态同类评分使用非思考和1536预算。
日志没有细化到粗筛/评分或每个请求耗时，因此该差异与长耗时一致，但不能把全部延迟
都归因于它，或据此断言供应商故障。必须以修正后的真实补跑验收。

PR334修正仅针对SF的任务识别：沿用已有usage_stage对已知评分提示的前缀及校准段识别，
使静态/固定窗口动态评分都使用同一经济策略。模型、完整评分提示、7分门槛、分类和
语义去重校验不变。非经济模式及其他复杂任务仍保留思考；旧DeepSeek策略不变。

SF请求以asyncio.wait_for落实既有request_timeout_seconds=120的总时限，覆盖SDK重试与
可能持续的网络保活；不把SDK逐次网络读取超时误认为整个请求有总时限。
超时会取消并等待在途协程清理；后续请求仍允许恢复，不当作账户永久故障。
取消不能撤销远端已执行的请求或保证不计费。未增加超时、并发、重试次数或费用限额。

加入粗筛开始/完成、评分开始/每10项已处理/完成的脱敏进度日志，只记录数量与模型名，
不打印提示词、正文或模型推理内容。每10项日志统计已处理项目，不把临时失败伪称成功。
新增回归覆盖动态评分的非思考/1536策略、非经济模式保持原策略、永不返回的异步请求
受总时限取消且后续正常调用能恢复。现有账户错误快速失败和并发取消回归继续保留。
本机AST通过；完整CI、正常合并和真实补跑仍pending。

## 第二轮与结构化任务修复

[PR334](https://github.com/ohxiyu/xiyunews/pull/334)应用head
 a37cb3a9d111f32950d9316804a1f178713cd053 的
[CI42455995141](https://github.com/ohxiyu/xiyunews/actions/runs/42455995141)适用检查全绿：
1212 passed、4既有skipped，44.51秒；审计无已知漏洞，治理及预览通过。
按正常流程合并ce37fc98e4a9a4e03d79709b8e3cccf8253d7c17；确认祖先后正常删除原分支。

[第二轮42456327190](https://github.com/ohxiyu/xiyunews/actions/runs/42456327190)，
同一期07:00边界、force_publish=false，源ce37fc9：

- 粗筛06:51:18.237Z至06:51:53.090Z，281选140，0失败批次，34.85秒。
- 评分06:51:53.093Z至06:54:52.342Z，140/140全部处理，179.25秒。
- 扩写06:55:28.450Z至07:14:47.493Z，14项，19分19秒；10项在重试后回退翻译。
- 07:20:10.364Z再到30分钟边界。没有摘要生成、Telegram成功或gh-pages发布日志；
  没有run-report.json。仍不能声明出刊。动作缓存保存沿既有always路径执行。

这证明评分修复生效，也揭示扩写仍有严重耗时。原日志只打印RetryError，不能确定
每个被包装异常的实际类型，不能把14项processed当14项完整扩写成功。

[Issue335](https://github.com/ohxiyu/xiyunews/issues/335)同一编辑负责人，
分支agent/siliconflow-json-economy，基线ce37fc9，隔离快照work/siliconflow-json-economy/source。
SF经济模式中所有JSON任务都关闭额外思考，包含扩写和事件关联；保留最终输出预算
（复杂任务8192）、模型、完整提示词、筛选分数/来源/语义校验和超时/并发/重试数。
非经济模式及自由正文仍按原策略支持思考；旧DeepSeek等provider不变。

复杂JSON请求记录开始、响应到达耗时或异常类型，不记录响应原文、提示词或推理内容；
响应到达不冒充解析或业务校验成功。扩写每5项记录已处理数量及阶段耗时；失败解包
RetryError的最终异常类型并立即刷新，只输出类型不输出供应商异常正文。
补充真实重试/翻译兜底下异常类型和脱敏回归，以及复杂/自定义JSON输出预算不缩减、
非经济模式/自由正文仍思考的协议回归。本机AST通过，完整CI和第三轮真实验收pending。

当前交付状态：PR334代码/测试/合并complete；Issue335修复code complete、tests/merge pending；
今天日报的生成、部署与生产验收全部仍pending。没有提高30分钟任务上限来掩盖问题。
