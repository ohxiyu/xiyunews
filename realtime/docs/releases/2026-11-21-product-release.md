# 2026-11-21 xiyu.news 共用发布入口

[任务 #391](https://github.com/ohxiyu/xiyunews/issues/391)统一日报与实时模块的发布和状态查询。实时 API 以 xiyu.news 标识自身。已有东京 systemd、SQLite、Telegram 目的地和外部看门狗继续承担生产职责。发布命令通过各模块健康接口核对同一个审核后的源码提交，报告实时来源的实际降级。

本地以 Python 3.12 验证 61 项测试、Ruff、mypy 和带哈希依赖。原锁中的 aiohttp、multidict 和 Pillow 已更新，复审零已知漏洞。正式部署结果以 [共用发布入口](../../../project-docs/product-release.md) 的回读为准。
