# 阅读层次：背景、正文、分析与资料

Issue: https://github.com/ohxiyu/xiyunews/issues/242；branch agent/story-reading-order，当前会话唯一 owner，基于 PR244 后 main。运营者要求修复 www 并自行评估/改造阅读结构、合理好用好读；保持信息密度与本站 UI，不新增框架/服务/AI，不改资讯/排序/来源/后台/推送。PR 和正式版本证据稍后补。

## 决定与实现

顺序确定为标题→背景→完整新闻/事件进展→影响分析与真实讨论→参考资料/标签。背景用于建立上下文，在正文前浅底色、品牌蓝左边标识、固定标签及三行可展开预览；正文保持最大的阅读字号与完整段落。分析读完事实后再看，更容易区分报道与判断；独立标为影响分析，不冒充社区讨论，存在真实讨论才显示。参考资料放在读后核查区域，桌面两列、手机一列，链接可读可点击，空字段不造占位。只用一个正文后的轻分隔，避免堆线条或大框挤掉资讯。

共享 JS 将旧的组合 details 分成真实 DOM 上下两组，键盘/屏幕阅读顺序与视觉顺序一致，不用 CSS order。新资讯 Python 输出和事件 Liquid 模板直接生成上下结构；没有 JS 时内容完整保留，新输出顺序正确。所有来源转义与安全 URL 处理不变；分享提取继续遍历 story-more-content 的全部 sections，背景预览不丢全文。旧日、英文、动态加载文章/事件也用同一个增强器，幂等处理，不新增内容推断或 AI。

## www 发布兼容

域故障/完整过程见 [www记录](2026-10-13-www-entry.md)。实际 `www.xiyu.news/* → xiyunews` 已由现有授权 OAuth 创建并回读，未删除/改 DNS。CI Token 无区路由写权限，PR244 的 38343326589 在写路由时报 No access，但代码和主域上传成功；不把工作流失败称完整上线。最终 wrangler 发布配置只留主域 Custom Domain，不声明普通区 routes；Wrangler 没有普通 routes 时不管理或清除运维路由，因此保留已有 www 绑定并恢复正常自动发布，不扩大任何凭据权限。合同测试/运维手册明确这一边界，最终还需完整部署成功后的真实301回读。

## 验证与边界

本地完整 pytest 1064 passed、4 skipped；阅读/分享/PWA Node33项通过。网络mock和历史模板安全测试沿用；最后发布配置修改须再跑边缘合同/CI。真实旧出版 HTML 的离线预览已验证1440桌面、390手机/暗色/英文无横向溢出；背景在正文前、分析/资料在原报道来源后，事件背景在状态前、分析/资料在进展后。键盘Enter展开/收起保留全文，分享1320×4176完整长卡生成成功。测试不发送 X/Telegram 或补历史。

本机默认 Ruby4 缺 csv，未改生产依赖，改用已经安装的 Ruby3.3 构建带当前模板的既有 gh-pages 快照。结果/图片及 CI 正式验收另补；不把快照预览当成正式部署。

相关范围最后回归：Python 1064 passed、4 skipped；130 项 Worker、audit/types/tsc/dry-run、治理/diff 均通过，33 项阅读/分享/PWA Node通过。视口与图片：[桌面改前](images/2026-10-13-reading-order/before-desktop-1440.jpg)、[桌面改后](images/2026-10-13-reading-order/after-desktop.jpg)（1440×1000）；[手机改前](images/2026-10-13-reading-order/before-mobile.jpg)、[手机改后](images/2026-10-13-reading-order/after-mobile.jpg)、[暗色](images/2026-10-13-reading-order/after-mobile-dark.jpg)、[英文](images/2026-10-13-reading-order/after-english-mobile.jpg)、[事件卡](images/2026-10-13-reading-order/after-events-mobile.jpg)（390×844）；[完整分享预览](images/2026-10-13-reading-order/share-dialog.jpg)。图中资讯是既有出版，不代表本轮事实重新核验。

Source commit: 现役4ce04e421c0a53146000b3d339b3636943823ad2，UI未上线。
Worker version: 现役5404da70-69c6-4385-b2e0-2f8ad2c211cf。
Deployment: pending，走已有 main→Deploy Docs→统一 Worker，无AI重建静态产物，不人工写gh-pages。
Verification: UI仅本地预览/测试；www已实际HTTP/HTTPS301并保留路径查询，最终要在正常发布后复验。
Rollback: 不自动回滚/清PWA数据，用户保留原读书记录；若需回滚先批准。
