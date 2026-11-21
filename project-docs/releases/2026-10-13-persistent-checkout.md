# 持久执行器的出版状态恢复

Issue: https://github.com/ohxiyu/xiyunews/issues/253。唯一编辑与生产整合负责人为当前会话，agent/persistent-checkout，基于合并 UI 后的 main 7ee1ee87b5d9ead50aafff564f3745dc1a6a0a1b。运营者已授权服务器迁移、优化和直接上线。

## 故障与修复

正常 Feed Collection 38353543010 与首次 X 分发 38353245000 在恢复 gh-pages 时出现本地 non-fast-forward 拒绝：自托管 checkout 会保留浅层远端引用，原命令针对全新临时机器。失败在采集、AI 或发送之前，不重刊日报、不重发历史、不清队列。

采集、日报、只读诊断、周报、X 和显式迁移工作流使用加号 refspec 更新本地远端跟踪引用，仍是 fetch，没有 force push 或修改远端历史。采集报告改用 Ubuntu 可用的 python3，初始化前失败不再以找不到 python 掩盖根因。使用隔离本地 Git 远端和两个不继承的出版快照执行各真实工作流命令：原命令拒绝、修订命令读取最新状态、远端 refs 完全不变。Square 和 staging 已用自动远端跟踪/FETCH_HEAD，不改其逻辑。

Source commit: pending；基线为 7ee1ee87b5d9ead50aafff564f3745dc1a6a0a1b。
Worker version: not changed by this fix yet；最近 f4bf4bd7-8e7b-4ed3-a353-8b4ba0bee0ae。
Deployment: pending；本修复待当前 CI 通过与 main 同步后合并，经正常工作流发布。
Verification: 修复回归、实际正常采集/缓存/出版及主域验收待完成；原 PID235825/NRestarts0 与三个现货分片 live 已核对。
Rollback: 需要先获批准；不自动回滚、不删除出版历史或重设发送状态，保留所有业务凭据和产物分支。

本地完整应用回归1064 passed/4 skipped；六项新增Git回归首次fixture目标引用省略refs/heads导致准备阶段失败，补齐后六项全部通过，非应用错误。治理、actionlint全部工作流与diff通过。当前服务器CI、合并和正常采集仍待完成。

随后本地完整1070项回归通过、4 skipped，治理通过。同类日报、周报和X报告也统一python3，避免初始化失败时相同缺失解释器问题；最终head重新运行CI，不使用旧head的成功检查。

实际Square38354408915也在安装依赖前的stdlib门控中因缺少python失败。全入口顺序复查后，Square门控、日报恢复及只读历史导入统一系统python3；不增加空任务的依赖安装，不改变调度/门控/发送/导入数据规则。新head再检查并按真实运行验收，不以原CI成功替代。

## 正常服务器业务验收

最终head dd962369da201eb6f5ada049c995e2509a0b1de9的实际CI38355573706全部适用检查通过：应用2m52s、整站3m37s、治理12s、路径11s、旧Pages成功；realtime路径未变与CodeQL按原条件跳过。同步main后PR254于上海14:26:49合并b5abadb2b44708533bc2db2f2f01b44d4c6cf857。

Source commit: b5abadb2b44708533bc2db2f2f01b44d4c6cf857。
Worker version: 7db2d592-2630-441d-8678-88258091ca23（修复首次静态生产版本，采集后最终版另记）。
Deployment: Deploy Docs38356741257、统一Worker38356833804均success，固定产物48f65b5e95ed00006f0db336a18425ad4f352560；来源/秘密/调度未改。
Verification: 日报恢复38356746499成功，stdlib python3正常、协调器healthy HTTP200，没有重复刊期。X38356833645成功work=false未发帖；Square38356833651成功attention0/unscheduled0，正常原队列处理不补历史。普通采集38356743463由xiyunews-tokyo-1执行，上海14:33:03–14:37:13，所有采集/报告/AI缓存/事件出版/staging分支持久化步骤success；手动正常采集的recover-daily按原schedule-only条件跳过，已独立验证恢复检查。
Rollback: 先获得明确批准，不重刊已发布日报、不清队列、不自动恢复已耗尽额度的托管运行位置。

本次报告：208条采集、197条URL去重、62条新增暂存/分析，累计1162条暂存；2个实质事件更新、9个新事件、分类与合并调用错误0。总tokens213072（输入171600/输出41472），用于本次新增分析、事件关系、合并与翻译；保留缓存，没有为验证重跑采集，也不把运行位置迁移声称降低模型单价。报告artifact run-report-38356743463-1可回读。

来源限制如实保留：5个顶层来源成功、GitHub当前窗口为空；The Block/The Defiant/CryptoSlate/Tether四个RSS子源HTTP403，报告status warning/partial_failure，不能写全来源正常。此前托管采集38343321421只有Fed404，说明这轮限制与服务器出站环境有关；东京对The Defiant同应用User-Agent只读复查HTTP403/cf-mitigated:challenge。其余RSS、Telegram与已有Google News继续工作，已有Google News包含CryptoSlate2条；不擅自删信源、开新代理/付费服务或解挑战，不扩大这次迁移为未批准的信源改造。

下一次自然四小时采集和明日上海07:26日报尚未发生，不以本次正常手动运行冒充自然触发。最终采集后统一部署38357733594仍在构建，待回读生产产物与版本后补记录。

最终采集后统一部署38357733594 success。上海约14:43主域回读source=b5abadb2b44708533bc2db2f2f01b44d4c6cf857、artifact=187c6a360815ad7f14cfeb79faba7515bdedb7b4、Worker=afd40c2f-e05f-4aeb-91a4-ab59b2640c5c，status=ok；新事件api/events/evt_5e8576e57a4b3ce4.json200且标题与出版快照相同。采集、状态保存、渲染、发布与主域已完成，不再将进行中的首次静态快照作为当前生产版本。
