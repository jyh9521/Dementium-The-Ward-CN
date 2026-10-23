# 《病房2》技术迁移评估（第一阶段）

调查日期：2026-10-23。本文是源码级迁移审计；目标资源验证以本项目原版调查、文件格式及基线报告为准。合成测试通过不构成目标游戏运行或画面验收。

## 1. 来源、版本与许可

- 上游：[jyh9521/Dementium-II-CN](https://github.com/jyh9521/Dementium-II-CN)。只读参考检出：`build/reference/Dementium-II-CN/`（Git 忽略）。
- 锁定提交：`c0ea10f93450972841e510ff82913920339bd058`，提交作者 BLFY，主题 `Update README for v1.1 release details`。
- 上游 `LICENSE` 为 MIT，版权声明 `Copyright (c) 2026 jyh9521`；`CREDITS.md` 将本地化工程与译文归于 Dementium-II-CN 项目贡献者。复用代码或实质片段保留 MIT 声明及上游出处。
- 上游原创译文为 CC BY-SA 4.0；游戏原文、商业美术和字体不是 MIT 授权的游戏素材。完整字体不复制进 Git。
- 已阅读上游 README、TECHNICAL、BUILDING、GLOSSARY、LICENSING、CREDITS、docs/FILE_FORMATS 及实现/相关合成测试。
- **已验证（上游源码）**：上游声明 AppID `5342930`、build `26123896`，兼容配方 `26099941`。这些数字、其原件哈希、677 条文本统计、字体名称及已通关结论全部属于《病房2》，不是《病房》的身份或验收。
- 本项目目标 AppID `3909960`；实际 build、哈希与文件大小由本项目原始资源身份记录独立建立，不通过改写上游 supported-build.json 得出。

## 2. 逐模块迁移结论

“原样复用”指对应函数的实现逻辑在满足格式前提后无需重写，不表示整个带 CLI 的文件和配置都可照搬，也不意味着已经在本项目导入所有功能。

| 上游模块 / 函数 | 迁移决定 | 前提与必要修改 |
|---|---|---|
| `localize.py`: `digest`、`filehash`、`write_json`、`Entry` | 原样复用候选，已验证源码为通用实现 | Python 3.11+；JSON UTF-8/LF；不附带任何游戏身份常量 |
| `localize.py`: `Zar.__init__`、`read`、`rebuild` | 优先按函数原样复用 | 目标实包必须满足 ZAR1、排序 ASCII 名、512 对齐、24-byte TOC、未知字段为零等守卫；不放宽守卫“兼容”未知变体。rebuild 是追加保留式而非压缩重排，空修改保持整包一致 |
| `localize.py`: `index_rows` | 优先原样复用 | 目标 `~INDEX` 必须证实为 u64 count、16-byte `<IIQ>` 记录及相对字符串池；名字大小写映射、flags 与大小关系需独立核验 |
| `localize.py`: `make_delta`、`apply_delta` | 原样复用 | `zar-sparse-delta-v1` 是本项目工具自定义格式，正反向文件大小/SHA-256/旧字节守卫；只支持追加保留式 ZAR；不是任意格式通用二进制补丁 |
| `localize.py`: `extract`、`import_text` | 复用主体，资源选择规则经目标清单确认 | 默认 EN、`.TBL`、`.SUB`、`EXAMINE/OPEN/UNLOCK.NNN` 不等于完整资源覆盖；UTF-8 strict、BOM、行尾、字幕前缀与偏移保护必须保留。新增类型走配置/适配层，不能略过未识别文本 |
| `localize.py`: `validate`、`TOKEN` | 复用守卫主体，游戏语法做适配 | 保留原文、ID、资源 SHA、偏移、控制码及占位符顺序；`/ALPHA` 谜题例外是《病房2》策略，需配置化。正则匹配通过不证明穷尽所有目标控制码 |
| `merge_locale.py`、`lint_locale.py` | 可复用数据合并/结构化诊断方法 | merge 假设完整 map、非空 target、固定字段，需要第一阶段清单模式；lint 参数已有可配置接口，编辑规范由 `locales/<locale>/` 管理 |
| `font_pipeline.py`: `printable`、`font_metadata`、`route_titles`、`glyph_width`、`wrap_text` | 算法候选；不可直接宣称目标字体可用 | metrics 键、字距、变量宽度（当前 `$...` 估24px）、颜色控制码、`|` 分隔符、PUA 支持须核实；标题中文识别 `ord>=0x3000` 与正文/标题路由仍有语言策略，移到 locale profile |
| `font_pipeline.py`: `discover`、`resolve_fonts`、`build_mixed`、`render_previews`；`localize.py`: `build_font` | 必须适配，非整文件原样复用 | 发现过滤写死 Fusion/ChillBitmap 名称，图集写死 D2FONT；目标字体资源名、格式、坐标、基线、行距、纹理边长上限和 renderer 路由均需独立验证。先证实目标格式再参数化，不为单次实验盲目导入混合字库/PUA |
| `check_runtime_assets.py` | 双索引一致性核心可复用；check 入口需改 | `index_rows` 已直接从 localize 导入；字体解码检查写死 D2FONT，目标应按配置枚举字体 PNG 并分别核验，不称为运行时测试 |
| `art_delta.py`: `capture`、`apply`、`png`；`image_preservation.py` | 通用 RGBA 差分/未修改成员守卫可复用候选 | 图片像素哈希与尺寸必须匹配，源图保持不变；不复制上游图片配方、遮罩、英文保留清单及商标分类 |
| `image_text.py`、`image_alignment.py`、相关 layout audit | 方法可借鉴，配方需重做 | 原图 SHA、编辑区域、资源名、布局/品牌判断均是游戏数据；只有目标图片完成独立清点和许可判断后使用。第一阶段不生成整批图片汉化 |
| `build_resource_payload.py` | 资源级差分/哈希复核思路可复用，现有入口需拆分 | make_payload 同时调用原生载荷构建；native_executable_payload 写死 EXE 名并要求 native-menu-pe-v1；资源与 EXE 流程分离后再迁移，不引入旧安装器兼容配方 |
| `executable_text.py`: `_rdata`、`build_executable` 等 | 仅作为未来受守卫数据槽工具候选 | 每个目标 PE 槽位必须独立确认容量、源字节、SHA 与实际调用。旧 recipe 一律不适用；`apply_executable_patch` 还有 native-menu 分支，不需为第一阶段复制 |
| `build_locale.py`、`verify*.py`、`install_patch.py`、打包和 WPF installer | 不直接移植；本阶段只保留设计经验 | build_locale 无条件调用 debug_menu，且强耦合上游 EXE、locale、图片审计、发布命名。当前阶段需独立只读调查/副本构建入口，不安装、不生成正式安装器、不发布 |
| `native_profile.py`、`native_patch.py`、`debug_menu.py`、`document_reader.py`、`menu_input.py` 及原生回放测试 | 不迁移旧地址、指令、状态布局或 hook | 虽有精确字节和身份守卫，但只验证《病房2》对应 build；F1 菜单不属任务，阅读器/输入 hook 也不是“默认兼容”。目标若日后需要，另立独立逆向与验收任务 |

## 3. 硬编码实例（锁定上游提交的文件行号）

| 位置 | 实例 | 处理 |
|---|---|---|
| `tools/localize.py:350` | scan 报告写死 `appid: 5342930` | 从独立游戏 profile/实际 Steam manifest 获取；禁止直接运行旧 scan 后当目标报告 |
| `assets/supported-build.json:2-9` | AppID/build/depot/manifest、ROM/EXE size/SHA | 重新采集目标身份；不是查找替换游戏名 |
| `tools/build_locale.py:24,45,51,54,67`；`tools/verify.py:17` | `Dementium II.exe` | 改为显式目标配置；源、生成目录分离 |
| `tools/build_locale.py:26-28,47-49` | full-zh-CN、locale路径、无条件 build_menu | locale参数化；资源构建与原生功能解耦 |
| `tools/install_patch.py:49,58-59,112,119,185` | 上游 EXE、AppID、cn-backup | 本阶段不引入安装路径；未来做目标专用身份配置与事务式恢复 |
| `tools/localize.py:145-152,180,213` | EN选择器、文档命名、context、`/ALPHA` | 可复用已验证子集；完整覆盖依目标清单扩展适配层 |
| `tools/localize.py:238,388`；`tools/font_pipeline.py:203,333-334`；`tools/check_runtime_assets.py:17` | `FONTS/D2FONT_12X15` | 目标独立字体 profile，不假定路径相同 |
| `tools/font_pipeline.py:28-47,68-69,297,308` | 已安装字体名过滤、标题字符范围、EXAMINE、固定排版分类 | 资源选择与语言策略配置化；度量须匹配目标 renderer |
| `locales/zh-CN/font-profile.json:6-12,17-24` | 字体 SHA、`EN/CHAPTERS.TBL`、512/4096 图集、228/240 文宽 | 是上游数据与保守预算，不是目标引擎实测限制 |
| `tools/native_patch.py:8-10` | ImageBase `0x140000000`、READER_STATE `0xa68980`、MENU_STATE `0xa68e80` | 目标绝不套用；未知布局阻止修改 |
| `tools/native_profile.py:4-29` | 默认 build26099941 与大批 RVA 映射 | 只适用于两个已审计上游 build，不是通用相对偏移算法 |
| `locales/zh-CN/executable-text.json:5`；`locales/zh-CN/debug-menu.json:3-4,93-94` | EXE/hash、字体源哈希及按build哈希 | 不复制为目标支持声明，不移植原生配方 |
| `tools/image_text.py:214` | `Dementium II title logo...` 资源保留原因 | 目标另立品牌/原画保留规则 |

`rom.zar` 在上游多个入口作为固定文件名；目标即使实际同名，也应由身份配置绑定。上游文档 `D:/Games/Dementium II Original` 是命令示例，不能把该路径当本机目标。`test_localize.py` 中随机种子 `5342930` 是合成确定性数据，不是游戏身份检查，无需为了改数字而改算法。

## 4. 已执行上游纯合成回归

工作目录：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\reference\Dementium-II-CN`。
输入：各测试文件内生成的字节/指标/图像夹具；无安装目录资产，无游戏进程，无真实字体依赖。2026-10-23 实际运行：

```powershell
python -X utf8 -m unittest discover -s tests -p test_localize.py -v
# Ran 23 tests in 0.021s
# OK
# exit 0
python -X utf8 -m unittest discover -s tests -p test_vfs_index.py -v
# Ran 8 tests in 0.001s
# OK
# exit 0
python -X utf8 -m unittest discover -s tests -p test_art_delta.py -v
# Ran 6 tests in 0.006s
# OK
# exit 0
python -X utf8 -m unittest discover -s tests -p test_font_pipeline.py -v
# Ran 24 tests in 0.362s
# OK
# exit 0
```

共 61 项通过。测试覆盖：空回写字节相同、重定位与未改成员保持、错误 ZAR 边界/对齐/重叠/路径拒绝；BOM/空行/字幕前缀、UTF-8/控制码顺序、过期位置与注入拒绝；差分正反向与错误输入拒绝；双索引扩容同步及 flags 拒绝；图片源/结果像素守卫；字库合成、原图保护、确定性、覆盖不足、PUA碰撞、基线与文字折行。

没有运行上游完整测试集；部分测试需要上游 locale数据、原版/构建产物、原生工具链或回放，不以61项代替全套结果。目标游戏实际原包的解析、noop、清单、双索引和隔离差分回滚由本项目目标基线单独验证。

## 5. 目标调查复核与最小“新游戏”实验门槛

本节已依据目标 `TECHNICAL.md`、`docs/FILE_FORMATS.md`、`assets/inspection/coverage.json`、`docs/VERIFICATION.md` 与当前 `tools/content.py`、`tools/investigate.py` 更新；前面矩阵保留上游源码迁移适用前提，不将其候选接口误作目标格式。

### 目标已验证

- 当前目标 AppID `3909960`、build `21501403`。外层 ZAR1 有668成员，`~INDEX` 有602记录；601项关联包内、一项外部 `LICENSES.TXT`，不是外层所有成员必须与VFS逐一对应。
- 真正的文本位于外层 `CONTENT.TAR`，不是上游 `EN/*.TBL` 外层成员。TAR有2555成员/2522文件。目标需要新 TAR/文本适配层，旧 `extract`、`import_text` 和 `is_document` 不直接适用（目标还存在 `item.NNN`）。
- `New Game` 源已定位为 `CONTENT.TAR` 内 `loc/en/UISSFrontend.tbl:0000`，资源361字节、该记录8字节，TAR数据偏移72625664、原包绝对偏移73674240。偏移是调查身份信息，重建按成员/记录查找，不硬编码用于后续构建。
- 5个语言655资源/1390非空记录；英语131资源/278记录。英语130资源纯ASCII，credits有单字节重音字节。调查清单使用 Latin-1 **仅作为字节无损视图**，不是运行时编码判定；未证实 Latin-1、CP1252 或 UTF-8 哪个为真实解码机制。
- 字体是内层 `fonts/d2font_12x15.binfont`，7620字节；没有上游 `FONTS/D2FONT_12X15.JSON` 与标准 PNG atlas 接口。EXE包含字体路径字面量，不等于加载/绘制调用链已经跟踪。
- 外层319个 `.PNG` 扩展名资源均为非PNG二进制容器，开头 `7a00000020000000`；标准PNG数量0。扩展名既不证明可解码，也不能交给旧 Pillow 图集工具直接改写。
- 已在 `tools/zar.py` 实际复用上游8个定义：`digest`、`filehash`、`write_json`、`Entry`、`index_rows`、`Zar`、`make_delta`、`apply_delta`。已迁移22项上游合成测试（14项归档/差分、8项VFS），加16项新TAR/文本测试；目标完整38项通过，具体命令和字面输出见 `docs/VERIFICATION.md`。这与第4节审计时单独运行的61项上游测试是不同集合，不能相加宣称目标99项。
- `tools/content.py` 新增内存TAR适配及显式编码文本保护；`tools/investigate.py` 验证完整原包 noop 字节相同、ASCII变长探针、未改成员/顺序/控制码、跨TAR块增长双索引同步、差分双向守卫，以及隔离副本恢复SHA一致。Steam目录保持只读，modified探针保留。

### 尚未建立的中文闭环

- binfont字段、glyph编码/索引、度量与位图布局、可扩展数量尚未确认；旧JSON/PNG字库生成器需重建后端，而非只改资源路径。
- 真实文本decoder、中文编码、三个字形生成与查询、font loader、字距/换行、固定按钮复制容量和裁剪尚未验证。`新游戏` 的UTF-8长度为9字节，不能由资源允许变长推出运行时支持UTF-8。
- 本阶段ASCII探针为 `New Game -> New Game [offline probe]`，**不是中文探针**。当前具备资源定位、重建、身份守卫和恢复条件，但尚未具备将“新游戏”正确显示的完整技术条件。
- 下一步先只读定位 binfont loader 与文本decoder，明确字体/纹理二进制格式，建立目标专用且locale-neutral的字库后端，再生成仅此条译文和必要字形的离线样本，之后由用户手动进行游戏内显示验收。
- 不复制上游 F1/阅读器/native RVA，不翻译全量，不制作安装器或Release；本阶段全部证据均为静态或离线，游戏内与中文显示状态均为未测试。

## 6. 第二阶段实施结果（2026-10-23）

第一阶段的目标未知项已按独立本作证据推进：字库页表、metrics、RGBA双zlib、section/relocation有解析和原生loader指令回放。实际菜单是byte→ushort，不是上游UTF-8。当前只做New Game一条，运行时用81/8D/8F三个空slot，真实译文仍在locale数据；不覆盖原180glyph，不改EXE。

font_metadata/discover/resolve_fonts已逐函数复用于tools/font_source.py；原版ZAR/TAR及差分核心继续使用，字体栅格化/身份门禁/原像素保留方法延续。序列化和decoder策略另写本作适配，没有移植旧native patches。单字节空槽只是POC预算，不作为全量汉化方案。当前72项合成测试与实际目标指令/资源回放通过，游戏画面仍待手动验收。详见MINIMAL_PROBE.md、TEXT_DECODING.md、BINFONT_FORMAT.md。

## 7. 全量阶段复用与独立适配（当前）

- **原样复用**：ZAR/VFS/资源差分的8个定义及其成熟测试；font_source的font_metadata/discover/resolve_fonts三函数；art_delta.py与其6项上游测试。来源、作者、commit与MIT见NOTICE.md。
- **按本作修改/适配**：上游Pillow字体生成及字形覆盖思路接入本作binfont后端；image_text的墨迹居中、按键保护和区域约束接入本作双LZ4容器；executable_text固定槽守卫独立审计，目前entries为空，不强造本作不需要的字面量补丁。
- **本作独立实现**：TAR文本结构、UTF-8/BMP入口RVA0xEA700、binfont扩页/重定位/双zlib、PCM采样时钟HUD字幕RVA0xBFF10、Image格式0/1/5/8读取、VP9 IVF/DAT同步与影片章名重建。它们没有复用病房2的JSON字库、旧EXE偏移、开发菜单或作弊功能。
- **已具备的最小中文条件**：New Game源身份、3个Unicode码点、字体生成/查字/测宽、归档回写与隔离恢复均已通过；现在由可扩展全量UTF-8构建覆盖，不再依赖81/8D/8F单字节POC空槽。全量278记录/855glyphs的具体输出见FULL_VERIFICATION.md。
- **仍待实际确认**：游戏内GPU、裁切、输入、存读档、完整流程与字幕听校/同步；低清装饰字与splat01额外尾部语义如实保留。离线回放不是游戏内通过，已保存的上游实机截图也不作为本作证据。

其他四语1112记录只做Latin1字节映射→UTF-8的无损编码迁移；原/新解码流逐条一致，既有French双角引号不被新工具臆断为待修改的markup。其测宽未额外声称已全量验证，兼容性证据是原decoded stream、原glyph与调用合同保持。
