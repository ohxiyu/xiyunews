# 单仓合并与统一边缘入口准备

Issue: https://github.com/ohxiyu/xiyunews/issues/196

PR195已merge commit合并为d6a9d3f29ef93c138842342c973b3049fb7bc252，旧main7807126d8c7cdb51e18f0b91ba27f500271f9f08是新main祖先；旧Token撤销已明确确认。新xiyunews入口复用看门狗，只把运维正文品牌改成xiyu.news，规则/私聊目标/STATE KV/频率不变，3项Node测试通过。

服务器仍为2.6.0/b226b625cf3875b6693e0768d75d88d50b33c08d、三现货分片live，没有新仓部署或自然message_id。新入口默认无Cron，不退役旧watchdog/仓库/数据库；安全配置、SSH缺口与切换步骤以 [根交接](../../../project-docs/handoff.md) 和 [单项目清单](../../../project-docs/cloudflare-single-project.md) 为准。

同日继续执行时再次回读仍是上述旧SHA、三个现货分片live。统一Worker的Node开发工具链安全修复后audit为0、94项边缘及3项看门狗测试通过；未改变实时Python依赖、规则、数据库或Telegram目标。默认SSH别名与主机已知指纹缺口仍在，新仓服务器和看门狗品牌版本都没有上线，不以测试或代码合并代替实际自然推送验收。
