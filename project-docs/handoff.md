# 当前交接

当前 Issue228：运营者确认背景资料前置与少量重点事件完整追踪，并要求修改上线。当前会话为唯一编辑和发布整合者；不续做旧迁移清理或 Quick Post，不改实时规则、来源、密钥、DNS、Cron 或 AI 模型。沿用 PR → main → Deploy Docs → xiyunews Cloudflare 现有发布路径，不手改 gh-pages。

<!-- execution-pointer -->
```json
{
  "goal": "上线背景前置标签页与 6 个完整重点事件追踪",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/228",
  "owner": "当前 Codex 会话，唯一编辑与发布整合负责人",
  "branch": "agent/focused-tracking",
  "last_verified_commit": "d1b430e9d8a563f81892a4109a360b64a1180d1b",
  "pr": "https://github.com/ohxiyu/xiyunews/pull/229",
  "completed": ["从最新 origin/main 开独立 worktree，保留原工作区未提交文件", "首页与旧刊期的背景/真实讨论/影响分析/参考前置标签页，完整文本和分享保留", "追踪统一完整事件卡、最多 6 个、最近 3 个节点、右侧概览及重点导航；完整历史和 URL 不删除", "保守展示去重，最近背景替代早期混入资料；影响不冒充讨论；明确来源的待办期限可保留候选资格", "只重建读者索引的无 AI 发布步骤，不改事件目录、日报 API 或消息队列"],
  "unfinished": ["精确 head CI", "同步 main、PR 合并与现有自动发布", "生产版本及页面现场验收"],
  "validation": ["完整 Python 1056 项通过、4 项跳过", "真实内容 Jekyll 构建、桌面1280和手机390、英文暗色320、键盘标签切换验收通过；分享完整长卡1320×3972生成", "Node 分享/PWA/Worker/阅读辅助共 45 项通过；治理和 diff 检查通过"],
  "unverified": ["生产新 UI 尚未上线", "不宣称机器置信度或多条来源等于独立事实核验；部分历史事件归属仍需单独审计", "不重写原始事件、新闻或密钥；实体设备 PWA 安装、剪贴板、真实渠道与后台登录不在本任务验收范围"],
  "production": {
    "source_commit": "d1b430e9d8a563f81892a4109a360b64a1180d1b",
    "artifact_commit": "4e915f937bd829408b78dbf1f1af79d1e5c61a45",
    "edition": "2026-10-09",
    "generated_at": "本任务未重生成日报，最终验收另读",
    "worker_version": "bc9eb588-e01e-4c48-b134-caaeade597eb",
    "verified_at": "2026-10-09，本任务修改前 health 与正式页面只读核验"
  },
  "blockers": [],
  "next_action": "完成真实内容本地构建/浏览器验收及测试后创建 PR；同步最新 main、全部适用检查通过后合并，等待 Deploy Docs 与统一 Worker 发布成功再验收。旧事件保留，不把 UI 去重声称为完整历史归属修复。",
  "states": {"code":"complete","tests":"pending","pr_merged":"pending","deployed":"pending","production_verified":"pending"},
  "evidence": "project-docs/releases/2026-10-09-focused-tracking.md"
}
```

上一项 llms.txt 应用 PR225 及证据 PR227 已合并；记录保留在 [llms 发布证据](releases/2026-10-07-llms-discovery.md)。现有视觉规则见 [UI 规范](ui-rules.md)，本次选择与非目标见 [发布记录](releases/2026-10-09-focused-tracking.md)。旧实时迁移与历史未验证项留在原记录，不因本次任务被视为完成。
