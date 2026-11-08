# 滚动精选扩写缓存生产验收

Issue: https://github.com/ohxiyu/xiyunews/issues/353
Evidence issue: https://github.com/ohxiyu/xiyunews/issues/355
Application PR: https://github.com/ohxiyu/xiyunews/pull/354

- Code complete: complete，使用扩写调用前的输入保存缓存，输出标签/背景/正文仍完整保留。
- Tests passed: complete，完整CI https://github.com/ohxiyu/xiyunews/actions/runs/42493308344 ，1251 passed / 4 existing skips，依赖审计通过；新增跨磁盘重载回归证明同输入不再调用AI、评分标签改变仍失效。
- PR merged: complete，0451c6c36b726c80aedefe535bb3654a22fad0b9。
- Deployed: complete，自然采集已加载该提交并成功发布；无需修改Worker或重建网站。
- Production verified: complete，后续实际运行14条扩写全部命中缓存。

Source commit: 0451c6c36b726c80aedefe535bb3654a22fad0b9（采集/精选Python代码）
Worker version: 3bbbb98c-5bdb-4b0f-a3f0-74b1f23b946d，前台源1cbb849a094e10c71276b7a5ed97f70939c40958、资产907ac8b4714ce2211b9719a26d8268c07c7de703，均未重部署。
Deployment: https://github.com/ohxiyu/xiyunews/actions/runs/42493880948 ，15:15Z自然触发，head为0451c6c...，成功发布并持久化正确键。
Verification: https://github.com/ohxiyu/xiyunews/actions/runs/42494382734 ，同一主分支后续正式采集成功，日志15:22:39.464Z明确Reused enrichment for 14 items，仅1条新输入进入评分。
Rollback: 如需回退先获用户授权，用独立PR撤销PR354；不删除旧缓存、不改生成分支、密钥或运行服务。本次未回退。

## 原因与修复边界

第二轮原生产运行42491773016成功但Enriched14/reused0。ContentEnricher将ai_tags替换为生成的editorial_tags，旧store_enrichment在生成后计算键，下一轮使用评分时标签便无法命中。修复在调用前复制输入，结果值保持生成后的完整内容，用实际调用输入计算键保存。旧缓存保留；来源、评分输入、模型、提示词变化仍自然失效，不放宽命中条件、不强制复用旧文本。

首次修复运行42493880948正常建立14条正确键；随后的人工复用验证42494382734使用既有生产流程（采集/精选/JSON发布、不发Telegram），日志显示AI analysis started: 1 items以及Reused enrichment for 14 items。它验证跨运行/持久磁盘复用；自动调度此前已由14:50和15:15自然派发证明。不能把这次人工验证说成自然调度。

## 产品与生产状态

完整前台上线证据见[密集滚动信息流](2026-11-08-rolling-news-stream.md)。原机器人Logo、紧凑全文、滚动最近24小时、真实来源时间、背景、稳定链接及手机浅暗色均已验收。后续公开API与首页仍为14条完整正文和背景，时间窗口/倒序/ID一致且stale=false。

频率为每5分钟目标轮询，执行器排队、源站错误和AI延迟仍可能影响实际出稿；不承诺永不延迟。没有新增服务、模型升级、配额提升或密钥变更。扩写缓存修复不改独立realtime服务和日报/Telegram投递。
