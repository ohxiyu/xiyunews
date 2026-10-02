# 单项目迁移基础与旧域清理回读

Task: https://github.com/ohxiyu/xiyunews/issues/196
Source commit: 基线d6a9d3f29ef93c138842342c973b3049fb7bc252；最终head见本任务PR。
Worker version: not changed；既有调度器9774435b-1c72-4dad-9552-0440e2ab574f，统一Worker未部署。
Deployment: 本任务尚未部署；PR195合并不是服务器切换。
Verification: 2026-10-02，旧历史祖先、区域/绑定面板、普通latest与实时health回读、离线回归；真实构建及远端CI随PR补齐。
Rollback: 本任务无生产切换；保留现役服务，不擅自恢复第二Cron。

## 本轮证据

运营者明确确认旧Token撤销后阶段3正常推送为PR195；主站、治理、实时双版本和Pages检查通过后，以merge commit合并为d6a9d3f29ef93c138842342c973b3049fb7bc252。已核验旧main7807126d8c7cdb51e18f0b91ba27f500271f9f08为origin/main祖先，远端有realtime/；无squash/强推，CodeQL因套餐跳过。

按本轮操作时确认删除旧DNS区与三个旧Pages绑定；Safari列表没有bmt.news，仍有xiyu.news及fomobtc.com，生产Pages域绑定只剩xiyu.news。新域latest为2026-10-02、14条；实时仍是旧2.6.0/b226b625cf3875b6693e0768d75d88d50b33c08d、三现货分片live。未删除注册，旧设置不会自动恢复；本机三记录快照不是完整DNS备份。

统一Worker基础默认不开Cron，复用原鉴权/公开路由/dispatcher/watchdog，原DO及KV不重置；准备固定出版SHA构建与默认关闭自动部署，恢复仅重建产物不用AI。94项边缘测试/tsc、看门狗3项、主站951项、原后台和路由51项、资产8项通过；实时3.11初次共享文档夹具缺两条链接导致60通过1失败，复制完整共享文档后61项/ruff/mypy/compileall/契约通过，未绕过检查。治理精确base/head通过；真实Jekyll/dry-run与双版本远端CI以[PR197](https://github.com/ohxiyu/xiyunews/pull/197)为准。

## 未完成

无新Worker/域名/Cron/DO/服务器切换、自然回执或统一生产证据。缺安全Secrets注入、自动部署配置和原可信SSH入口；未新增权限、密钥、收费服务或发送真实测试消息。原开发工具链audit有7项告警，未强制升级或屏蔽，需上线前另行修复并复测。准确切换与验收见 [单项目清单](../cloudflare-single-project.md)。
