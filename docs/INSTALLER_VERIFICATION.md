> 2026-10-24最新：仅四处发布修正，安装器仍为1.0，78497853 bytes，SHA256 `5bd98a3d21403bada448ef154fcda22914f12b98cb9294b802d8d4aa5c505939`。Python271项、C#59项及独立安装/恢复通过；详细范围与身份见[四处发布修正](RELEASE_FOUR_FIXES.md)。以下保留上一安装器历史。

# v1.0：已试玩候选的安装包

2026-10-23。用户报告新副本约20分钟简测未见明显问题，现授权生成v1.0安装器供其覆盖Steam目录进一步测试；自动化仍不启动游戏或写Steam原安装目录。简测不代表全流程/最终美术验收。

- 文件：`dist/Dementium-The-Ward-zh-CN-v1.0-Setup.exe`；通用名称副本字节相同。
- 体积：78,274,109 bytes。SHA256：`beea24d0709979ce4ebf74595f0f518a8db67e495945b585cfb36030e87dedce`。
- UI/产品版本1.0，PE文件/程序集版本1.0.0.0。
- Python268项、C#59项全部通过；真实嵌入载荷在额外副本完成原版检查→安装→重复安装→恢复→原SHA检查。
- source-copy/add流独立重复生成相同；两次发布安装器字节相同。
- 三尺寸/缩放WPF原生预览通过，原图标PNG在PE资源中逐字节核对，顶图源身份不变；未重画UI素材。
- 载荷ZAR目标：`bf4d6c52b7912f6216bd4662a15ba0948048f38dabbde2f734945506339c005f`；EXE目标：`d426d3065b7fdf530d3fd48c9f117d3bb7339bf67c1252f600b68e5f32a8b7f0`，与已试玩副本一致。
- 旧安装器完整身份与可执行文件保留于`build/installer/baseline-v1.1.1`，SHA仍为`77ad756c7a144f0973b6b907caaf593629ff5b3089968c4f178252976375e984`。

四证据文件：`build/installer/MODIFIED_FILE.exe`、`DIFF_FILE.json`、`VERIFICATION.txt`、可执行`ROLLBACK.sh`。最后一项只恢复额外构建副本；Steam安装后的恢复使用安装器“恢复原版”。所有精确命令/输入/字面输出/退出码记录于VERIFICATION.txt。

复现命令：

```powershell
python -X utf8 tools/build_installer.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward" --build build/framed-artwork-release --dotnet "C:/path/to/dotnet.exe" --output dist/Dementium-The-Ward-zh-CN-v1.0-Setup.exe
python -X utf8 tools/record_installer_verification.py --build build/framed-artwork-release
```

## 历史v1.1.1安装器记录

# v1.1.1：四项实测反馈修复与离线验证

2026-10-23。自动化没有启动游戏或写Steam目录；用户截图是本轮修复依据，修复后实际渲染/听音由用户复测。

## 交付身份

- 安装器：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\dist\Dementium-The-Ward-zh-CN-Setup.exe`
- 78,268,477 bytes（78.27 MB），比v1.1的78,266,941 bytes增加1,536 bytes
- SHA256：`77ad756c7a144f0973b6b907caaf593629ff5b3089968c4f178252976375e984`
- Python253项、C#59项通过；真实嵌入载荷安装→重复安装→恢复原SHA通过
- 最终交付EXE双ASLR 24项反馈回放通过；完整构建两次字节一致
- 安装器21个非版本元数据源文件与v1.1完全相同；三尺寸/缩放WPF预览逐像素相同，PE图标/顶图原字节一致
- 原102个电影成员不变，18对白、9画面译注、18标题及3547帧双ASLR回放保留

## 改动字段

loc/en/*; other-locale encoding; BMP font; decoder RVA 0xEA700; audio HUD RVA 0xBFF10 mixer/delay/gain + modal exclusion + cue-ID dedup; display classic/high-resolution fixed literals; debug nameX16/valueX112; reviewed images; original IVF/DAT/OGG preserved; decoded-frame movie captions/annotations/titles RVA 0xBDBCA; independent F1 raw48/action18; native enabled L3+Y; localized debug menu; installer UI retained

修复细节见[UI_FEEDBACK_FIXES.md](UI_FEEDBACK_FIXES.md)，实际步骤见[MANUAL_TEST.md](MANUAL_TEST.md)。

## 四项证据产物

- `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\MODIFIED_FILE.exe`
- `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\DIFF_FILE.json`
- `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\VERIFICATION.txt`
- `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\ROLLBACK.sh`

改件保留；单独real-sample和rollback-sample恢复原版SHA、New Game、原字体/decoder/debug门禁，未覆盖待测sample。

## 命令、输入和原样结果

下列保留阶段总结末行；含全部电影编译输出、stderr、每项C#断言和UI命令的完整原样记录在上述VERIFICATION.txt。

### BASELINE

```text
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py baseline --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\ui-feedback-release --locale zh-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
RESULT: BASELINE PASS records=278 archive-members=668 content-members=2555 noop=byte-identical input=unchanged decoder=byte-widen
EXIT STATUS: 0
```

### MODIFIED

```text
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py modified --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\ui-feedback-release --locale zh-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
RESULT: MODIFIED PASS records=278 UTF8=roundtrip glyphs=885 dual-index=consistent reproducible=true native-replay=PASS game-launched=false
EXIT STATUS: 0
```

### ROLLBACK

```text
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py rollback --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\ui-feedback-release --locale zh-CN
INPUT: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\ui-feedback-release\MODIFIED_FILE.zar
RESULT: ROLLBACK PASS isolated-copy=original-sha256 text=New Game decoder=byte-widen font=original modified-and-sample=retained
EXIT STATUS: 0
```

### 最终EXE专项回归

```text
C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe tools/verify_ui_feedback.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward" --build build/ui-feedback-release
FEEDBACK PASS cases=24 bases=2 duplicate=1 modal=0 close=current gap-first=1 inaudible=0 inputs=unchanged game-launched=false
EXIT STATUS: 0
```

## 原件与候选完整身份

- 原EXE：`26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`
- 原ZAR：`9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c`
- 新EXE：`a6c5be2dbdd7980a56456ae2723a9a08dcc793e1da74ad4ee7a943eb45c12cfb`
- 新ZAR：`07a73306e85cb3037308f6eb0cc9d1aff8e0c2b3fb10d2aed5eb77a088568dd0`
- 手测副本：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\ui-feedback-release\sample`
- 上轮样本build/release-candidate/sample未覆盖；上一版安装器保留在build/ui-feedback-release/baseline/Dementium-The-Ward-zh-CN-Setup.exe。旧版已安装时，先用该对应旧安装器恢复原版，再安装1.1.1。

## 审查与边界

独立只读审查发现的gap-first提前去重丢字已修复，并经重新测试；无未处理P1/P2，报告build/ui-feedback-release/review.md。最小列距18不等于实际GPU/鼠标已验收；原生指令回放的系统边界替身明确记录在报告。开头房间广播是否原本可听不作推定；本轮仅按本作实际混音数据过滤字幕，不改原声触发。
