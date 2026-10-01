# 稀有News 品牌与域名迁移：阶段 1

Issue：[#168](https://github.com/ohxiyu/xiyunews/issues/168)。分支 agent/xiyunews-brand-domain，唯一编辑与部署整合负责人 Codex。运营者授权全部迁移及部署；历史、包名、内容规则、版式与运行路径不变。

Source commit: 本阶段 PR head；基线 de180b0cf4ef99699374d606137c750b897a2428。
Worker version: Pages 未部署；独立调度器留给阶段 2。
Deployment: 未部署；GitHub 改名和免费 zone 创建成功，NS 保存、Pages 与 Access 未验收。
Verification: 本地 Python 3.13 完整 929 项 pytest、Node 76 项（含 15 项跳转）、调度器 61 项测试及 dry-run、治理与 diff 检查通过。Ruby 3.3 / github-pages 232 本地 Jekyll 构建通过，远端 CI/Pages 仍核验仓库锁定依赖；尚未声称新域上线。
Rollback: 保留原域、Pages 项目、旧产物与媒体版本；回退须通过独立 PR，禁止手写 gh-pages 或清空本地存储。

## 变更及剩余项

迁移读者可见品牌、自有地址、README、当前文档、RSS、API、后台 repo/origin 与媒体字标。旧域精确 Host 301 保留路径与查询，先于认证和缓存；PWA 资产缓存升级，页面存储保留。Logo 图形不变，备选 Redirect Rule 与后台核验列入手册。发布工作流迁移已有 API / editions / archive 的本站 URL，不调用 AI、不改新闻事实、ID 或交付状态；已验证幂等及队列不触碰。

允许旧名剩余：历史记录及证据、旧媒体包、LICENSE 原版权、内部包/命令/类、BMTNEWS_* 变量、兼容存储标识与跳转代码。ops 旧仓库引用仅本阶段暂留，阶段 2 必须清除。私有实时服务完整历史尚未并入或公开。
