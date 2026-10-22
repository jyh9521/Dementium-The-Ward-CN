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
