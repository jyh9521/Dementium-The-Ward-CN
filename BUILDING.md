# 全量离线构建与隔离恢复

## 可复现输入

- 原版Steam AppID3909960/build21501403，9文件身份在assets/original-identity.json。未知版本拒绝，不自动重写受支持身份。
- Python3.11+与requirements.txt固定版本；实际本机Python3.14.2。
- Fusion Pixel12px简中，SHA与发现规则见locales/zh-CN/font-full-profile.json和docs/FONT_SOURCE.md；许可assets/fonts/Fusion-Pixel-OFL.txt。不下载或安装字体。
- ffmpeg/ffprobe9.0.2（libvpx-vp9），实际工具身份会写入媒体报告。媒体构建为单线程、bitexact、lossless VP9；不改原OGG/FLAC音轨。
- 语音识别及美术编辑只在研究阶段使用；已审校locale数据与源依赖差分足够重建，不需要缓存模型或生成服务。

## 仓库根目录命令

```powershell
$game = "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward"
python -m pip install -r requirements.txt
python -X utf8 -m unittest discover -s tests -v
python -X utf8 tools/record_locale_verification.py --game "$game"
python -X utf8 tools/verify_sample.py
& "C:/Program Files/Git/bin/bash.exe" ./ROLLBACK_LOCALE.sh
python -X utf8 tools/investigate.py check-input --game "$game"
```

单独运行的阶段命令为tools/build_locale.py baseline/modified/rollback；baseline/modified提供--game，均可用--output指定仓库build/下目录。--text-only只供中间文本研究，不能将其叫作全量样本。

## 流水线与证据

1. 只读验证全部原输入，ZAR/TAR/binfont无修改回写逐字节一致。
2. 校验278记录原身份、ID、控制码，收集正文及媒体字幕字形，生成保留原180glyph的BMP字体。
3. 中文按已验证宽度/高度自动折行；四语原文只做Latin1字节映射到UTF-8，1112记录逻辑不变，所有HUD字段仍守255byte。
4. 构建49张程序化UI图、3张界面美术差分、26张场景纹理差分及完整mipmap，保护区域外像素、按键、UV、血迹。
5. 18个影片文件的章名逐帧改写（16段独立章名、2段内嵌章名），573帧后续剧情原样保留，保持源fade/红装饰；电影对白及新闻/门牌画面词译注重编码，独立ffprobe更新DAT关键帧/偏移/尺寸。原音轨不变，VP9帧率/帧数/PTS保持；YUV区域外字节校验。
6. 仅副本EXE增加受完整SHA/邻域守卫的UTF-8 decoder和PCM采样时钟字幕overlay，保持ASLR/Win64 unwind；本作真实指令离线回放，不运行游戏进程。
7. 重复完整构建比较；差分正反向验证；准备sample后复核原9文件身份。
8. 恢复只写rollback-sample的两文件，不覆盖modified及sample。逆序移除overlay、固定字面量层、UTF-8补丁，归档恢复原SHA。

默认输出build/full/。MODIFIED_FILE.zar、MODIFIED_EXECUTABLE.exe为待测改件；DIFF_FILE.json包含本地可逆差分，可能携带整个变更TAR/媒体，禁止提交。VERIFICATION.txt/verification.json记录实际命令、输入、字面输出与退出码；ROLLBACK.sh是可执行恢复包装器。native-replay.json、preserved-locales-replay.json、audio-replay.json、images.json记录分层证据。

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
