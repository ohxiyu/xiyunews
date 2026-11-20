# 阅读入口与分享图精简

## 范围

按 [Issue284](https://github.com/ohxiyu/xiyunews/issues/284) 停用公开周报模块。中英主导航和 PWA 底栏仅保留信息流与追踪，PWA 快捷方式同步移除周报，RSS XML 继续供订阅读者和接口使用。

删除周报定时工作流，CLI 不再接受 weekly，统一部署不再监听周报任务。Jekyll 排除中文/英文周报入口及历史页面；Worker 在缓存之前把旧周报 URL 301 到相应语言首页，保留查询参数。日报发布和无 AI 重建清理旧 sitemap 的周报记录，发布重建同步修正 llms 导航描述，历史归档和旧周报代码/模板保留以供审计，不继续生成和推送。

分享 PNG 只呈现品牌、新闻标题、背景与完整分段正文。背景置于标题下的浅底圆角区域，有明确标签和蓝色侧标识；之后接正文，没有评分、分类、分析、来源栏、参考资料和标签。保持网站配色、440 CSS px 宽/3 倍导出和高度保护；无背景时不造空面板，旧日报通过背景 section 兼容。

## 验证与状态

### 发布出口补充

PR285 已于 2026-10-14 23:41 上海合并为 f5610b12553783ebfe60d58956dd2dda7d1f6fbc，CI38589139515 全部适用检查通过。无 AI 重建 38591505567 正在执行。后续采集仍可能携带旧 llms 描述，因此 [Issue286](https://github.com/ohxiyu/xiyunews/issues/286) 将同一精确文本清理放到 scripts/prepare_edge_assets.py 的最终公共产物复制阶段，覆盖所有发布来源与恢复的构建缓存，不改变不可变输入快照或 RSS；有回归测试覆盖旧快照重复构建。此补充需要新的 CI 与正常统一部署验收。

38591505567 第一次运行在第二个代码下载步骤超过 10 分钟并取消，生产未被替换；已提交第二次重试。东京执行器实测下载一次可达 6 分钟，因此本补充将 Deploy Docs 的总时限由 10 分钟调为 20 分钟，给两次精确下载和无 AI 重建留出空间，保持有界、串行和现有服务/费用设置，不更换执行器。完整 CI 将重新验证该工作流；这是本次正常发布遇到的实际故障修复。

独立分支 agent/reader-simplify，基于 main eef77c30，[PR285](https://github.com/ohxiyu/xiyunews/pull/285)。完整 Python 1113 项通过、4 项既有条件跳过；117 项前端 Node 与 135 项 Worker 测试通过，npm 审计 0 漏洞，治理/actionlint/diff 检查通过。CI 与生产发布仍需完成，不把本地验证当作上线。

桌面 1440×1000，手机 390×844，英文窄屏 320×844 预览无横向溢出。实际分享：中文浅色 1320×2742 px、英文暗色 1320×3519 px，完整背景先于所有正文段落，无其他附加内容；图片保存通过，没有点击 X 发送。预览用隔离的已发布快照和现有本地 Jekyll 3.9/Liquid 4.0.4（Liquid 单独临时安装）；生产锁定的 Jekyll 3.10 由 CI 构建验收。公开构建中无 weekly 页面，sitemap 与发布 llms 无周报导航。Quick Post 本地动态接口不可用，不冒充生产故障，待生产回读。

- [改前桌面](images/2026-10-14-reader-simplify/before-desktop.jpg)与[改后桌面](images/2026-10-14-reader-simplify/after-desktop.jpg)。
- [手机浅色](images/2026-10-14-reader-simplify/after-mobile-light.jpg)、[手机暗色](images/2026-10-14-reader-simplify/after-mobile-dark.jpg)、[英文320](images/2026-10-14-reader-simplify/after-english-320.jpg)。
- [完整分享PNG](images/2026-10-14-reader-simplify/share-light.png)与[英文暗色分享面板](images/2026-10-14-reader-simplify/share-english-dark-mobile.jpg)。

Source commit: 待 PR 合并后核验。
Worker version: pending，本轮含旧周报 URL 处理。
Deployment: pending，按现有 Deploy Docs → xiyunews Cloudflare 自动流程发布，不手工写生产分支。
Verification: pending，验收中英/手机导航、分享 PNG、旧周报跳转、RSS 与 sitemap。
Rollback: 已知健康版本 eef77c30 / Worker 8d340dfc-a146-420e-9d3d-6ab35cc04340；回退需要运营者明确批准，再按原生产流程发布。
