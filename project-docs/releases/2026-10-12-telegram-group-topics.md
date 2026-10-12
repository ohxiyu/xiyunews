# 群内信息流与事件追踪：准备与权限阻塞

Issue: https://github.com/ohxiyu/xiyunews/issues/234
Branch: agent/telegram-group-topics
Baseline: 9d051a9d7c06cd3166217ce9203f4c524d013b21

运营者确认每日信息流＋每日事件进展两个话题的方案，并同意执行。当前会话为唯一 owner，只新增两个目的地，不改原频道、三个实时话题、Bot Token、源配置或服务器服务；不新增 AI 调用、不补历史。原工作区 tests/test_entity_profiles 2.py 未触碰。

## 本轮实际结果

实现只读消息快照准备模块：使用出版 API 与同一重点追踪索引，保留全部日报标题、前三条事实首句、固定日期/序号链接，长消息按完整条目分割，事件保留原 ID、状态、节点证据及已结束事件供后续收尾。仅供离线准备，尚未接入 Worker/工作流，不能宣称已经自动推送。

新增两话题专用初始化脚本，默认只读检查，不重跑原三话题脚本。创建前持久化未知状态，可能已创建但丢失回执时拒绝自动重复；Token 不写入回执或日志。此脚本尚未执行创建操作。

2026-10-12 使用既有 SSH 配置，严格主机校验、BatchMode 与 sudo -n 读取既有配置，在服务器进程内调用 getMe/getChat/getChatMember。确认 Bot 为 xiyunewsbot、群名 xiyu.news、forum=true、administrator=true，但 can_manage_topics=false。未扩大权限、未创建话题、未写 /etc/fomobtc.env、未重启服务、未发送消息。客户端只读替代路径尝试过，但 Telegram 的内容不提供可用 AX 操作；没有修改管理员设置。

阻塞：必须由运营者决定，只为现有 Bot 开启管理话题权限，或由管理员手动创建两个话题后提供话题链接。不能把“已经是管理员”当作具备所有管理权限。

## 状态与下一步

代码仅准备完成，发送与去重状态机、Worker 接入、配置绑定及自然回执均未完成。准备模块的离线测试另记录；PR 保持 Draft，不合并、不部署。获权限方向后先回读权限/话题，完成独立持久化发送记录、未知结果保护和自然发送验收。

离线回归：新增快照测试 5 项，完整主项目 pytest 1,061 项通过、4 项跳过；治理检查和 git diff --check 通过。验证范围只有准备代码与既有功能，不代表发送器、话题创建、生产或自然推送已经验收。

Source commit: 本轮未部署，现役 9d051a9d7c06cd3166217ce9203f4c524d013b21。
Worker version: not changed；现役只读核验 2431d2dd-5e7e-49f0-8226-6492698aac79。
Deployment: not performed；没有派发真实采集、AI、测试发送或部署工作流。
Verification: 仅配置存在、身份/群组/权限只读核验及离线消息准备测试，两个话题不存在创建成功回执，自动推送未配置。
Rollback: 无生产变更，无需回退；准备分支不能直接用于生产。
