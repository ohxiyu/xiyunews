# shadcn/ui 紧凑展示

Issue #13：React/Vite + shadcn/ui 官方生成的 Table、Button、Input、Badge，组件源码保留在 web/src/components/ui。复用现有采集 API 与实时控制器，26px 行高、顶部统计文字、固定表头、表内滚动，详情原位展开。后台和阈值未改变。

验证：10000 消息限频和暂停恢复检查，Vite 生产构建；部署证据随后记录在本文件及 PR。

2026-09-14 线上验收：前端 d03e4293858254271d6a6c57d2e60df2355f2c28，Worker 677b119e-408b-46a6-a03c-b818c340d192，https://fomobtc.com 。浏览器显示94条累计记录和真实表格；842px窗口表格起点73px、行高26px，390px手机页面宽度与scrollWidth均390，表格起点118px。暂停/恢复、展开、现货筛选及状态页通过。数据源状态保持真实降级提示。JS 主包 gzip 81.35kB、控制器3.99kB、CSS4.89kB。回退可重新部署 f7c1721 的前端。后端版本与数据库未改。
