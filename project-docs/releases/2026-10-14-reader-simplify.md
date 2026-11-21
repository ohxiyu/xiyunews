# 阅读入口与分享图精简

## 范围

按 [Issue284](https://github.com/ohxiyu/xiyunews/issues/284) 停用公开周报模块。中英主导航和 PWA 底栏仅保留信息流与追踪，PWA 快捷方式同步移除周报，RSS XML 继续供订阅读者和接口使用。

删除周报定时工作流，CLI 不再接受 weekly，统一部署不再监听周报任务。Jekyll 排除中文/英文周报入口及历史页面；Worker 在缓存之前把旧周报 URL 301 到相应语言首页，保留查询参数。日报发布和无 AI 重建清理旧 sitemap 的周报记录，发布重建同步修正 llms 导航描述，历史归档和旧周报代码/模板保留以供审计，不继续生成和推送。

分享 PNG 只呈现品牌、新闻标题、背景与完整分段正文。背景置于标题下的浅底圆角区域，有明确标签和蓝色侧标识；之后接正文，没有评分、分类、分析、来源栏、参考资料和标签。保持网站配色、440 CSS px 宽/3 倍导出和高度保护；无背景时不造空面板，旧日报通过背景 section 兼容。

## 验证与状态

### 发布出口补充

PR285 已于 2026-10-14 23:41 上海合并为 f5610b12553783ebfe60d58956dd2dda7d1f6fbc，CI38589139515 全部适用检查通过。无 AI 重建 38591505567 正在执行。后续采集仍可能携带旧 llms 描述，因此 [Issue286](https://github.com/ohxiyu/xiyunews/issues/286) 将同一精确文本清理放到 scripts/prepare_edge_assets.py 的最终公共产物复制阶段，覆盖所有发布来源与恢复的构建缓存，不改变不可变输入快照或 RSS；有回归测试覆盖旧快照重复构建。此补充需要新的 CI 与正常统一部署验收。

38591505567 第一次运行在第二个代码下载步骤超过 10 分钟并取消，生产未被替换；已提交第二次重试。东京执行器实测下载一次可达 6 分钟，因此本补充将 Deploy Docs 的总时限由 10 分钟调为 20 分钟，给两次精确下载和无 AI 重建留出空间，保持有界、串行和现有服务/费用设置，不更换执行器。完整 CI 将重新验证该工作流；这是本次正常发布遇到的实际故障修复。

应用分支 agent/reader-simplify，基于 main eef77c30，[PR285](https://github.com/ohxiyu/xiyunews/pull/285)。该阶段完整 Python 1113 项通过、4 项既有条件跳过；117 项前端 Node 与 135 项 Worker 测试通过，npm 审计 0 漏洞，治理/actionlint/diff 检查通过。两阶段 CI 与生产发布现已完成，最终生产结果见下文。

桌面 1440×1000，手机 390×844，英文窄屏 320×844 预览无横向溢出。实际分享：中文浅色 1320×2742 px、英文暗色 1320×3519 px，完整背景先于所有正文段落，无其他附加内容；图片保存通过，没有点击 X 发送。预览用隔离的已发布快照和现有本地 Jekyll 3.9/Liquid 4.0.4（Liquid 单独临时安装）；生产锁定的 Jekyll 3.10 由 CI 构建验收。公开构建中无 weekly 页面，sitemap 与发布 llms 无周报导航。Quick Post 本地动态接口不可用，不冒充生产故障，待生产回读。

- [改前桌面](images/2026-10-14-reader-simplify/before-desktop.jpg)与[改后桌面](images/2026-10-14-reader-simplify/after-desktop.jpg)。
- [手机浅色](images/2026-10-14-reader-simplify/after-mobile-light.jpg)、[手机暗色](images/2026-10-14-reader-simplify/after-mobile-dark.jpg)、[英文320](images/2026-10-14-reader-simplify/after-english-320.jpg)。
- [完整分享PNG](images/2026-10-14-reader-simplify/share-light.png)与[英文暗色分享面板](images/2026-10-14-reader-simplify/share-english-dark-mobile.jpg)。

Source commit: c6814f9c9e3e47012a3d63fdd49bfc8b599766df
Worker version: d7e2c610-2b5d-4c76-beca-8f4df2bf2390。
Deployment: [Deploy Docs38600872805](https://github.com/ohxiyu/xiyunews/actions/runs/38600872805) 成功（56秒），[Cloudflare38601024172](https://github.com/ohxiyu/xiyunews/actions/runs/38601024172) 成功（4分10秒）；Artifact 57b1e476966f0c2ddb4b5615be11462ce8b9a646，Build key 9840aa72c3f08c38a3c0de0f25c7615e3710e480fd8ade03cfccedf2aceed91b。
Verification: 2026-10-15 00:54上海，https://xiyu.news/health status=ok 且精确Source/Artifact/Worker一致；首页、中英追踪、about、developers、10月14日日报返回200且两菜单/canonical/sha256-5267d8be426b正确；中英RSS与crypto-zh XML、sitemap均200，sitemap无weekly，manifest两个快捷方式，llms无周报说明；四个旧中英周报地址301且查询参数保留。
Rollback: 已知健康版本 eef77c30 / Worker 8d340dfc-a146-420e-9d3d-6ab35cc04340；回退需要运营者明确批准，再按原生产流程发布。


## 最终生产验收

PR287 合并为 c6814f9c9e3e47012a3d63fdd49bfc8b599766df，[CI38595850494](https://github.com/ohxiyu/xiyunews/actions/runs/38595850494) 全部适用检查通过；本地完整 Python 1114 通过、4 既有条件跳过，14 项新增发布出口/时限检查通过。两次原10分钟发布失败均发生在下载阶段，没有替换生产；当前新的有界发布成功。失败发布衍生的X任务38593029053和38596668128在发送前取消；依赖PR252的CI38592292414治理已失败，取消剩余检查保留失败记录，未合并该依赖PR。正常调度和真实新闻消息未更改。

生产首页保留两期28条内容，手机390×844宽度390无横向溢出，追踪仍6个重点事件；正文后的分析/参考保持折叠。PWA更新提示由用户操作式按钮刷新，刷新后两菜单/新资源正确。分享实际生成并保存：中文暗色1320×2742，英文暗色1320×3519，所有背景与正文段落完整，没有分析/来源栏/参考/标签/评分/分类，X发送按钮未点击。Quick Post公开只读接口200且当日items=[]；未验收登录后写入，不将本地缺少动态接口视作生产故障。

- [生产桌面](images/2026-10-14-reader-simplify/production-home.jpg)、[手机暗色](images/2026-10-14-reader-simplify/production-mobile-dark.jpg)、[手机浅色](images/2026-10-14-reader-simplify/production-mobile-light.jpg)、[追踪手机](images/2026-10-14-reader-simplify/production-tracking-mobile.jpg)。
- [生产分享面板](images/2026-10-14-reader-simplify/production-share-dark.jpg)、[完整生产PNG](images/2026-10-14-reader-simplify/production-share-dark.png)、[英文手机分享](images/2026-10-14-reader-simplify/production-share-english-mobile.jpg)。

应用、测试、PR合并、部署、生产验收五项均完成。未验证真实iOS/Android安装与未来人为慢网络故障；凌晨15日今日刊期准备中、最新14日属于正常07:26生成边界，不是内容延迟。当前仅按 [Issue288](https://github.com/ohxiyu/xiyunews/issues/288) 合并这些证据，不再触发应用部署。
