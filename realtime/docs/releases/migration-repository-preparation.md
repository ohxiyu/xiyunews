# 新仓迁移操作准备

本记录仅说明本地准备，没有服务器部署或 Telegram 改名。Issue 为 https://github.com/ohxiyu/xiyunews/issues/172，旧仓 main 与最新主仓已合入本地 agent/xiyunews-realtime，完整历史待凭据撤销确认后才可上传。

根 942 项 pytest 通过；实时 Python 3.11/3.12 各 61 项测试、ruff、mypy、compileall、仓库契约和 3 项看门狗测试通过。[部署说明](../deployment.md) 补齐原连接核对、新仓打包、独立 venv、停机 SQLite 备份、SOURCE_COMMIT 修改、原子切换、三分片及自然回执查询、看门狗观察和经授权回退；8 个 Bash 代码块及嵌入 Python 语法通过，不代表在生产执行过。

阈值、地址簿、运行代码、依赖锁、systemd 和 nginx 不改动。没有尝试不明 SSH 连接、关闭主机验证、读取或输出私钥、调用实际 Telegram 测试接口、清空队列或更换凭据。只有新仓 SHA、三分片、自然回执和看门狗验收后才可归档原仓。
