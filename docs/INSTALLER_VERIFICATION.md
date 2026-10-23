# v1.0 安装器与文案/图片修正验证

日期：2026-10-23。未启动游戏、未写Steam安装目录；原九文件SHA复核相同。

## 本轮结果

- 31条无内部标点的单句短说明仅去末尾句号；85条真正文档/信件/谜题/演职员表target指纹不变，电影/语音对白数据不变。
- 明确撤回notepad、wboard02、code03三张证据不足的推补式重绘；原压缩资源和mipmap逐字节保留。当前26张美术差分（23 inner+3 outer）和49张程序化UI均保留可读原文汉化。
- Python228项通过；C#安装器59项通过（含54个合成断言和真实嵌入载荷5项安装/恢复检查）。
- 原件基线、两次整包改件比较、隔离恢复均退出0；两个source-relative差分各生成两次一致，安装器重复发布字节相同。
- WPF默认780×710、最小680×640、200%三份预览实渲染通过；主题/ripple/入场动画与病房2相同。图标PNG与用户附件在PE图标资源内逐字节相同；顶图为附件原PNG。

## 改动字段

31 terminal full stops removed; documents/dialogue preserved; 3 unsupported image redraws withdrawn; F1/L3+Y retained; Material Design 3 installer with supplied icon/logo

## 交付与身份

- 安装器：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\dist\Dementium-The-Ward-zh-CN-Setup.exe`
- 大小：`241513533` bytes；SHA-256：`c6cfe00169454df35588046c923f09c884453458c97e246456d19fcd0214abba`
- 自包含Windows x64，不要求玩家另装Python或.NET；仅支持原Steam build21501403完整身份或本版已安装状态。

- `MODIFIED_FILE.exe`：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\MODIFIED_FILE.exe`；SHA-256 `c6cfe00169454df35588046c923f09c884453458c97e246456d19fcd0214abba`
- `DIFF_FILE.json`：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\DIFF_FILE.json`；SHA-256 `5aa35b2a8d97c548d7a547cf442624e9045ca4c9989e86bc299b7512c97e5fc3`
- `VERIFICATION.txt`：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\VERIFICATION.txt`；SHA-256 `1e3e7cb8882fbcb47602a526037bbb796060334ac98275685e71648d785a664f`
- `ROLLBACK.sh`：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\ROLLBACK.sh`；SHA-256 `0d7643d4a8d0ccc75b1d59825a7737604f928dfe96a5cb449da0a4e1b15a28b1`

## 基线、修改、隔离恢复的实际命令与输出

### BASELINE

```text
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py baseline --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\release-candidate --locale zh-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
STDOUT:
BASELINE PASS records=278 archive-members=668 content-members=2555 noop=byte-identical input=unchanged decoder=byte-widen
STDERR:

EXIT STATUS: 0
```

### MODIFIED

```text
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py modified --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\release-candidate --locale zh-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
STDOUT:
MODIFIED PASS records=278 UTF8=roundtrip glyphs=884 dual-index=consistent reproducible=true native-replay=PASS game-launched=false
STDERR:

EXIT STATUS: 0
```

### ROLLBACK

```text
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py rollback --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\release-candidate --locale zh-CN
INPUT: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\release-candidate\MODIFIED_FILE.zar
STDOUT:
ROLLBACK PASS isolated-copy=original-sha256 text=New Game decoder=byte-widen font=original modified-and-sample=retained
STDERR:

EXIT STATUS: 0
```

## 实际嵌入载荷回环

```text
COMMAND: C:\Users\noway\Downloads\Dementium-II-CN\build\toolchain\dotnet\dotnet.exe C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\tests\net10.0-windows10.0.17763.0\InstallerTests.dll --real C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\real-sample
末尾原样输出:
PASS: REAL BASELINE identities
PASS: REAL MODIFIED install
PASS: REAL idempotent install
PASS: REAL ROLLBACK restore
PASS: REAL restored original identities
INSTALLER_TESTS_PASSED=59
EXIT STATUS: 0
```

所有合成断言/发布命令完整输出保存在build/installer/VERIFICATION.txt与build-commands.json；包括安装/恢复提交中断后的双文件回滚、未知文件不删、未知/混合版本、缺失/坏备份、坏载荷/源越界/EOF、硬链接与目录联接拒绝。

## Python与恢复包装器

```text
COMMAND: python -X utf8 -m unittest discover -s tests -q
----------------------------------------------------------------------
Ran 228 tests in 38.940s

OK
EXIT STATUS: 0

COMMAND: "C:/Program Files/Git/bin/bash.exe" C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\ROLLBACK.sh
ROLLBACK PASS isolated-copy=original-sha256 text=New Game decoder=byte-widen font=original modified-and-sample=retained
EXIT STATUS: 0
```

RESTORED：额外real-sample与rollback-sample两文件均恢复原版SHA，原New Game/字库/单字节decoder/原调试门禁。安装器、修改归档/EXE及手测sample保留不覆盖。

## 界面证据

```text
COMMAND: C:\Users\noway\Downloads\Dementium-The-Ward-CN\dist\Dementium-The-Ward-zh-CN-Setup.exe --render-preview C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\preview.png 1 780 710
WPF MaterialDesign3 preview width=780 height=710 raster_scale=1 material_ripples=5 entry_animation=PASS checkbox=NONE progressbar=NONE runtime=10.0.13 game_launch=NEVER
EXIT STATUS: 0
```

```text
COMMAND: C:\Users\noway\Downloads\Dementium-The-Ward-CN\dist\Dementium-The-Ward-zh-CN-Setup.exe --render-preview C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\preview-min.png 1 680 640
WPF MaterialDesign3 preview width=680 height=640 raster_scale=1 material_ripples=5 entry_animation=PASS checkbox=NONE progressbar=NONE runtime=10.0.13 game_launch=NEVER
EXIT STATUS: 0
```

```text
COMMAND: C:\Users\noway\Downloads\Dementium-The-Ward-CN\dist\Dementium-The-Ward-zh-CN-Setup.exe --render-preview C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\preview-200.png 2 780 710
WPF MaterialDesign3 preview width=780 height=710 raster_scale=2 material_ripples=5 entry_animation=PASS checkbox=NONE progressbar=NONE runtime=10.0.13 game_launch=NEVER
EXIT STATUS: 0
```

原图/字节审计、受控原指令回放和安装器副本回环不等同于游戏画面/真实设备/流程验收。使用方法见[INSTALLER.md](INSTALLER.md)，手测副本为build/release-candidate/sample。
