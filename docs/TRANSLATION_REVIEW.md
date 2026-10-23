# 全部英文清单译文与遗漏来源审校

## 检查范围与结论

本轮只读检查 `strings-documents.json` 和 `strings-ui-items.json`，合计278条，对照第一阶段原始英文清单。没有改动这两个翻译文件。

- 已验证：278个唯一ID，无重复、遗漏或空target；原metadata一致；保护token顺序、换行序列和空行位置均一致。
- 已验证：37条target与source相同，均为制作人员姓名、机构或专名，属于有意保留，不计正文漏译。
- 已验证：`examine.509`数字串`0 8 1 3 9 9`，`examine.538`数字串`11 6 25 10`，照片碎片`10`、`31`、`07`及`examine.514`中的 E 对应关系保留。
- 278条覆盖的是当前识别出的英文表格/文档记录，不等于游戏全部可见/可听内容已汉化。视频、纹理和音频单独审计，见下文。

## 具体修改建议（交主维护者决定并统一应用）

| ID | 发现 | 建议 |
|---|---|---|
| `loc/en/item.043:0000` 与 `loc/en/examine.520:0000` | 同一 guard tower 分别为“岗楼”和“瞭望塔” | 两处统一为“岗楼”；该物品的取得地与书上目的地应一眼对应，避免玩家以为是两处地点 |
| `loc/en/examine.519:0000` 与 `loc/en/examine.013:0000`、`loc/en/item.044:0000`、`loc/en/map.tbl:0004` | 同一3rd floor出现“3层”“3楼” | `.519`统一为“西楼3楼”，其余地图仍沿用1楼至7楼 |
| `loc/en/UIOptionsNew.tbl:0002` | 在“Inverted/Normal”这组输入轴选项中，Normal译“普通” | 建议“正常”，与“反转”构成有意义的方向设置；不连带更改普通难度 |
| `loc/en/UIOptionsNew.tbl:0018` | QUIET译“轻微”，是心跳声音量档位 | 建议“轻声”或“低”，与正常/关闭搭配；主维护者须统一该组三档语义 |
| `loc/en/UIOptionsNew.tbl:0027` | Last Save译“读取存档”较偏行为而非原文名词 | 建议“最近存档”；如实际按钮含“从最近存档恢复”语义，可用“读取最近存档”，待手动UI确认 |
| `loc/en/open.002:0000` | keypad译成“密码锁”，与文档里的键盘实体不完全一致 | 可改“由密码键盘控制开锁。”，保持次行“密码会是什么呢？”；并非阻塞项 |
| `loc/en/examine.535:0000` | “经历了某种记忆闪回，起因是我放上了那张唱片”准确但较机械 | 可顺为“这台留声机竟让我想起了某些往事。我刚放上那张唱片，就……真奇怪！”；如改写仍须保留四个控制码顺序和三行结构，不擅自加强剧情结论 |

## 诊疗与剧情用语复核

- 寄生虫妄想症、精神分裂症、解离性漫游症、慢性失眠症、精神运动性激越、痢疾、慢性偏头痛、人格障碍、抗精神病药物及抗抑郁药物，未发现明显语义颠倒。
- `examine.526` Monomania暂译“单一妄想症”；`examine.541` Moral Insanity与Focal Infection Treatment分别为“道德性精神错乱”“病灶感染疗法”。这些是游戏历史化病历语言，保留原意，不改写成现代诊断。
- `examine.539` Malay Root暂“马来根”，具体植物仍未知；不能擅自猜成另一种药材。
- `examine.544`放克音乐玩笑保留，Future Funk译“未来放克”，没有误当成真实病名。
- `examine.046` Amanda使用《病房2》“阿曼达”，母亲信件的 Daddy/Mommy对应“爸爸/妈妈”；未把母亲的话改写成已确认剧情结局。
- John/Jane Doe译匿名男/女病人，其他病历姓名保留Latin，制作人员原名不被替换为剧情人物。

## 278条之外的来源审计

审计命令：

```powershell
python -X utf8 tools/audit_text_sources.py --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --out build/full-research/text-source-audit.json
```

本地报告包含源资源名、SHA-256、可打印候选偏移；报告保存在Git忽略的build目录，避免提交完整原文或素材。

### stringpool：已验证为技术名称池，而非新增台词表

`CONTENT.TAR/stringpool`原长2624字节。第一层header为`(2600,2611,2624)`，第二层为`(7272,2585,2600)`，每层header后均为可解的zlib；解开后7272字节。

以长度至少4的ASCII串扫描得到232个候选：前`0x728`之前6个候选是二进制数字字段的偶然可打印组合；`0x728`起226个为纹理、动画、按钮、地图图元、谜题字母和数字控件的技术标识。抽查和全集阅读未发现完整玩家句子或字幕。

| 解开后offset | 候选 | 分类 |
|---|---|---|
| `0x728` | `357_bump.tga` | 材质纹理名 |
| `0x750` | `alphabet_bg` | 字母谜题背景标识 |
| `0x7C0`–`0xA7C` | `alphabet_letter_a`…`alphabet_letter_z` | 谜题字母资产ID，不能翻译ID本身 |
| `0xA98` | `anims/menus/button` | 动画路径 |
| `0x10D0` | `elevator_floor_1` | 电梯楼层图元ID |
| `0x195C` | `Save_YesNoButton` | 菜单控件ID |
| `0x1C58` | `YesNoButton` | 菜单控件ID |

技术ID不能作为漏译正文写入locale；其指向的纹理仍可能含有玩家看到的英文字样，需要视觉审计。

### config：65个文件，未发现新增玩家正文

已只读逐项扫描65个`config/`文件，包括空文件。内容为INI键值、关卡/场景ID、难度敌人参数和技术注释。`config/game.ini`里的`StartSection*`、`SkipIntro`、`DrawDistance`等是逻辑配置；`config/cinema.ini`里的`StartCinema*`是过场资源选择。没有发现应添加到中文文本清单的标题或句子。配置中的调试入口、起点和难度数值不应随着翻译修改。

### MOVIES：34组DAT/IVF/OGG，当前文本覆盖率不包含过场

- 已验证：34个DAT全部符合`size = 24 + 24 × header[4:8]`，该字段是相同结构下的记录数。它们没有长度至少12的ASCII可打印候选。仅根据这一点，不将DAT认定成字幕表，也不把猜测字段意义当事实。
- 已验证：34个OGG资源开头均为`OggS`，与同名IVF和DAT组成34组媒体。资源名包含`AMANDA01/02`、`NEWSCAST`、`INTRO`、`FINAL`和`CHAPTER01`至`CHAPTER16`。
- 未确认：OGG是否含可懂对白、新闻播报，IVF是否含烧录英文字幕、章节标题或场景文字。不能以扫描未命中ASCII代替媒体内容验收。
- 高置信推测：DAT为媒体逐帧辅助数据而非可直接翻译的字符串；确切字段须后续独立验证，不改写它。
- 待办：对视频关键帧和音轨进行离线内容审计；若含对白或画面正文，需要可复现字幕/纹理方案。不得因278条文本已齐就宣称完整游戏汉化完成。

### 其余覆盖边界

本审计没有穷尽EXE硬编码提示、Steam叠加层、运行库系统对话框、场景纹理、章标题图片和隐藏剧情文本。主维护者应合并EXE与纹理审计结果，并将确定的玩家文本计入覆盖率分母。未启动游戏；离线检查不等于手动通关或画面验收。

## 可复现检查结果

`TEXT AUDIT records=278 missing=0 structural-issues=0 stringpool-candidates=232 config-files=65 movie-DAT=34 movie-OGG=34`

工具配套6项合成测试覆盖双层zlib、无容器保留、长度失配拒绝、候选偏移及token/换行差异检测。


## 后续落地核验

已重读当前locale核验：Guard Tower统一“岗楼”、`.519`统一“西楼3楼”，UIOptionsNew的反转对照Normal改“正常”、QUIET改“轻声”、Last Save改“最近存档”。上述五项已落实，不再作为未修复缺陷。其余语气建议仍属非阻塞风格建议。

本页最初记录的遗漏来源随后已独立调查：内层507图片审计见`docs/INNER_TEXTURE_AUDIT.md`；34电影音轨与疑点变体见`docs/MOVIE_AUDIO_AUDIT.md`；全部177 FLAC无VAD与全部新词候选大模型复核见`docs/AUDIO_SUBTITLE_AUDIT.md`。仍保持278表格/文档记录与图像/音视频字幕分开计数，不把单项覆盖率冒充全游戏实机验收。
