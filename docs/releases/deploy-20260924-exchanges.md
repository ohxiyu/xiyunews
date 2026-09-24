# 2026-09-24 2.2.0 多交易所与两级分类部署

部署状态：deployed
源码提交：bf62c640191cd08e0b447a6d4ba88f4c1bb182b1
运行版本：后端 2.2.0 systemd fomobtc，PID 162572；前端 Cloudflare Worker 版本 a446f4a5-412d-40e3-83f7-a247bc736a96，config.js revision 为同一 SHA。
验收结果：2026-09-24 23:23（北京时间）切换；公网 health 为 2.2.0/bf62c64，telegram_enabled=true；Bybit/Bitget/KuCoin/HTX/Bithumb 公告及 Upbit/Bithumb/Gate/MEXC 交易对全部 polling（855/493/2222/1837 个市场），币安官方流 live；首轮 5677 条基线，无待推送积压。网页两级分类与交易所标签线上可用。发现交易对基线占满“全部交易所”，由本 PR 修复。
回退信息：后端上一 release 290d373edc73babebb995abe54c122cc954f3aac 与备份 /opt/fomobtc/backups/20260924T152310Z-before-bf62c64（SQLite integrity ok、env、previous_release）；前端上一版本 e86d3aef-1fe7-4f03-852b-a91d0991a6da。
授权记录：用户 2026-09-24 “一次性全加上，然后在ui要调整一下”；未新增密钥。
