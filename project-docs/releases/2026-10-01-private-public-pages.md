# 私有仓后的公开页面修复

Issue: https://github.com/ohxiyu/xiyunews/issues/181

## 修改范围

运营者要求解决迁移审计中发现的问题。本阶段仅修复私有仓后的公开站点说明与许可访问：关于页、联系页、法律页、llms 和 Organization 元数据不再把私有 GitHub 链接描述为公开渠道。三份许可及权利说明直接在 /legal/ 下公开，逐字同步根文件；原版权声明和法律权利不变，未开放仓库。RSS 和 Telegram 抓取标识指向公开站点，未调整信源、阈值或页面结构。

运营者先要求不公布私人信息，后指定公开 X 账号 @ohxiyu。联系页只链接 https://x.com/ohxiyu，不公布邮箱或个人 Telegram，不新增站内表单，不承诺私信开放或实时回复，也不把打开主页当作请求送达。

## 验证与发布状态

新增 5 项离线回归覆盖公开文案、站内许可文件一致性、元数据和抓取标识。完整 942 项 pytest、治理和 79 项 Node 通过；远端 CI、主分支同步、正常 Pages 发布及线上回读仍须逐项完成后记录。没有真实调用 AI、X 或 Telegram 作为测试。

自然采集运行 36849586444 使用 d09677fcd7a1ccf0cf9fedac3a4c81c2145a0fe3，整次运行 success，事件页发布和缓存持久化步骤均 success；缓存修复首次自然执行已验收。运营者随后取消旧域入口和 301，仅保留新域 Access 路径，旧域注册与 DNS 资源未删除。Access、历史凭据撤销、实时新仓部署、Telegram 实际改名与私有 CI 成本优化属于后续独立步骤。

Source commit: 实施分支基于 d09677fcd7a1ccf0cf9fedac3a4c81c2145a0fe3；本阶段未合并。
Worker version: 现有独立调度器 dd126dda-3c13-4e8d-b582-e2550c08cb98，未在本阶段修改。
Deployment: 尚未发布本阶段页面，须通过正常 Actions，禁止手动写 gh-pages。
Verification: 完整 942 项 pytest、治理与 79 项 Node 通过，自然采集 36849586444 成功；本阶段公开页面生产仍待验收。
Rollback: 未执行回滚或删除；仓库保持私有，历史保留。
