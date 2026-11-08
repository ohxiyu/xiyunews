# 2026-11-08 日报账户错误快速失败

[Issue327](https://github.com/ohxiyu/xiyunews/issues/327)，分支 agent/provider-balance-failfast，本聊天Codex唯一编辑与整合负责人。使用GitHub connector固定当前main e810cf95a6687a12deb7a469c58d7c0bdadd7bf7读取隔离源码快照；未使用已失效的旧worktree或修改他人目录。

## 根因证据

- 11月6日主定时[42129284424](https://github.com/ohxiyu/xiyunews/actions/runs/42129284424)，job127601494390，23:38:14Z明确记录 `reason=insufficient_balance, status=402`，去重拒绝发布。
- 11月7日主定时[42311933425](https://github.com/ohxiyu/xiyunews/actions/runs/42311933425)，job128215228855，同为402；140条评分失败后继续到0条榜单和去重失败。
- 11月8日主定时[42425266301](https://github.com/ohxiyu/xiyunews/actions/runs/42425266301)和恢复[42430827271](https://github.com/ohxiyu/xiyunews/actions/runs/42430827271)仍是402；采集恢复job128606074201和watchdog128605983502返回daily_retry_limit（503）。
- 当前生产配置为DeepSeek/deepseek-flash，analysis_concurrency=5。调度和Runner可以工作，采集/Cloudflare发布仍有成功任务；没有证据支持Cron未触发。
- 2026-11-08约11:02上海时间，首页及latest均停在11月5日13条，generated_at=2026-11-05T07:37:56.199782Z；/health=ok、/ready=ready仅代表技术就绪，不能当作当前刊期健康。
- starts_24h是守护进程重启预算，不是工作流次数，不以0推断未执行。此前发布时限修复不是本次余额故障根因。

## 修复

OpenAI兼容客户端仅依据显式整数HTTP401/402/403识别账户故障，输出固定原因和处理动作，不回显供应商响应。单次客户端运行内缓存该账户故障，后续粗筛、评分等阶段不再访问该账户；新运行重新允许尝试，不永久锁死充值后的账户。

评分器不再对账户故障执行三次tenacity重试，不把它转换成每篇0分/Analysis failed。首次账户故障使整批失败并保留缺失分数；并发队列停止，已在途任务取消并等待清理（最多仍有当前并发额度请求已发出，不能撤销已发生的远端计费）。429/网络/服务端等原有临时错误重试不变，未新增fallback模型或改变费用。生产已有三次刊期恢复上限继续保留。

固定错误文本进入现有运行报告和GitHub error注释，明确要求充值或修复凭据后再试。没有修改Worker健康协议；独立业务新鲜度告警仍应与技术就绪分别解读，不宣称本次已新增低余额余额查询或送达通知。

## 验证与边界

新增回归涵盖140条批次首次账户故障只调用一次、401/402/403不产出伪零分、三并发在途取消且后续不开始、客户端跨阶段熔断与新客户端可恢复、429重试后正常评分、字符串含402不误触发。没有真实AI/消息测试。

本机Python3.9语法和标准库分类验证通过；完整Python及相关CI待远端运行。代码完成，测试/合并/部署待验证；公开出刊恢复仍受余额阻塞。用户2026-11-08明确“暂不充值，先完成代码修复”，不得充值、换密钥/模型、降低质量门槛或重跑日报来假装恢复。不得为历史缺刊编造数据或重发历史消息。

Source commit: 基线 e810cf95a6687a12deb7a469c58d7c0bdadd7bf7；应用提交和PR待记录。

Worker version: not changed，本次不修改Worker代码；最近核验90302c66-5a58-4a88-a632-f247214fe6db。

Deployment: pending，尚未合并或发布。

Verification: 生产latest仍为11月5日，暂不声明恢复。

Rollback: 不自动回滚、改状态分支或重置发送回执；任何回退另按授权处理。

