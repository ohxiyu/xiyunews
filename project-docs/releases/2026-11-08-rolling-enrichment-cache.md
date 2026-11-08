# 滚动精选扩写缓存键修复

Issue: https://github.com/ohxiyu/xiyunews/issues/353

- Code complete: complete (local)
- Tests passed: local focused regression passed; final CI pending
- PR merged: pending
- Deployed: pending
- Production verified: pending

真实第二轮42491773016成功但扩写14条全未命中。ContentEnricher会把评分标签ai_tags改为生成的editorial_tags，原store_enrichment在调用后计算缓存键，导致下一轮的原始评分标签查不到结果。修复在调用前复制输入，结果仍保留全部生成标签、正文和背景，但用实际输入的键保存。输入/模型/提示词变化仍自然失效，不放宽缓存条件，不改模型/配额/密钥/调度。

新增回归跨磁盘重载缓存：同一来源与分析输入第二次不调用AI且恢复输出标签，分析标签改变仍重新调用。生产证据待补。
