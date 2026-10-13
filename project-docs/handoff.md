# 当前交接

当前 Issue240：修复运营者报告的 www.xiyu.news 入口故障，代码已准备，尚待 CI/合并/部署。用户明确要求修复，授权仅覆盖 www 必要绑定/DNS 和同功能发布，不改主域、API、Access、Cron、密钥及实时服务。后续阅读层次 UI 使用独立串行 PR；不继续旧的消息验收任务。

<!-- execution-pointer -->
```json
{
  "goal": "修复 www 入口并保留路径查询统一 301 到主域",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/240",
  "owner": "当前会话，唯一编辑与发布整合负责人",
  "branch": "agent/www-entry-fix",
  "last_verified_commit": "6a1b99b0f1c0d742e624d994d49853a999076c89",
  "pr": "PR 待创建",
  "completed": [
    "独立 worktree，原工作区未提交文件保留",
    "www 统一 301 处理先于私有接口/资产/缓存与运维路由",
    "现有 Worker 声明新增 www Custom Domain，主域/DO/KV/Cron 不变",
    "29 项主机 Node 跳转测试及 130 项 Worker/type/audit/dry-run 通过"
  ],
  "unfinished": [
    "完成 Python 全量/CI、同步 main 后合并、授权部署与 www 自然 DNS/TLS/301 验收",
    "随后独立 PR 调整背景、正文、影响分析及参考资料阅读层次"
  ],
  "validation": [
    "主域首页 200、health ok；www 证书覆盖但 HTTP520/HTTPS522",
    "Cloudflare 只读实际 Custom Domains 仅 xiyu.news→xiyunews；没有另一个同名 www Worker",
    "新增/旧域/相似域/运维/后台/查询参数转义跳转测试通过"
  ],
  "unverified": [
    "www 新绑定与最终 301 尚未部署",
    "其他阅读层次 UI 尚未实施"
  ],
  "production": {
    "source_commit": "6a1b99b0f1c0d742e624d994d49853a999076c89",
    "artifact_commit": "39457be860c590f21b1de4983af1470b795759f3",
    "edition": "2026-10-13",
    "generated_at": "本任务不采集或生成新闻，仅读取既有出版",
    "worker_version": "d18c6c94-0120-4523-9ab4-15f1c0d4a134",
    "verified_at": "2026-10-13 11:07 Asia/Shanghai，HTTP/health 与 www 入口诊断"
  },
  "blockers": [],
  "next_action": "完成只读 changeset 检查、全量/CI，同步 main 后合并并经统一流水线部署；只改 www 必要绑定/DNS。不改变 Access/Cron/密钥/主域/API/旧品牌。",
  "states": {
    "code": "complete",
    "tests": "pending",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-13-www-entry.md"
}
```

上轮双话题已上线，真实消息验收仍保留在 [原发布记录](releases/2026-10-12-telegram-group-topics.md) / Issue238；它不是本轮补发或通知授权。
