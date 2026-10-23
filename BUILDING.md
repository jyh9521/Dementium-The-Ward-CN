> 当前纵轴布局测试输出：build/yaxis-alignment。本轮暂不运行build_installer.py；现有dist安装器保持原SHA。构建/回放命令见docs/YAXIS_LAYOUT.md，待用户确认后再打包。

# 全量离线构建与隔离恢复

## 可复现输入

- 原版Steam AppID3909960/build21501403，9文件身份在assets/original-identity.json。未知版本拒绝，不自动重写受支持身份。
- Python3.11+与requirements.txt固定版本；实际本机Python3.14.2。
- Fusion Pixel12px简中，SHA与发现规则见locales/zh-CN/font-full-profile.json和docs/FONT_SOURCE.md；许可assets/fonts/Fusion-Pixel-OFL.txt。不下载或安装字体。
- ffmpeg/ffprobe9.0.2，工具身份写入媒体报告。当前仅离线解码原视频以生成稀疏覆盖层，不调用视频编码；全部原IVF/DAT/OGG及FLAC音轨保持原字节。
- 语音识别及美术编辑只在研究阶段使用；已审校locale数据与源依赖差分足够重建，不需要缓存模型或生成服务。

## 仓库根目录命令

```powershell
$game = "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward"
python -m pip install -r requirements.txt
python -X utf8 -m unittest discover -s tests -v
python -X utf8 tools/record_locale_verification.py --game "$game" --output build/ui-feedback-release
python -X utf8 tools/verify_sample.py --output build/ui-feedback-release
& "C:/Program Files/Git/bin/bash.exe" ./build/ui-feedback-release/ROLLBACK.sh
python -X utf8 tools/investigate.py check-input --game "$game"
```

单独运行的阶段命令为tools/build_locale.py baseline/modified/rollback；baseline/modified提供--game，均可用--output指定仓库build/下目录。--text-only只供中间文本研究，不能将其叫作全量样本。

## 流水线与证据

1. 只读验证全部原输入，ZAR/TAR/binfont无修改回写逐字节一致。
2. 校验278记录原身份、ID、控制码，收集正文及媒体字幕字形，生成保留原180glyph的BMP字体。
3. 中文按已验证宽度/高度自动折行；四语原文只做Latin1字节映射到UTF-8，1112记录逻辑不变，所有HUD字段仍守255byte。
4. 构建49张程序化UI图、3张界面美术差分、23张场景纹理差分及完整mipmap，保护区域外像素、按键、UV、血迹。
5. 全部102个电影成员保持原样；离线解码24个需汉化片段生成对白、顶部译注及章节标题的稀疏RGB覆盖层，保持标题fade/红装饰及后续剧情。原生BDBCA上传前复制BGRA并叠层，按实际打开DAT和选定帧PTS定位，不重编码或更新DAT。详见docs/MOVIE_OVERLAY.md。
6. 仅副本EXE增加受完整SHA/邻域守卫的UTF-8 decoder和PCM采样时钟字幕overlay，保持ASLR/Win64 unwind；本作真实指令离线回放，不运行游戏进程。
7. 重复完整构建比较；差分正反向验证；准备sample后复核原9文件身份。
8. 恢复只写rollback-sample的两文件，不覆盖modified及sample。逆序移除电影覆盖、debug、场内字幕、固定字面量层、UTF-8补丁，归档恢复原SHA。

建议显式使用--output build/ui-feedback-release；未指定时工具默认build/full/只为历史兼容。MODIFIED_FILE.zar、MODIFIED_EXECUTABLE.exe为待测改件；DIFF_FILE.json包含本地可逆差分，可能携带整个变更TAR/媒体，禁止提交。VERIFICATION.txt/verification.json记录实际命令、输入、字面输出与退出码；ROLLBACK.sh是可执行恢复包装器。native-replay.json、preserved-locales-replay.json、audio-replay.json、images.json记录分层证据。

输出树必须位于仓库build/，并拒绝symlink、reparse与多硬链接普通文件。原版目录不是写入目标。用户实际测试后产生的未知文件不会被构建工具擅自删除；先自行归档日志再重建。

[手动测试](docs/MANUAL_TEST.md) · [边界](docs/KNOWN_ISSUES.md)。归档/媒体/指令检查不等于游戏内通过。

---

# 以下为历史阶段复现（非当前手测样本）
# 第二阶段：最小中文样本构建

## 输入与命令

Python3.11+、requirements.txt固定依赖，以及用户原版AppID3909960/build21501403。字体为已安装Fusion Pixel12px简中，文件名/哈希见locales/zh-CN/font-profile.json；工具只发现并验证，不下载或安装字体。源码不含字体二进制，许可见assets/fonts/Fusion-Pixel-OFL.txt。

```powershell
$game = "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward"
python -m pip install -r requirements.txt
python -X utf8 -m unittest discover -s tests -q
python -X utf8 tools/build_probe.py baseline --game "$game"
python -X utf8 tools/build_probe.py modified --game "$game"
& "C:/Program Files/Git/bin/bash.exe" tools/ROLLBACK_PROBE.sh
python -X utf8 tools/investigate.py check-input --game "$game"
```

一键重跑并记录实际输出：

```powershell
python -X utf8 tools/record_probe_verification.py --game "$game" --bash "C:/Program Files/Git/bin/bash.exe"
```

默认build/phase2/sample为手动启动副本，MODIFIED_FILE.zar为保留改包，DIFF_FILE.json为本地可逆差分，ROLLBACK_COPY.zar与rollback-sample/rom.zar恢复原身份。VERIFICATION.txt/commands.json记录精确命令/输入/输出/退出码。所有工具均不执行游戏。

构建前校验全部9文件身份，输出限制到仓库build/，拒绝输出树symlink/reparse及多硬链接文件；不把Steam目录当写入目标。两次同输入构建字节相同；重新解包仅两内层成员变化；原生字库loader/重定位与表解析/测宽回放通过。GPU与完整进程仍待用户手动验收。

[用户手动测试](docs/MANUAL_TEST.md) · [最新验证](docs/PROBE_VERIFICATION.md)

---

# 第一阶段复现与恢复

## 输入

- Python 3.11+，当前标准库工具在 3.14.2 验证，无 pip 依赖。
- 用户提供的 Steam 原版；AppID3909960、实测 build21501403，9个输入文件 SHA-256 记录于 `assets/original-identity.json`。
- Bash 只用于执行 shell 恢复包装器（Git for Windows 自带）；恢复逻辑本身为 Python。
- `assets/game-profile.json` 管理资源名、语言、清单编码及外部 VFS 成员。`latin-1` 只提供无损字节视图，不宣称是运行时中文编码。

不要将未知版本重新扫描后自动覆盖受支持身份；调查新版本需要独立评估、审阅及新增身份记录。基线/修改命令校验整包大小与 SHA-256 后才构建。

## 命令（仓库根目录）

```powershell
$game = "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward"
python -X utf8 -m unittest discover -s tests -v
python -X utf8 tools/investigate.py scan --game "$game"
python -X utf8 tools/investigate.py baseline --game "$game"
python -X utf8 tools/investigate.py modified --game "$game"
& "C:/Program Files/Git/bin/bash.exe" tools/ROLLBACK.sh
python -X utf8 tools/investigate.py check-input --game "$game"
```

一键记录精确命令、字面输出、退出码及产物身份：

```powershell
python -X utf8 tools/record_verification.py --game "$game" --bash "C:/Program Files/Git/bin/bash.exe"
```

所有命令均不执行游戏。输出必须在仓库 `build/` 内且不得位于输入目录；Steam目录仅为输入。

## 生成物

| 文件 | 用途 |
|---|---|
| `build/phase1/text-{en,de,es,fr,it}.json` | 完整已识别语言资源记录；包含稳定ID、源字节位置、哈希、控制码与空 target |
| `build/phase1/archive-manifest.json` / `content-manifest.json` | 外/内层顺序、大小、位置与 SHA |
| `build/phase1/executable-string-candidates.json` | EXE/DLL ASCII、UTF-16LE候选；不是经过确认的界面文字 |
| `build/phase1/coverage.json` | 明确分母与未知覆盖范围 |
| `build/phase1/MODIFIED_FILE.zar` | ASCII资源探针：New Game → New Game [offline probe]，不是中文补丁 |
| `build/phase1/DIFF_FILE.json` | 绑定原包/结果哈希的可逆差分，仅本地；包含源依赖资源数据，禁止提交 |
| `build/phase1/ROLLBACK_COPY.zar` | 从额外副本恢复的原版身份；不覆盖 modified产物或安装目录 |
| `build/phase1/VERIFICATION.txt` / `commands.json` | 实际执行证据 |
| `tools/ROLLBACK.sh` | 可执行恢复包装器，目标固定为本地输出 |

无修改往返是完整字节相同；变长测试另以600空格跨越TAR块边界，验证 `CONTENT.TAR` 外层TOC与 `~INDEX` 大小同步。正式保留的探针只改一个内层文本成员。控制码、空行、行尾、其他成员、名称顺序保持。TAR变长后相邻成员绝对位置允许改变。

## 后续阶段门禁

先调查 binfont、文字查字/解码/测宽，再选择有许可的字体；通过三个中文字形的离线构建后，由用户手动运行中文最小样本验证。当前无正式安装、字体下载或发布步骤。

## 独立 F1 与简体中文调试菜单

当前构建从 `locales/<locale>/debug-menu.json` 读取本作原生命令表及状态译文，生成字形并在 UTF-8/音频 overlay 后增加受守卫的独立 F1 层。L3+Y 仍受原手柄秘密序列启用状态控制。不启用整套键盘模拟手柄。新一轮验证使用 `--output build/ui-feedback-release`，样本及恢复均只写该目录。

完整重建、精确入口、复用来源和人工测试见 [调试菜单](docs/DEBUG_MENU.md)。`build/full` 旧样本不是本次调试入口候选。每次变更需完整重复构建、原指令回放及逆序恢复，通过后才使用新 sample。


## v1.0 安装器与本轮修正

当前候选是 `build/ui-feedback-release/sample`。31条单句短说明只删最后句号，文档/信件/对白不改；分类与回归见 [PUNCTUATION_STYLE.md](docs/PUNCTUATION_STYLE.md)。撤回notepad、wboard02、code03三张推补式重绘并锁定原资源；现为23 inner +3 outer美术差分、49张程序化UI，见 [图片复审](docs/IMAGE_READABILITY_REVIEW.md)。此前build/full及build/debug-menu样本保留历史，不能用于验收本轮修正。

安装器复用病房2 Material Design 3 / MaterialDesignThemes 5.3.2布局、动效、自动检测、日志和确认弹层；图标和顶图直接使用用户提供文件，ICO嵌入原PNG不重绘。引擎与载荷为本作重写，完整SHA/大小绑定EXE+ZAR，不继承病房2宽松资源识别或偏移。

需要.NET 10 SDK（本轮10.0.402），不是只有runtime。显式指定SDK，可用全新机器的任意安装路径，不依赖旧项目未记录中间文件：

```powershell
python -X utf8 tools/build_installer.py --game "$game" --build build/ui-feedback-release --dotnet "C:/path/to/dotnet.exe"
```

生成 `dist/Dementium-The-Ward-zh-CN-Setup.exe`，自包含Windows x64，不要求玩家安装Python或.NET。先独立生成两次gzip source-copy/add差分并比对；Python重建后核对修改目标SHA；锁定依赖发布两次并比对EXE；C#实际嵌入资源在额外原件副本完成安装→重复安装→恢复，所有原输入仍只读。

`build/installer/payload.manifest.json`记录源/目标大小和SHA；差分中的COPY引用用户自己的原文件，ADD仅写新增/修改字节。测试与UI预览均不启动游戏。安装/恢复总是两个文件一起处理，先生成并校验所有临时结果再提交；提交失败逆序恢复。`cn-backup`仅存对应完整原件，恢复时只删除已校验的已知备份，保留未知用户内容。详见 [安装与恢复](docs/INSTALLER.md)。

本轮版本1.1.1。固定EXE字面量必须纳入字体收集，UTF8_RUNTIME.exe保存纯解码器层；字幕层严格验证并反向移除字面量后核对原runtime SHA。安装验证记录使用`tools/record_installer_verification.py --build build/ui-feedback-release`。

最终产物字幕回归：`python -X utf8 tools/verify_ui_feedback.py --game "$game" --build build/ui-feedback-release`（两个ASLR基址，报告绑定最终EXE SHA）。
