# 当前交接

当前 Issue243：修正 www 外部托管 DNS 与 Custom Domain 的冲突，改用精确 Worker 路由复用现有记录。不删除 DNS、不改凭据/主域/Access/Cron/API/实时服务。UI242 自有更改已精确 stash，当前只编辑域路由及证据，完成后恢复 UI。

<!-- execution-pointer -->
```json
{
  "goal": "保留 www 外部托管 DNS，添加精确 Worker 路由完成 301",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/243",
  "owner": "当前会话，唯一编辑与发布整合负责人",
  "branch": "agent/www-proxied-route",
  "last_verified_commit": "c1595aa900e5fc77ba85e2ad5d189c5883f9d7c0",
  "pr": "https://github.com/ohxiyu/xiyunews/pull/244",
  "completed": [
    "PR241 已合并，主域 Worker 跳转代码已上传且健康正常",
    "已定位实际绑定错误100117：www 的 DNS externally managed，未删除或覆盖任何记录",
    "将 www 改为精确同区 Worker 路由，原主域 Custom Domain/DO/KV/Cron 不变",
    "UI242 未发布改动保存在自有 stash，未丢弃"
  ],
  "unfinished": [
    "路由 CI/同步 main/合并/授权部署并验收 www 301",
    "随后恢复 UI242 自有 stash 并完成预览、CI、上线"
  ],
  "validation": [
    "PR241 的 1063 passed/4 skipped、130 Worker、29 主机跳转与 CI 全通过",
    "changeset 预览显示 conflicting=[]，实际部署却100117；记录两者，不将预检当成功",
    "主域 health=ok/source=c1595aa9，www仍未验收"
  ],
  "unverified": [
    "精确 www 路由未部署；不声称已经修复",
    "UI242尚未上线"
  ],
  "production": {
    "source_commit": "c1595aa900e5fc77ba85e2ad5d189c5883f9d7c0",
    "artifact_commit": "f45d2392d6e654906ea0c4bbee706241ed9c74cc",
    "edition": "2026-10-13",
    "generated_at": "本任务不采集或生成新闻，仅读取既有出版",
    "worker_version": "9358c8e3-9103-46f0-a7db-0fd2c2d7ea98",
    "verified_at": "2026-10-13，部署日志100117与主域health只读回读"
  },
  "blockers": [],
  "next_action": "核验精确路由无已有其他 Worker，完成测试/CI/main 同步后部署，不删除 DNS、不改权限或密钥；成功后回到 UI242。",
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
