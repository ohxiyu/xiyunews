# 合并与部署授权调整

- Issue: [#148](https://github.com/ohxiyu/bmtnews-standalone/issues/148)
- Branch: `agent/merge-policy`
- Scope: AGENTS.md、codex-collaboration.md 的合并/部署规则；不改代码与生产配置。

## 变更

维护者 2026-09-28 指示「以后不需要单独合并，每次开发完了直接合并部署」。

| 之前 | 之后 |
| --- | --- |
| 默认只交付 PR，合并与部署需逐任务明确授权 | PR 与 main 同步且必需检查全部通过后，整合负责人直接合并，由现有自动部署上线 |

仍需维护者单独批准：强制推送、回滚、手工写 gh-pages/staging-cache/x-queue/square-queue、Worker 部署、密钥变更、新增付费服务或提高额度。

同日按此前授权合并 PR143（f22dc34）、PR145（e10b946）、PR147（858e96c）；PR143/145 触发的 Deploy Docs 均成功。

## 验证

- `uv run python scripts/check_governance.py` 通过。
- 纯文档变更，无部署动作。
