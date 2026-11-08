# 2026-11-08 日报迁移硅基流动

日报AI已配置并启用硅基流动 `Qwen/Qwen3.5-27B`。用户确认创建的专用密钥已保存到仓库Actions Secret，既有客户端在Actions中完成1次真实调用并通过解析与去重校验。当前状态不能代表当期日报已发布或消息已送达。

[应用Issue329](https://github.com/ohxiyu/xiyunews/issues/329) /
[PR330](https://github.com/ohxiyu/xiyunews/pull/330)，正常合并为
7bfde5d22b9b1db60fca17010305f5b3e29515b3。
[证据Issue331](https://github.com/ohxiyu/xiyunews/issues/331)由本聊天Codex唯一编辑与整合负责人维护，
分支agent/siliconflow-activation-evidence，隔离快照work/siliconflow-activation-evidence。
本次仅更新交接与本记录，不直接写main或生产状态分支。

## 接入行为

- 显式siliconflow provider，接口 `https://api.siliconflow.cn/v1`，模型精确为 `Qwen/Qwen3.5-27B`，环境变量 `SILICONFLOW_API_KEY`。
- 日报（含诊断）、采集和X分发四处AI步骤已映射新Secret；向导提供新provider及默认值。
- 按[硅基流动协议](https://docs.siliconflow.cn/docs/userguide/capabilities/reasoning)发送enable_thinking；经济模式简单任务关闭思考，其余任务thinking_budget=4096。最终输出预算不变，不发送DeepSeek官方thinking对象或reasoning_effort。
- JSON与正文请求分开，拒绝空或截断输出，仅返回content。缓存、计量和评分来源使用新provider/model，历史评分不重算、旧缓存不清空。
- 保留PR328账户错误快速失败、并发取消与脱敏提示、质量门槛、刊期、并发和恢复上限。未增加fallback、升级依赖或改动独立realtime服务。

模型选择针对中文新闻分析、指令遵循和长文理解，参考
[27B模型卡](https://huggingface.co/Qwen/Qwen3.5-27B) /
[35B-A3B模型卡](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)；
不声明跨所有任务的绝对最强，也没有生产A/B结论。

## 代码验证

最终应用head41c015f36975f8fc6c14639de43a0e69fdb3f3da的
[CI42449090503](https://github.com/ohxiyu/xiyunews/actions/runs/42449090503)
全部通过：1210 passed、4个既有skipped，47.18秒；pip-audit通过PyPI且无已知漏洞；
治理、web、edge-build、realtime Python3.11/3.12及Cloudflare Pages预览成功。
新增协议、工厂/默认值、密钥、JSON与正文分离、计量、评分来源、缓存隔离、向导、
Secret映射和siliconflow账户熔断回归。首次发现的一处旧provider断言已同步新配置并完整复跑，
未删测试或放宽检查。依赖未变，不更新版本或锁文件。

## 密钥配置与真实验证

用户原要求先交付代码、稍后配置密钥；后续明确回复“GitHub已登录，确认创建并保存”，
授权创建xiyunews-production专用密钥并仅保存到ohxiyu/xiyunews的Actions Secret。

2026-11-08约13:49 Asia/Shanghai，GitHub页面显示“Repository secret added”，
列表出现SILICONFLOW_API_KEY。仅存储在指定GitHub Secret；密钥未写入代码、
聊天、日志或本地文件。未修改旧密钥、其他Secrets、账户权限或余额。
临时读取的密钥变量在保存后已清空。

硅基流动控制台选择Qwen3.5-27B，关闭思考，max_tokens=128、temperature=0.3，
最小JSON提示返回 `{"ok":true}`，界面显示5输出tokens。
这只证明控制台模型可用，不冒充新密钥经应用调用的证明。

随后运行既有
[只读诊断42452591451](https://github.com/ohxiyu/xiyunews/actions/runs/42452591451)，
原任务分支agent/siliconflow-qwen27b，head41c015f，diagnostic_only=true，
trigger_source=siliconflow-api-validation。该诊断读取合并后origin/main配置，
使用工作流传入的SILICONFLOW_API_KEY，并由现有客户端调用API。
job128644794687于2026-11-08 13:55:21 Asia/Shanghai记录：

```json
{"mode":"cached_subset_not_exact_historical_replay","items":20,"batches":[2],"call_limit":12}
{"result":"all_replayed_batches_valid","calls":1}
```

诊断成功，daily-summary明确skipped。实际仅1次调用，通过响应解析和去重校验；
不是只检查密钥名称存在，也不是完整历史重放。未发布日报、重写生产状态、发送消息或重放历史消息。
本次没有扩大预算，上限12为既有诊断限制；不声称真实请求免费。

## 交付边界

应用代码、功能测试、合并和API配置已完成。真实Actions非思考去重请求已验证。
动态评分、扩写、启用思考的真实请求、当期日报生成、公开网站新鲜度及消息送达
尚未作为本次配置验收完成，不把旧网页的health/ready当作新刊健康。
不能保证账户持续有余额或供应商未来不故障。未手工部署Worker或重跑生产日报。

Source commit: 7bfde5d22b9b1db60fca17010305f5b3e29515b3，PR330正常合并；应用head41c015f。

Worker version: unchanged，本次不改Worker；上次90302c66-5a58-4a88-a632-f247214fe6db，未重新核验。

Deployment: API配置已在main与Actions Secret启用；无手工Worker部署，未重发公开刊期。

Verification: GitHub Secret保存成功；控制台返回ok=true；Actions诊断42452591451成功且真实calls=1；当期日报/送达pending。

Rollback: 不自动回退到余额不足的旧账户，不手改状态分支或消息回执；如需回退另按授权处理。
