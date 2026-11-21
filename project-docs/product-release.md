# xiyu.news 发布与运行状态

日报和实时监控共用发布入口。发布命令锁定当前 `main` 的完整提交，日报通过现有 Cloudflare 工作流发布，实时模块通过现有东京 SSH 部署。日报仍由 GitHub Actions 执行，实时服务保持常驻。各自的数据库、投递记录和 Telegram 目的地沿用生产配置。

```sh
python3 ops/release/xiyunewsctl.py status
python3 ops/release/xiyunewsctl.py deploy --ssh-config /path/to/tokyo-ssh-config
```

`status` 显示当天刊期、日报源代码和产物提交、实时模块源代码提交及来源状态。实时 API 的 503 连同来源降级信息会如实显示。命令只读取公开健康接口。

发布从包含生产 `main` 提交的本地仓库运行。GitHub CLI 必须已使用现有运营者身份登录，东京 SSH 配置需要已有的受信主机指纹和部署权限。默认同时发布两部分，也可以指定 `--component daily` 或 `--component realtime`。SSH 主机别名默认为 `xiyunews-tokyo`，可用 `--host` 选择现有兼容别名。已运行目标提交的模块会跳过。日报发布走无 AI 的代码部署，继续使用现有的公开归档。

东京发布先安装带哈希的独立依赖并验证导入，然后串行切换现有 systemd 服务到新版本。实时版本通过公开 API 回读确认。服务仍使用同一个 SQLite 和现有目的地。切换后的启动异常会告警退出，并给出上一版本路径供运营者按[回退流程](../realtime/docs/deployment.md#rollback)处置。一次发布中任一模块失败，命令会返回非零状态。修复原因后，可按模块接续执行。
