# 当前交接

当前目标：五阶段迁移的阶段 3：将实时提醒以保留历史的方式并入 realtime/。PR169、PR171 已合并，两仓均私有；新域 Pages 已绑定、HTTPS 首次 200，Access 与旧域 301 尚待验收。保持首页和实时规则不变。

<!-- execution-pointer -->
```json
{
  "goal": "阶段 3：保留完整历史并入 realtime、独立 CI 和新仓部署打包",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/172",
  "owner": "Codex / 迁移唯一编辑及部署整合负责人",
  "branch": "agent/xiyunews-realtime",
  "last_verified_commit": "d5360740bb571c6bf95d3fcb631a54ac00634e9f",
  "pr": "待建立阶段 3 PR；必须 merge commit，不能 squash/rebase",
  "completed": ["PR169、PR171 全绿后顺序合并，自动发布品牌；两仓私有", "Dynadot NS 已传播、Cloudflare active，新旧 www 域名绑定 Pages；xiyu.news 首页 200 和新 canonical", "调度器 ac52cef1 已部署，health 指新仓，ready 验证 Actions 写与 Contents 读权限", "旧 main 7807126d 完整历史不 squash 导入 realtime，运行规则与独立依赖保留"],
  "unfinished": ["阶段 3 全量检查、合并与祖先验证", "新域 Access、旧域 301 与公共检查正式切换", "阶段 4 服务器切换与阶段 5 Telegram 品牌"],
  "validation": ["阶段 2 929 项 pytest、64 项调度器、22 项后台 Node、类型/dry-run/治理与远端 CI/Pages 通过", "阶段 3 独立验证正在执行；根/子模块依赖不互相安装"],
  "unverified": ["后台 Access/Quick Post 与旧域 301", "新仓实时服务 SHA、三个分片和自然回执", "调度器下一次自然 workflow_dispatch"],
  "production": {
    "source_commit": "e12179905981ed2ff5c31811db41f4c5f7b259d1（PR169 已发布；PR171 自动发布待回读）",
    "artifact_commit": "7fe7ed4c15610534c3d1609552616cf6dfc9cd4a",
    "edition": "2026-10-01（迁移前记录）",
    "generated_at": "2026-09-30T23:28:59.968601Z（迁移前记录）",
    "worker_version": "ac52cef1-d767-4d0e-903b-bfe1886b3b1f（调度器）",
    "verified_at": "2026-10-01；新域首页 HTTPS 200，后台/301/自然任务仍未验收"
  },
  "blockers": ["两份旧 Git 历史 README 含疑似 Telegram Token，需确认已撤销；保留历史需求下不能擅自重写，导入尚未推送", "本机不存在既有 fomobtc_tokyo_config，不能代替原电脑进行服务器切换", "Access 云端权限修改需要操作时确认，当前先准备，不扩大权限"],
  "next_action": "阶段 3 全绿后以 merge commit 合并核对历史祖先，再准备阶段 4 命令和阶段 5 文案；Access/HTTPS 就绪后切换 301 与调度器 PUBLIC_SITE_URL",
  "states": {"code": "complete", "tests": "pending", "pr_merged": "pending", "deployed": "pending", "production_verified": "pending"},
  "evidence": "project-docs/releases/2026-10-01-xiyunews-realtime.md"
}
```

实时入口见 [realtime 交接](../realtime/docs/handoff.md) 和 [部署手册](../realtime/docs/deployment.md)。主站迁移见 [运行手册](brand-domain-migration.md)。不执行旧 backlog、不合并其他人的 PR、不修改规则与地址簿；历史发布记录保持原样。
