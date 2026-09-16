# 阅读型信息流

任务：Issue #31，基于 main 918d0f2。用户 2026-09-16 明确要求前端与 Telegram 并行；参考 bmt.news 的视觉风格。

实现暖白/深色主题、编号事件列表、正文展开、响应式布局；保留来源筛选、搜索、历史分页、自动更新及状态。现货策略和发送队列未修改。

验证：Python 3.12下46项测试、Ruff、Mypy、compileall、仓库契约通过；前端pnpm run check及build通过（本机无npm，使用pnpm安装，未提交其锁文件；CI仍按npm锁文件验证）。新增React服务端渲染测试覆盖HTML转义、官方链接白名单、行情交付状态。浏览器真实API经本地只读代理预览，桌面和390px宽度无横向溢出，深色主题刷新记忆、ZEC搜索、历史50→100条分页、运行状态页通过。预览代理使用轮询，未重新验证生产SSE。

公开健康接口本轮报告后端2.1.0、源码185fabf590abe65cf7f943433d85a9ce69889d13，Telegram关闭；Workbench连接成功，但未完成systemd核验。

代码已推送feat/editorial-feed，实现提交ce70fc10cf292660a8c8bdba77823277c24099a5；[Draft PR #32](https://github.com/ohxiyu/fomobtc/pull/32)。合并：未合并。部署：未部署。Telegram：机器人已创建，未完成配置与收件验收。
