# fomobtc.com 跳转到 Telegram 群组，群组成员只读

用户 2026-09-25：“把 fomobtc.com 指向telegram群组。然后还需要设置权限不能让成员发言。只能看。”

## 群组
- 群组 fomobtc（-1004364162227，已开启话题）默认成员权限改为只读：发消息、各类媒体、投票、链接预览、改群信息、邀请、置顶、管理话题全部关闭，仅保留表情回应（can_react_to_messages）。机器人为管理员，推送不受影响。
- 机器人创建专用邀请链接（名称 fomobtc.com）：https://t.me/+mdTufn9GK1UyODk0 ，不作废群内其他链接。

## 域名
- scripts/deploy/redirect：同名 Worker `fomobtc` 替换已下线的静态前端，对 fomobtc.com 任意路径返回 302 到上述邀请链接（302 便于以后更换链接）。沿用原 custom domain，未改 DNS；api.fomobtc.com 不受影响。
- 部署：wrangler deploy，Version ID c165e6c5-f2c9-4fab-a29a-c42089452c13。首次请求在域名绑定更新期间失败一次，随后本机与东京均返回 302 https://t.me/+mdTufn9GK1UyODk0（含子路径）；api.fomobtc.com/api/health 200。
- 该 Worker 现在承担跳转，不应再按前端下线记录删除。
