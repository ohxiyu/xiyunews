# 阅读入口与分享图精简

## 范围

按 [Issue284](https://github.com/ohxiyu/xiyunews/issues/284) 停用公开周报模块。中英主导航和 PWA 底栏仅保留信息流与追踪，PWA 快捷方式同步移除周报，RSS XML 继续供订阅读者和接口使用。

删除周报定时工作流，CLI 不再接受 weekly，统一部署不再监听周报任务。Jekyll 排除中文/英文周报入口及历史页面；Worker 在缓存之前把旧周报 URL 301 到相应语言首页，保留查询参数。日报发布和无 AI 重建清理旧 sitemap 的周报记录，发布重建同步修正 llms 导航描述，历史归档和旧周报代码/模板保留以供审计，不继续生成和推送。

分享 PNG 只呈现品牌、新闻标题、背景与完整分段正文。背景置于标题下的浅底圆角区域，有明确标签和蓝色侧标识；之后接正文，没有评分、分类、分析、来源栏、参考资料和标签。保持网站配色、440 CSS px 宽/3 倍导出和高度保护；无背景时不造空面板，旧日报通过背景 section 兼容。

## 验证与状态

独立分支 agent/reader-simplify，基于 main eef77c30。69 项相关 Node 测试已通过，包含周报跳转、PWA 两入口/退休路由、分享内容排除与背景先于正文。完整 Python、治理、CI 与视觉检查进行中，结果完成后补记，不把代码完成当作已上线。

Source commit: 待 PR 合并后核验。
Worker version: pending，本轮含旧周报 URL 处理。
Deployment: pending，按现有 Deploy Docs → xiyunews Cloudflare 自动流程发布，不手工写生产分支。
Verification: pending，验收中英/手机导航、分享 PNG、旧周报跳转、RSS 与 sitemap。
Rollback: 已知健康版本 eef77c30 / Worker 8d340dfc-a146-420e-9d3d-6ab35cc04340；回退需要运营者明确批准，再按原生产流程发布。
