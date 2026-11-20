# 统一服务器执行与阅读优化：生产验收

Issue: https://github.com/ohxiyu/xiyunews/issues/255。唯一编辑与整合负责人为当前会话，agent/runtime-verification，从main b5abadb2b44708533bc2db2f2f01b44d4c6cf857开始。此PR仅回写事实证据、当前交接、运行手册与架构，不修改应用或触发新发布。

## 已交付

PR251安装既有东京服务器专用执行器并统一20个任务入口；真实当前head完整CI通过后合并。PR249默认折叠正文后的分析/讨论/参考/标签，背景在上、正文和完整分享保留；真实当前headCI通过、自动发布与浏览器验收。PR254针对真实正常采集验收暴露的持久Git浅层引用/初始化前解释器问题修复，各本地实际Git回归和最终服务器CI通过后合并。历史失败、取消与后续成功分项记载在各发布记录，不掩盖问题或绕过检查。

| 验收环节 | 实际证据 |
| --- | --- |
| 执行方案CI | 38352364252 success；实时3.11/3.12、应用、整站、治理通过。 |
| 阅读UI CI | 38353338739 success；主项目/构建/治理/路径与Pages通过。 |
| 持久环境修复CI | 38355573706 success；最终head dd962369da201eb6f5ada049c995e2509a0b1de9。 |
| 正常采集 | 38356743463 success，xiyunews-tokyo-1执行4m10s，208条采集、62条新增暂存、2个事件实质更新；AI缓存和staging分支保存success。 |
| 日报恢复 | 38356746499 success，协调器healthy HTTP200，不重复出刊。 |
| 分发门控 | X38356833645 success/work=false无发送；Square38356833651 success/attention0/unscheduled0，处理原正常队列。 |
| 最终网站发布 | 38357733594 success，固定新出版产物；/health与新事件API回读相符。 |
| 原实时进程 | PID235825/NRestarts0、三个现货分片live、Telegram启用、队列0；没有重启或发送测试消息。 |
| 服务器资源 | 执行器硬768MiB/软704MiB/CPU1核/swap最多512MiB，物理峰值741953536字节，swap观察约300MiB，OOM及oom_kill0，磁盘剩余约30GB。 |

Source commit: b5abadb2b44708533bc2db2f2f01b44d4c6cf857。
Worker version: afd40c2f-e05f-4aeb-91a4-ab59b2640c5c。
Deployment: https://github.com/ohxiyu/xiyunews/actions/runs/38357733594 ，产物187c6a360815ad7f14cfeb79faba7515bdedb7b4，主域xiyu.news。
Verification: 2026-10-13上海约14:43回读status=ok/source/artifact/version，首页/API/RSS/sitemap/manifest200，日报.html规范化307后200，canonical新主域，www301保留路径查询。真实桌面1280×720、手机390×844、暗色、英文、追踪页附加面板closed/点击/Enter/Space正常，无溢出；完整分享1320×4176未丢资料。新事件API标题与出版快照一致。
Rollback: 若需回退先获批准；不重刊当日日报、不清队列/AI缓存/读者数据、不强推生产分支、不把耗尽额度的托管执行器当可用备用。

## 运行职责与成本

GitHub统一私有仓、工作流/Secrets/记录与产物分支；东京单runner执行采集、AI分析、CI、构建与正常发布任务；Cloudflare统一项目负责网页/API/后台、Cron派发和看门狗。实时systemd单独运行，同机不同用户、依赖、数据库与目标群；源码统一不意味着合并进程或数据。工具环境复用，测试/解压/下载并发受限，每周只清专用旧诊断日志和无用uv包，不清业务缓存。没有新增套餐/服务器/预算，托管2000分钟保持耗尽与预算0，自托管执行避开该分钟限额；AI/机器/Cloudflare和artifact/cache成本限额分别存在。

## 实际限制与尚未验证

1. 本次采集报告status=warning，四个RSS子源The Block/The Defiant/CryptoSlate/Tether在东京返回403，其余五个顶层来源成功；其中The Defiant确认cf-mitigated:challenge。与迁移前托管报告对比，这组限制为新出站环境差异。保留来源和真实告警，已有Google News/Telegram等继续覆盖，不删除来源或擅自添加代理/付费服务；这不是全来源健康。
2. 采集记录213072 tokens用于新增分析/事件关系/合并/翻译，没有为了验收再跑第二次AI，迁移位置不改变模型单价或永远命中缓存。保持缓存降低重复工作，不承诺总成本0。
3. 明日上海07:26自然日报与后续自然四小时触发尚未发生；手动正常采集成功不证明未来触发。服务器/GitHub网络仍为单点依赖，排队可能延迟，不承诺每天永不中断。
4. 既有实时Hyperliquid降级不由此迁移修复，health200不等于全来源ready；本次不验证手机实际收件、看门狗真实故障告警或登录后Quick Post，不制造故障/测试新闻。

关联证据：[执行方案](2026-10-13-self-hosted-runtime.md)、[阅读UI](2026-10-13-analysis-collapse.md)、[持久环境修复](2026-10-13-persistent-checkout.md)；运维入口为[执行器手册](../self-hosted-runner.md)、[系统架构](../system-architecture.md)。工作区outputs/analysis-collapse-20261013/保留production桌面/手机/暗色/追踪截图。
