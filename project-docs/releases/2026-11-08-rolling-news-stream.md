# 密集信息流与滚动24小时精选上线验收

Issue: https://github.com/ohxiyu/xiyunews/issues/349
Evidence issue: https://github.com/ohxiyu/xiyunews/issues/351
Application PR: https://github.com/ohxiyu/xiyunews/pull/350

- Code complete: complete，恢复原机器人Logo、密集全文、滚动24小时精选与稳定链接。
- Tests passed: complete，最终CI https://github.com/ohxiyu/xiyunews/actions/runs/42484085862 ；Python 1250 passed / 4 existing skips，Worker141测试、类型检查、依赖审计、真实出版数据Jekyll构建及统一Worker打包全部通过。
- PR merged: complete，合并为1cbb849a094e10c71276b7a5ed97f70939c40958。
- Deployed: complete，自动Docs和Cloudflare成功。
- Production verified: complete，真实采集/AI/鉴权发布/服务端首页/API/固定链接与手机桌面外观均验收。

Source commit: 1cbb849a094e10c71276b7a5ed97f70939c40958
Artifact commit: 907ac8b4714ce2211b9719a26d8268c07c7de703
Worker version: 3bbbb98c-5bdb-4b0f-a3f0-74b1f23b946d
Deployment: https://github.com/ohxiyu/xiyunews/actions/runs/42490315582 ，之前Docs https://github.com/ohxiyu/xiyunews/actions/runs/42490154328 。
Verification: 2026-11-08T14:46:17.091812+00:00（北京时间22:46），https://xiyu.news/ 与 /api/live.json 实际响应和DOM核对。
Rollback: 如需回退，先获得用户授权，再以独立PR撤销PR350并走原自动部署；不手改gh-pages，不删除Durable Object存储或更换命名空间。本次未执行回退。

## 实际数据链路

首轮 https://github.com/ohxiyu/xiyunews/actions/runs/42490379778 成功。37秒完成来源采集；192条未缓存候选经过预筛，113条进入siliconflow:deepseek-ai/DeepSeek-V3.2评分，预筛失败批次0。经评分门槛、URL/语义去重和原配额精选14条，扩写14条成功，14条均有背景，共51个参考链接。采集时间2026-11-08T14:37:54.613Z，精选时间14:45:32.394Z；没有将两者当来源发布时间。

/api/live.json返回200，stale=false；14条来源发布时间全部位于请求前24小时内且倒序。首页服务端HTML包含同样14个ID、全部正文和背景，无JS也有全文；compact-story数量0。测试固定链接 /story/8b235f57278abe2407ff2dba80b1b06a/ 返回200且正文完整。含If-None-Match和If-Modified-Since的首页请求仍返回200/no-store，无ETag，不能用静态shell缓存保留旧精选。

保留每日07:00截止归档（当前刊期2026-11-08、generated_at 2026-11-08T08:58:08.694761Z）；日报/Telegram单次投递与滚动精选分离。每轮采集不写gh-pages、不触发整站重建、不发Telegram。事件AI独立每4小时更新。英文代码仍保留、功能关闭；人工纠错等此前停用功能没有恢复。独立realtime服务未修改。

## 视觉与边界

正式桌面浅色与390×844手机浅/暗色截图完成。手机scrollWidth=innerWidth=390，14条正文均可见，14背景、原机器人SVG与三项导航正常；固定链接实际点击打开全文。

截图及响应证据在本次工作区outputs/rolling-news/：production-desktop-light.png、production-mobile-light.png、production-mobile-dark.png、production-verification.json、production-live.json、production-home.html和production-health.json。它们是实际生产响应/截图；本地preview截图不作为生产证据。原分支e1b416e...到main比较ahead1/behind0，确认祖先后通过GitHub Delete branch清理，页面显示Restore branch。

目标采集检查周期5分钟，属于轮询。首次补齐未缓存内容的AI阶段约7分13秒，另有约4分钟执行器排队，不能承诺每5分钟完成出稿。后续复用评分/语义比较/扩写缓存；所有原模型、评分阈值、max_items14、候选上限140及并发5均保留，没有新增服务或提升配额。采集落后30分钟明确提示，读取自动剔除过期新闻；无快照明确归档兜底，不冒充实时。上游个别来源403仍有记录，不代表所有来源可用；本轮整体采集和精选成功。
