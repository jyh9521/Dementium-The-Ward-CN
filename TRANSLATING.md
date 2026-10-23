# 翻译数据与维护规范

## 当前全量候选

- 主数据为`locales/zh-CN/strings-ui-items.json`与`strings-documents.json`，合计278条。稳定ID采用TAR资源路径与物理行号；241条中文译文、37条姓名/公司按清单保留。术语参考`GLOSSARY.md`及注明commit的《病房2》资料，不凭同系列关系猜测技术结构。
- 维护source、资源SHA、ID、原始换行及控制标记；修改target时保留占位符、颜色标记、谜题字母/数字、资源路径和机器令牌。构建拒绝未知ID、源身份漂移、缺字、超宽与编码错误。
- 译文保存为Unicode；运行时用经本作原生代码离线回放验证的UTF-8/BMP解码及扩展binfont。不再使用POC单字节空槽。自动折行是构建步骤，逻辑段落不改；字库来自全部正文、画面译注与音频字幕的字符集合。
- 原视频不重编码；movie-titles/movie-onscreen-text/movie-subtitles生成运行时解码帧覆盖，修改后重建EXE和覆盖报告，不手改视频。图片标签、影片章名、画面词译注、对白与场内音频字幕分别维护于image-text/movie-titles/movie-onscreen-text/movie-subtitles/audio-subtitles；美术源依赖差分在art/。修改时一并更新对应视觉/音频审计，不猜补无法可靠完整辨读的小字。
- 语音转写状态区分交叉转写共识与高置信推断；离线听辨/识别不等于玩家实际听校。所有字幕时间轴仍待游戏内核验。
- 其他四种原语言仅无损转为UTF-8以保持全局解码合同，原逻辑文字不翻译，也不算中文覆盖率。
- 每次数据变更运行完整合成测试及`tools/record_locale_verification.py`；重新生成本地sample，检查重复构建、未改成员、控制码、字体、原生回放及独立回滚。提交源码/译文/元数据，不提交整游戏资产或含整TAR的差分。

当前工程/离线候选完成不等于游戏流程验收；用户核对步骤见`docs/MANUAL_TEST.md`，明确保留项见`docs/KNOWN_ISSUES.md`。

---

## 历史阶段门禁（保留当时结论）

# 翻译规范与启动门禁

第二阶段只开放locales/zh-CN/probe.json的一条New Game→新游戏；逻辑译文保持Unicode，显式slot映射只在构建期使用。字槽有限不用于全量汉化；详见docs/TEXT_DECODING.md。下列第一阶段清单仍不批量回写。

本阶段只建立技术清单，不全量翻译。未来译文放在 `locales/<locale>/`；工具与语言数据分离。

- 由 `tools/investigate.py scan` 生成 `build/phase1/text-en.json`，当前target为空；源原文清单只在本地保存。
- 稳定ID使用实际TAR成员路径及物理行号；保留资源哈希、字节位置、source、控制码、标记、原空行和换行。重复原文不自动合并上下文。
- `capacity_bytes=null`表示未知，不表示无限制；不得套用《病房2》容量或像素预算。
- Latin-1只用于原始字节可逆清单，完整中文target尚未开放批量构建；不能为方便直接改成UTF-8后宣称兼容。
- 技术闭环通过后只做New Game一条POC，确认字库、解码、测宽与裁剪，再开展批量。
- 谜题字母、数码、专名、文件路径和命令标记按实际用途保留，不凭上下文猜改。
- 全量翻译前扩展验证：字体覆盖、缺字、运行时容量、链接字符串与各UI布局。离线测试不替代用户游戏内验收。

## 原生调试菜单译文

`debug-menu.json` 独立保存本作21张表的稳定name指针/原callback/源表SHA与306个唯一标签，以及开/关状态引用。表ID、原始source、关卡ID和callback不是译文；仅修改target。标签最多63 UTF-8 bytes，布尔状态最多15 bytes；字符集合自动并入binfont。不要给普通工具添加中文硬编码，也不要替换全局共享true/false原文。详见 [调试菜单](docs/DEBUG_MENU.md)。


## 单句短提示句号与图片证据

[句末规范](docs/PUNCTUATION_STYLE.md)维护显式资源分类和受保护文本SHA。仅无内部标点的单句物品/系统/按键说明去掉最后句号；不能对文档/对白全局替换。原图不清楚时保留原资源，不能用关联文档或清晰同类图补写；[严格图片复审](docs/IMAGE_READABILITY_REVIEW.md)锁住本轮三项撤回资源。
