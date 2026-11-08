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
