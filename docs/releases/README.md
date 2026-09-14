# 发布与验证记录

[1.0.0 基线](1.0.0.md) · [交接机制验证](agent-handoff.md) · [发布模板](template.md)

历史记录保留原始时间与证据，不改写成当前状态。仓库版本说明使用 `<VERSION>.md`，首行必须是 `# <VERSION>`。文档或 CI 修改不必增加应用版本。
每次应用 PR 增加或更新一份验证记录；实际部署另建 `deploy-YYYYMMDD-描述.md`，按模板填写，状态必须为 deployed 或 rolled-back，字段不能填 unknown/待填。计划与未知事项留在交接中。
本项目是 PM2 服务，因此运行版本记录 PM2 进程/启动时间及 checkout SHA；Worker 版本填写“不适用（PM2）”。进程在线不是业务验收。
