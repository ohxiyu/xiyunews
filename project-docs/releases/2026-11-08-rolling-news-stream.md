# 密集信息流与滚动24小时精选

Issue: https://github.com/ohxiyu/xiyunews/issues/349

- Code complete: yes (local)
- Tests passed: local Python regression passed (unchanged binary brand archives unavailable locally; full remote suite required), Worker npm check passed: 140 tests; full GitHub Python: 1250 passed / 4 skipped; final cache-validator guard adds one Worker test, final-head CI pending
- PR merged: pending
- Deployed: pending
- Production verified: pending

恢复原机器人Logo，所有新闻完整展开；沿用SiliconFlow DeepSeek V3.2评分/扩写、缓存和原配额。既有采集工作流目标5分钟轮询，不保证即时或固定延迟；每轮只发布精选JSON，不重建整站、不发送Telegram。滚动采集使用独立并发组，不取消日报排队；持久缓存按URL/缓存键合并远端最新数据，Git非快进拒绝覆盖。事件AI独立每4小时，固定日报归档及单次投递保留。

滚动窗口读取时排除过期新闻；来源发布时间与采集/精选时间分别显示；稳定链接在窗口外保留。鉴权发布只接受白名单数据，HTML由Worker转义渲染，DO原子持久化与单调写入。无快照明确归档兜底、延迟明确提示。

验证与生产证据待补，不能据此声称已上线。

本地视觉：390px浅/暗色，无横向溢出、正文均可见、无compact折叠、机器人SVG存在。截图位于本次工作区outputs/rolling-news/preview-mobile-{light,dark}.png；仅证明本地外观，非生产验收。

初轮CI: https://github.com/ohxiyu/xiyunews/actions/runs/42483139300 。追加首页条件缓存请求保护：静态shell的ETag/Last-Modified不能控制动态精选；移除请求验证头和响应验证头，避免304保留旧首页。PR: https://github.com/ohxiyu/xiyunews/pull/350 。
