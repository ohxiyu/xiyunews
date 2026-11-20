# 私有仓分发到期门控

Issue: https://github.com/ohxiyu/xiyunews/issues/183

## 修改

Worker 五分钟时钟保持，新增私有队列只读门控：Square 只在每日计划缺失或未尝试任务到期时派发；X 独立检测新刊期、修订、到期、过期和 pending 清理，不再依赖广场每次完成。两者 GitHub 备用改为小时级，正常发布事件及日报首次 X 派发保留。时间表、正文、未知结果不自动重试、先持久化再发送的 Python 规则未改变。

固定 GitHub Contents API，鉴权且禁止重定向，JSON 限制 1 MiB；权限错误、404、无效 JSON/状态/时间戳 fail closed。活动任务不重复派发，失败后 30 分钟冷却。没有新服务、付费套餐、权限扩张或手动队列写入。Worker 不调用 AI、不持有社交发帖凭据。

## 验证和状态

完整 942 项 pytest、84 项 Workers 测试、绑定类型检查、tsc、dry-run 和工作流契约测试通过；治理、远端 CI 与生产仍须验证。预计消除大部分五分钟空跑，但采集、日报、发布、CI 和小时备用仍消耗私有 Actions 用量，不承诺零费用。实际账单读取权限不可用。

公开页面 PR182 全绿合并 21c96d4281e1cec771c7516d3722ea6ba6688c62，Deploy Docs 36851300087 success。Pages edf84841-0af3-470d-9a4e-47ec879e4a16 对应 artifact d4958131d9066268eef025fb07f912b25ea2b54a，生产检查 success。新域普通许可入口 200，联系页后续持续回读，不用查询旁路代替普通验收。Access 已仅保留新域六路径、原 policy 与 AUD，匿名入口 302 登录；登录后的 Quick Post 待运营者完成验证码。

Source commit: 调度改动基于 21c96d4281e1cec771c7516d3722ea6ba6688c62，尚未合并。
Worker version: 现有 dd126dda-3c13-4e8d-b582-e2550c08cb98，未发布本阶段。
Deployment: npm run check dry-run 不是生产；合并后 keep-vars 部署既有 Worker。
Verification: 942 项 pytest、84 项 Worker 测试通过；真实五分钟 idle 与到期派发待验收。
Rollback: 不自动回滚、删除锁或清空队列；现有数据和服务保持。
