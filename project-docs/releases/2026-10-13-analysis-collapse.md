# 正文后的分析与资料默认折叠

Issue: https://github.com/ohxiyu/xiyunews/issues/248。当前会话唯一 owner，分支 agent/analysis-collapse，基于 main 36cc79258b196146fcf74e23137ff076db7c7515。运营者要求截图中的正文后资料恢复折叠，保持背景在上和当前 UI。[PR249](https://github.com/ohxiyu/xiyunews/pull/249)。

## 改动

阅读顺序不变。背景保留三行可展开预览，正文完整显示，影响分析、真实讨论、参考资料与标签合并为默认关闭的原生 details。摘要只列存在的栏目，显示加减号，支持点击、Enter/Space 与屏幕阅读器；展开后沿用共享字号、色彩与双列/手机单列资料。没有附加内容时不造空面板。旧日报与动态事件共享增强器且幂等，新 Python 与事件 Liquid 输出无 JS 也可展开。分享提取读取全部资料，不因折叠丢内容。

只改 UI 与静态渲染，不改资讯、排序、来源、AI、推送、后台、DNS、Access、运行凭据或 Cron。资源指纹更新为 sha256-d7ce605479ae，用户 PWA 阅读数据保留。

## 验证与发布

Source commit: pending；开工基线 36cc79258b196146fcf74e23137ff076db7c7515。
Worker version: not changed yet；开工 /health 回读 c49f4b21-cb47-46c2-acfc-afb9a73defff。
Deployment: pending；沿已有 PR→main→Deploy Docs→统一 Worker 自动发布，不人工写 gh-pages。
Verification: 本地应用回归1061passed/4skipped，首次三项治理测试因本轮交接缺少快照字段失败，补齐后单独治理11passed及检查通过；阅读/分享/PWA33项Node通过。真实1280×720桌面、390×844手机/暗色/英文/事件验证默认关闭、点击及Enter/Space展开/收起，无横向溢出；关闭分析时仍生成1320×4176完整分享卡。整站Ruby3.3 Jekyll构建成功，六个静态事件资料默认关闭、背景打开，summary存在。初次临时预览构建的安全真实路径检查在使用/private/tmp后解决，未修改生产依赖。生产验收未完成，不宣称已部署。
Rollback: 不自动回滚或清读者数据，如确需回退先获运营者批准。

视觉对照：[之前直接显示](images/2026-10-13-reading-order/production-desktop.jpg)（1440×1120）；[桌面折叠](images/2026-10-13-analysis-collapse/local-closed.png)、[桌面展开](images/2026-10-13-analysis-collapse/local-open.png)（1280×720）；[手机折叠](images/2026-10-13-analysis-collapse/mobile-closed.png)、[手机展开](images/2026-10-13-analysis-collapse/mobile-open.png)、[暗色](images/2026-10-13-analysis-collapse/mobile-dark.png)、[英文](images/2026-10-13-analysis-collapse/english-closed.png)、[事件折叠](images/2026-10-13-analysis-collapse/events-closed.png)、[事件展开](images/2026-10-13-analysis-collapse/events-open.png)、[完整分享](images/2026-10-13-analysis-collapse/share.png)（390×844）。本地使用既有出版资讯，不重新核查新闻事实；Quick Post本地无法核实仅为快照不含生产API，非新功能故障。

## 外部发布阻塞

2026-10-13 CI [38346104455](https://github.com/ohxiyu/xiyunews/actions/runs/38346104455) 的主项目、路径、治理和整站任务均在执行步骤之前失败，没有日志；GitHub annotation 明确说明近期账户付款失败或支出上限需要增加。没有把未启动当测试失败，也未提升预算、变更付款/计划或绕过必需检查合并。运营者先在GitHub Billing恢复Actions可用状态，再重跑CI；检查通过且同步main后按长期授权合并、自动发布与生产验收。保留本分支/worktree及Draft PR，不提前清理。

最终本地完整回归：1064 passed、4 skipped（39.21秒），33项Node和整站构建及治理/diff全部通过。旧非生产Cloudflare Pages预览检查已通过；GitHub CI仍因账户状态未启动，主站/health回读仍为原c49f4b21版本且status=ok。当前完成代码与本地验证，未合并/未部署/未生产验收。恢复后从PR249当前head重跑CI并核实所测SHA，不把旧SHA检查当当前验证。

## 执行方式恢复后的继续发布

运营者2026-10-13授权已准备方案直接改完上线并优化服务器运行。PR251在东京自托管CI38352364252全部通过后，于13:46:54合并7388457ae407ebf68d00a4c1d9b519c354052cf6。原托管2000分钟/预算0保持，计算已转现有服务器，无新增付费额度；主分支Deploy Docs38353164281已正常启动。PR249同步新main，唯一冲突根交接按实际当前目标改写，保留全部服务器改造和记录；本分支新的完整CI、合并/部署/生产验收待完成，不再要求恢复付款或增加预算。其后证据在本节补齐。
