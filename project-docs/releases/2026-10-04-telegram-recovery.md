# 2026-10-04 Telegram 日报安全补推

Issue: https://github.com/ohxiyu/xiyunews/issues/208

## 范围与授权

运营者授权正常补刊并确认机器人已加入目标日报频道。本次只补回原正常日报run37174775715明确403而未发出的消息，不以测试消息替代真实日报。独立branch `agent/telegram-daily-recovery`，唯一编辑负责人当前Codex；基于main97241d5c。前次[调度与网站恢复证据](2026-10-04-daily-delay-recovery.md)保留。

## 实现

- main专用手动workflow `telegram-recovery.yml`，默认只检查，仓库/Actions仅read权限；只注入既有日报Bot/频道Secret，不加入任何AI、X、Square或Cloudflare密钥。
- 验证原始日报workflow/main/completed与当次报告artifact；只接受唯一明确bot-not-member403，且零成功发送；当前刊期、时区、条数及updated_at必须匹配报告date/started_at。拒绝旧刊期、改过的刊期及不明确的网络失败。
- 使用[getMe、getChat、getChatMember](https://core.telegram.org/bots/api#getchatmember)确认是channel、配置中的Bot是administrator且can_post_messages=true。不会改权限或打印token/chat ID/HTTP异常URL。
- 补推沿用既有紧凑HTML：前三条完整首句，后续仅标题，最多10条；12条刊期另2条从完整日报链接阅读。排名、内容不重写。
- 每刊期串行；send=true任何已有调用都拒绝第二次（含失败/取消），run_attempt>1也拒绝。全页读取工作流历史而非前100条。取消/超时后须人工核对，不能认为exactly-once；无平台幂等键，历史运行删除也会破坏保守屏障，不应删除该工作流的发送运行。
- POST前留outcome_unknown检查点；仅SUCCESS且有效message_id认定sent。脱敏回执artifact90天；屏障依靠工作流历史，不依靠artifact期限。无自动重试、持久分支写入、新队列/付费服务、Worker部署。
- 原日报自动发送逻辑不变，仅返回值新增可选message_id。修正配置手册中建议force_publish测试Telegram的旧说明（已经发布时原实现不发送）。

## 验证状态（提交时快照）

- 代码：complete；依赖frozen dev通过，Telegram mock测试35项通过；完整pytest1040项通过，既有google-genai/Python3.14弃用警告1条；治理及diff检查通过。远端CI待补充。
- PR合并：pending；上线：pending（Actions入口，无Worker部署）；真实权限/发送：pending。不将运营者“已加入”当作API权限验收。
- 未验证：真实手机收件、明日07:26自然出刊；原Crypto6/9与EN脉络缺失仍独立，不改本次内容质量策略。

## 操作与回退

合并且CI通过后，在main手动检查date2026-10-04/source_run_id37174775715/send=false，权限通过再单次send=true。不得重新运行日报、force_publish或手写队列。若权限不通过停止并告知运营者；若send已尝试但无回执，人工检查频道，不能自动重试。

回退代码可revert本PR，不删除已有Telegram消息或恢复工具运行历史；回滚不等于撤销渠道发送。后续部署和验收证据按[协作规则](../codex-collaboration.md)以独立文档PR补齐，不直接提交main。
