# 2026-10-02 新仓实时服务部署

部署状态：deployed
源码提交：d6a9d3f29ef93c138842342c973b3049fb7bc252
运行版本：2.6.0，systemd fomobtc，MainPID233683、NRestarts0，2026-10-02 20:01:45 Asia/Shanghai启动，current指向新仓完整SHA的独立release；nginx和现役看门狗未修改。
验收结果：源码SHA与公网health一致，三个spot分片live，独立venv哈希安装与pip check通过，SQLite备份integrity_check=ok，仅SOURCE_COMMIT变化；首条自然提醒被Telegram拒绝，无message_id，业务验收未通过。getMe200且Bot有效，但在禁止普通成员发消息的xiyuNews话题群中只为member；迁移前已有43条同类拒绝。看门狗20:10:23/20:15:23两轮自然检查均ok，但不覆盖群Bot权限；手机收件未验证，Hyperliquid既有degraded保留。
回退信息：旧release /opt/fomobtc/releases/b226b625cf3875b6693e0768d75d88d50b33c08d和独立venv保留；root-only备份/opt/fomobtc/backups/xiyunews-d6a9d3f29ef93c138842342c973b3049fb7bc252含runtime.env、SQLite及原路径。没有回滚；回滚须运营者确认，不恢复备份数据库覆盖新发送状态，步骤见根服务器迁移清单。
授权记录：运营者此前明确要求执行整合后的服务器部署；本轮操作时又明确确认生成本机专用SSH密钥并追加公钥。没有更换业务凭据、群组、话题、阈值、地址簿或信源；未授权的群权限和Cloudflare新凭据变更未执行。

## 切换证据与边界

来自新仓main合并SHA的realtime/src、config和requirements.lock与线上旧b226b625提交逐树比较无差异。确认旧实时main为新仓合并SHA祖先，从新仓根目录git archive该SHA realtime，远端strip-components=1解包；只安装独立模块依赖，未混入日报src。先创建独立venv再停服务，停机后使用SQLite backup API保存一致备份，权限0700/0600；仅修改环境中的SOURCE_COMMIT，原子切换current，再由原systemd启动单实例。

环境文件排除SOURCE_COMMIT后与备份cmp逐字节一致，保留原Bot、目标群、话题3/5/7和数据库。新进程预热后三个spot分片live；只读SQLite提取首条自然price_notice事件b6865c8b3031af04ea89cd62942e67f5n，status=failed、error=telegram_rejected、telegram_id为空，未伪造成功、补发或清队列。

getChat/getChatMember只读核验目标为forum supergroup，Bot普通member，默认can_send_messages与can_send_photos均false；这解释了该群对普通Bot消息的拒绝。getMe验证通过，因此不需要盲目轮换Token；应先由群管理员恢复机器人的管理员发消息权限，再观察新的自然事件。既有看门狗主要判断源状态/积压，没有直接检查Bot群权限，未告警也不能作为送达证明。

2026-10-02 20:10:23和20:15:23（Asia/Shanghai）捕获现役看门狗两轮自然Cron执行：均outcome=ok、日志watchdog: ok；只读KV为failing=0、alerted=false、lastAlert=0。这只证明现有看门狗没有发现其规则覆盖的异常，不能推翻自然消息被拒绝的实际结果；群权限恢复后的自然回执仍待核验。20:15:49公网回读三个spot分片均live、SOURCE_COMMIT为新仓SHA，两个新增自然提醒失败后通知failed总数45，sent总数仍1399；不作成功交付声明。

关联：[专用SSH验证](ssh-access-20261002.md)、[服务器迁移清单](../../../project-docs/realtime-server-migration.md)、[根交接](../../../project-docs/handoff.md)、[PR197](https://github.com/ohxiyu/xiyunews/pull/197)。Cloudflare单项目迁移仍未部署，旧资源不提前删除。
