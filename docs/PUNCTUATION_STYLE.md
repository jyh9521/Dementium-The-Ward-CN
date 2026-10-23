# 单句短提示的句末句号规范

## 本轮结果（2026-10-23，已验证）

仅删除 **31 条 target 的最后一个句号**：物品/界面数据29条，混合资源清单中的交互提示2条。完整稳定ID及逐条 before/after 见 [PUNCTUATION_CHANGES.json](PUNCTUATION_CHANGES.json)。source、ID、资源SHA、控制码、原始换行和所有其他字段保持不变。

本轮只对**整个逻辑说明**判断，不对屏幕自动折行或每个物理行单独删标点；标题加空行不算第二句。带内部逗号、句号、问号、引号等标点的说明保持原样，问号、叹号、省略号也不删除。.357口径中的点是小数点，不是句间标点。

## 按实际内容分类，而不是按文件名猜测

`locales/zh-CN/punctuation-style.json` 显式记录131个实际资源的分类，通用审计器不硬编码中文路径或游戏偏移。

- `strings-ui-items.json` 内的 `examine.046` 实际是妈妈写给阿曼达的信，按信件保护。
- `strings-documents.json` 内混有交互文字，不能把整文件当作纸面文档：`examine.515` 的“锁住了。”和 `examine.531` 的“这是一本钢琴曲谱。”属于单句交互提示，此次删除末尾句号。
- 26份真正的纸面文档/病历/谜题，以及1封信和演职员表共85条target，逐条保留SHA-256并由测试校验。原文中“我”的叙述不自动等同于对白；这里只改已确认的物品描述/交互提示。
- 多句说明、文档、信件、诗谜、病历、报纸与对白字幕不做全局替换。

本轮未改动的对白文件SHA-256：

| 文件 | SHA-256 |
|---|---|
| audio-subtitles.json | `57087ecc99d009cacc93c4efe77e7225804f2f78e402bfaacb80dcbe4b7f775c` |
| movie-subtitles.json | `e6de9bccbc078bc76a600ef66a2f092bc61dfcdfcd2371dbd8a2b8940d859c0e` |

## 可复现审计

```powershell
python -X utf8 tools/audit_punctuation.py
python -X utf8 -m unittest discover -s tests -p test_punctuation_style.py -v
```

审计只读：出现遗漏句号时输出稳定ID、before/after并退出1；资源清单漂移或受保护target变化时拒绝。当前输出 pending_terminal_stops=0、protected_targets=85，退出0。

新增测试在改译文前运行5项，其中真实locale门禁失败（待修正31条，退出1）；修改后5项全部通过（退出0）。覆盖控制码、CRLF、标题、口径小数点、多句/内部标点不变、同文件内信件与系统反馈分类、受保护文本漂移拒绝。全量归档重建/回滚及游戏内验收由总体交付流程单独记录，不用本条文本检查代替实际画面验证。

数据维护后应重跑审计；新增资源须先人工分类，新增文档须记录受保护target指纹，不能为了放行测试把文档标为短提示。
