# 第6项：发布去重与校验产物复用

Source commit: 合并后记录，前置695c0fa3d980ab30dd61092150a95aad966d5153
Worker version: 首次发布后回读，目前7c0f3e05-92a8-4bfc-937c-4bbbbf5b7c39
Deployment: 当前PR通过后统一工作流部署，再分别验收同版本快跳过和force_deploy修复
Verification: 1098应用测试/135Worker测试/类型/actionlint成功；不可变输入变化失效、故障强制发布和全文件完整性通过。生产节约耗时与cache命中尚未验收。
Rollback: 旧Worker7c0f3e05；必要回退另行授权。缓存异常自动重新构建，不手工改gh-pages或发送状态。

build key包含实际gh-pages完整SHA与公开源码、构建程序、配置、锁文件和发布工作流的Git对象哈希，文档记录不导致无效构建。现役health为正常且build key/artifact完全一致时快速结束；故障恢复明确force_deploy=true，不能被快跳过阻挡。该流程不调用AI或重刊。

渲染结果仅在主分支统一生产工作流里保存到既有Actions缓存；分支隔离遵循[GitHub官方规则](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching#restrictions-for-accessing-a-cache)，生产不读取PR专属缓存。无模糊restore-key，命中仍验证完整文件集与每个SHA，异常拒绝后重新构建；先完成公共输出验证再保存。原npm/pip安全检查保留，无新配额。当前使用约1.07GB；总缓存<3GiB才保存新的渲染，否则继续正常发布。缓存清单不发布到读者网站。

新增独立生成的Ruby Gemfile.lock，平台覆盖Linux/macOS并包含依赖校验和，原工作区用户未跟踪Gemfile.lock未动；代码依赖与构建键保持精确。Ruby3.3/uv0.11.32/Node24/npm11.11.1既有运行边界保留。完整UI/刊期、主题、推送回执无变更。

实际进度：PR271合并eeb9a4641c0a6a7333a92adb6855bed26b8998d4，完整CI38392618155成功。首生产38393741292success，Worker a553648b-755f-4c92-aefc-26fa2573cc9b/source eeb9a464/artifact cd1b66613bd72f3a51622425565bc1b9775c34f1/build key a2df60e249201d799165410ba8d8cc6d36a4a701742db91a1a5d02587f4dac0c已回读。相同版本快跳过38394412431在验证，强制缓存修复随后单独验收。
