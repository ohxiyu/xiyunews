# 阅读层次：背景、正文、分析与资料

Issue: https://github.com/ohxiyu/xiyunews/issues/242；branch agent/story-reading-order，当前会话唯一 owner，基于 PR244 后 main。运营者要求修复 www 并自行评估/改造阅读结构、合理好用好读；保持信息密度与本站 UI，不新增框架/服务/AI，不改资讯/排序/来源/后台/推送。PR 和正式版本证据稍后补。

PR: https://github.com/ohxiyu/xiyunews/pull/245。

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

## 正式合并、自动发布与生产验收

PR245 已于2026-10-13 11:59:36 Asia/Shanghai同步main后合并305701a18aca68c91b0945d3a873c09571e740c3。GitHub CI [38343910157](https://github.com/ohxiyu/xiyunews/actions/runs/38343910157) 的主项目/治理/路径/整站构建全部success，realtime/CodeQL按已有条件skipped。旧非生产Pages预览0cbeb81c在clone阶段悬停，后返回failure；它已不承载主域，未将其写为成功或用其替代正式Worker验收，不更改其权限/项目。实际网站继续受GitHub整站CI及后续Worker渲染/部署验证，不跳过任一正式流水线步骤。

Source commit: 305701a18aca68c91b0945d3a873c09571e740c3。
Artifact commit: 5b72a32067c87b6110e8ab22476f50b89bcbc13e。
Worker version: c49f4b21-cb47-46c2-acfc-afb9a73defff。
Deployment: [Deploy Docs38344302628](https://github.com/ohxiyu/xiyunews/actions/runs/38344302628) success；其正常workflow_run触发[统一Worker38344355331](https://github.com/ohxiyu/xiyunews/actions/runs/38344355331) success，2m32s、全部步骤通过。恢复正常自动部署，不再额外手动发布/改Token权限。
Verification: 2026-10-13 12:03–12:05 Asia/Shanghai，health source/artifact/version一致、ok、dispatcher/watchdogtrue及原Cron列表不变；www首页/文章/RSS/API301到主域并保留查询，目标200；线上HTML新指纹sha256-10267c5504c6。真实浏览器www→主域保留hash，1440×1120桌面、390×844手机/暗色/英文无横向溢出；旧日报10.12可读且同样上下分层，事件卡背景在状态/完整进展前，分析/资料在后。键盘Enter展开true且全文保留，正式分享1320×4176完整长卡生成。原实时health200、telegram_enabledtrue、spot接收新鲜。未测试真实设备安装（本轮不涉及PWA逻辑改动）。
Rollback: 没有自动回退/清用户阅读数据，www区路由未删；如需回滚代码/绑定先获批准。

正式截图：[桌面](images/2026-10-13-reading-order/production-desktop.jpg)、[手机](images/2026-10-13-reading-order/production-mobile.jpg)、[暗色](images/2026-10-13-reading-order/production-mobile-dark.jpg)、[英文手机](images/2026-10-13-reading-order/production-english-mobile.jpg)、[事件手机](images/2026-10-13-reading-order/production-events-mobile.jpg)、[完整分享](images/2026-10-13-reading-order/production-share.jpg)。旧日期/新增静态数据/分享引用均没有编造内容；图片仅为展示验证，不重新核查新闻事实。

Issue246/branch agent/reading-order-production-record只补本段/其他当前证据/handoff/图片，当前会话唯一owner，不改代码、配置或再次部署。应用五阶段全部complete。自有stash经文件逐项比对与main相同后清理，全部改动在已合并PR/main可恢复；原用户未提交文件保留。旧群消息Issue238与旧Pages预览克隆问题不在本任务补发/修复范围。
