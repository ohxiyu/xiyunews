# 第4项：一致性加密备份与隔离恢复

Source commit: 合并后回读，前置6dbc9bffe38db730ad6a300ab4dfcb5146f5792f
Worker version: 本项不改变网站运行代码，前置统一发布38388839156待验收
Deployment: 备份定时器/首次运行、Encrypted Backup工作流和隔离恢复待合并后实施
Verification: 离线SQLite WAL已提交数据/pending/sent/unknown均保留，SHA/表计数与损坏检测通过。完整应用回归与当前CI尚待完成。真实生产备份、异机取回与解密尚未验证。
Rollback: 不覆盖或恢复生产数据库。若备份异常可停独立备份timer；原数据库、服务和凭据不变，任何真实回退另行授权。

使用SQLite在线backup API逐库生成一致性副本，主日报与实时数据库分别独立，不假装两个系统是单个跨库事务。清单包含SHA、表计数、时间和脱敏部署版本；不读env/私钥/消息内容。压缩后用现有运营者SSH公钥通过age加密；私钥只在本机。不增加Secret、服务器、套餐或配额。

服务器03:20上海运行（最多2分钟随机偏移），保留7个独立加密版本。GitHub03:45上海工作流只读取加密导出，验证格式/时间/大小/SHA后保留3天，每份上限8MiB；超出预算停止导出，不购买扩容。既有Git生产/队列分支仍为独立审计及异机快照，本项不手改或重置发送状态。日报SQLite在第9项创建后自动纳入。

安装：先通过严格SSH将现有公钥安装到/etc/xiyunews-backup-recipient.pub（不传私钥），合并SHA导出ops/backup，root运行install.sh。本机age -d -i现有SSH私钥解密到私有临时目录，验证SQLite integrity_check、manifest哈希和表计数；绝不启动应用进程。只有加密副本复制到执行器可读的backup-export，原实时DB继续保持执行器不可读。
