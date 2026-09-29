# X 模板帖截断

- Issue: [#150](https://github.com/ohxiyu/bmtnews-standalone/issues/150)
- Branch: `agent/x-template-truncation`
- Scope: `src/services/x_delivery.py` 的截断逻辑（`truncate_weighted`、`_first_sentence`）。AI 撰稿、数字校验和发送流程不变。

## 问题

2026-09-29 第一条 X 帖的 AI 稿因 `unsupported_figures` 未通过校验，回退到模板帖。模板导语按字数硬截断，已发出的帖子结尾是「……交易所已处理9585笔提现订单，合计4098.…」。

## 变更

| 项 | 内容 |
| --- | --- |
| 截断 | 退到最近的分句处（，；：、或空格），且保留至少一半内容 |
| 无分句处 | 丢掉被切断的数字或单词，再加省略号 |
| 影响范围 | 模板帖导语与正文、日报汇总帖标题、周报 X 文案（都调用 `truncate_weighted`） |

## 验证

- 新增回归测试：2026-09-29 原文不再出现「4098.…」，且任何截断都不以数字、字母或小数点紧接省略号结尾。
- `uv run pytest` 全部通过；`uv run python scripts/check_governance.py` 通过。

## 尚未验证

- 下一次模板回退时的实际帖子文案。
