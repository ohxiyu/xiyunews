# 当前交接

当前目标：[Issue162](https://github.com/ohxiyu/bmtnews-standalone/issues/162) 发布用户已确认的 A「稀有信使」Logo v3。用户本次明确授权写入规范并上线；只替换品牌，不改内容、调度、认证或费用。规范唯一维护在 [brand/logo-spec.md](../brand/logo-spec.md)。

<!-- execution-pointer -->
```json
{
  "goal": "发布稀有信使 Logo v3、写入精确几何规范并同步网站与媒体资源",
  "issue": "https://github.com/ohxiyu/bmtnews-standalone/issues/162",
  "owner": "Codex / brand-v3（唯一编辑负责人及发布整合人）",
  "branch": "agent/brand-v3",
  "last_verified_commit": "6ba4c1c0e087f9e67fd9a302af1751d186adfa54",
  "pr": "https://github.com/ohxiyu/bmtnews-standalone/pull/163",
  "completed": [
    "重建三路径矢量母版，新增 brand/logo-spec.md 单一规范",
    "生成 v3 图标、公开媒体与 ZIP；保留 v1/v2 版本化文件",
    "规范、完整回归测试和桌面/手机/暗色/媒体/分享视觉检查完成"
  ],
  "unfinished": [
    "取得依赖安全处理的独立授权，确认修复路线",
    "安全问题处理后同步 main 并重跑全部 CI",
    "合并 Logo PR、自动部署及公网验收"
  ],
  "validation": [
    "uv sync --frozen --extra dev --offline 成功，锁文件未变",
    "原生 SVG → sharp PNG/ICO → ZIP 构建成功",
    "919 项 Python 测试通过；61 项 Node 前端测试通过；治理与 diff 检查通过",
    "Jekyll 构建成功；1280×720 桌面及 390×844 手机/暗色无横向溢出",
    "媒体浅深色 SVG 正常；分享 Canvas 1320×3045 px，三路径显示正常",
    "远端 pytest / governance / CodeQL / Pages 分支预览通过，但 test job 因依赖审计失败，未合并"
  ],
  "unverified": [
    "扫描报告的漏洞对本项目的具体适用性与修复策略尚未评估",
    "生产仍未发布 v3；Pages 分支预览成功不等于生产成功",
    "存量真实设备图标刷新时机未验收"
  ],
  "production": {
    "source_commit": "unknown; 本次尚未合并",
    "artifact_commit": "1f40fedf (先前 fetch 的 gh-pages，非本次部署)",
    "edition": "2026-10-01（本次替换前公网首页）",
    "generated_at": "unknown; 待正式部署核验",
    "worker_version": "not changed / unknown; 本次不操作独立 dispatcher",
    "verified_at": "2026-10-01 替换前仅确认公开页头及 v2 引用"
  },
  "blockers": [
    "CI 36812520245 的依赖安全扫描失败：现有 pyjwt 2.13.0 与 urllib3 2.7.0 报告 16 项漏洞，其中 CVE-2026-103001 未列出修复版本；必须先处理，不能跳过或强行合并"
  ],
  "next_action": "等待维护者授权先独立处理现有依赖安全问题；保留 Draft PR163 与 work/bmtnews-brand-v3，修复合并后再同步并继续 Logo 发布",
  "states": {
    "code": "complete",
    "tests": "pending",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-01-brand-v3.md"
}
```

## 先前任务保留记录（非执行指针）

上一指针为 Issue160 / Claude Code 的来源清理，代码已随 PR161 进入当前 main，记录见 [来源清理](releases/2026-09-29-source-cleanup.md)。先前未验收项仍保留：Worker 1.1.0 生产部署、PR155/157 线上验收、2026-10-05 周报推送验收；它们不属于本次 Logo 授权，不自动继续。先前声明并不代表本次已核验 Worker 实际版本。开放的历史发布证据 PR 不在本任务范围内合并。
