# 背景前置与重点事件完整追踪

Issue: https://github.com/ohxiyu/xiyunews/issues/228
Branch: agent/focused-tracking
Baseline: d1b430e9d8a563f81892a4109a360b64a1180d1b
PR: https://github.com/ohxiyu/xiyunews/pull/229；CI、合并及部署待完成，不宣称已上线。

## 范围与规则

维护者确认讨论方案后授权修改、合并并上线。首页/旧刊期的阅读辅助移到标题下，默认背景预览、显式展开，讨论与影响按真实字段分别标注，参考显示实际链接数量。空字段不造占位；全文保留于 DOM 与分享图，正文不截断。无 JS 时新生成正文上方原生 details 保持展开；旧刊期仍保持原生折叠可读，JS 用同一控制器前置。Quick Post 独立模块不变。

追踪默认最多 6 个统一完整事件卡、最近 3 个不同节点和源证据定位；近期脉络 3 条及右侧重点导航引用同一集合。其他、沉寂、完成及归档折叠保留。选择门槛为重要性至少 7、至少两个不同节点、最新归属置信度至少 0.90、未关闭/解决；优先最多 3 个合格 Crypto 候选，剩余按重要性与有限新近度折减填补，不因转载量排名，不凑足。置信度是原匹配输出，不是事实核验。

只做保守展示去重：相同文本，或同一日期、相同数字和极性、同类型且共享源 URL 的近乎相同文本；纠错节点保留。所有更新 ID、原目录和完整详情不改。按 occurred_at 展示并保留时间精度；历史 edition 节点明确标刊期。最近可用背景代替早期背景，当前参考随该背景与最新节点，不聚合所有历史搜索结果。来源数量表示链接数，不称独立确认数。

[选择策略](../../data/tracking-focus.json) 仅维护可审查的排除/带来源期限，不自动猜测下一节点。ESMA 与 Abstract 的已收录期限保留候选资格，但不强制置顶；到期后自然失效。已识别 Coinbase/Deribit 历史线混有清算牌照等不同业务，暂退出重点，原记录和 URL 保留，尚未做破坏性归属迁移；不可据此宣称历史目录已全面修复。

Deploy Docs 从当前 gh-pages 还原事件目录后，只通过 [tracking_republish](../../src/tracking_republish.py) 重建读者索引。未来采集仍调用同一 build_event_index_data。没有 AI/渠道/后台写入，日报 API、原事件目录与队列不修改。现有自动统一 Worker 发布仅运送静态资源，保留运行变量；不改 Cron、DNS、Access、状态、依赖与实时服务。

## 验证与五阶段

完整 Python 1,056 项通过、4 项跳过；Node 阅读辅助 5 项以及分享/PWA/站点 Worker 合计 45 项通过；治理、diff 通过。真实生产快照用 Ruby 3.3 / github-pages 232 构建成功，桌面 1280×720、手机 390×844、英文窄屏暗色 320×760 检查无横向溢出；键盘方向键切换、参考显示、完整背景和首页前置通过。分享面板生成 1320×3972 的完整长卡，不发送到 X。根与 docs 指纹同步为 sha256-45be953e1aef。生产版本另行验收，不冒充已完成。

本地预览只复制生产快照到临时目录，不提交生成新闻或修改生产。Ruby 4.0 与旧 Jekyll/Liquid 不兼容，已改用现有 Ruby 3.3；临时安装及锁文件不进入仓库，不修改生产依赖。

桌面验收截图（1280×720）：[首页改前](images/2026-10-09-focused-tracking/feed-before.jpg)、[首页改后](images/2026-10-09-focused-tracking/feed-after.jpg)、[追踪改前](images/2026-10-09-focused-tracking/tracking-before.jpg)、[追踪改后](images/2026-10-09-focused-tracking/tracking-after.jpg)、[完整事件卡](images/2026-10-09-focused-tracking/event-card-after.jpg)。改前为当时正式页面，改后为生产快照配本次真实模板渲染。

- 代码完成；本地测试与浏览器验收完成，远程精确 head CI 待完成。
- PR 合并、部署及生产验收待完成。
- 不验证真实设备安装、剪贴板权限、X/Telegram 发送或 Quick Post。

## 发布与回退

Source commit: 待本 PR 精确合并 SHA。
Worker version: 修改前只读为 bc9eb588-e01e-4c48-b134-caaeade597eb，本次发布待完成。
Deployment: 授权沿用现有 Deploy Docs → xiyunews Cloudflare；待成功运行链接。
Verification: 修改前主站及追踪 200；修改后须核对新指纹、最多 6 卡/3 节点、背景/讨论/参考操作、日期链接和正常 API，不以 CI 替代现场验收。
Rollback: 需授权通过独立 revert PR 回退本次变化，再走同一自动发布；已知良好基线 d1b430e9d8a563f81892a4109a360b64a1180d1b。不手改 gh-pages 或状态分支，不撤销现有依赖安全修复。
