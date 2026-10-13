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
