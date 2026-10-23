# v1.1 原视频保留版：安装器与离线验证

日期：2026-10-23。仅副本构建/回放/安装恢复；未启动游戏，未修改Steam目录。

## 交付与身份

- 安装器：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\dist\Dementium-The-Ward-zh-CN-Setup.exe`
- 大小：**78,266,941 bytes（78.27 MB）**；旧版241,513,533 bytes
- SHA256：`cd047569e618e7f3b999bebdad445bf5eb67d39372e613a7fe886d905cb6560a`
- 原媒体102成员逐字节不变；18对白、9画面译注、18标题均保留
- 完整构建重复字节相同；3547覆盖帧×2个ASLR基址原生回放通过
- Python248项，C#59项；真实嵌入载荷检查→安装→重复安装→恢复通过
- UI核心源码字节相同；780×710、680×640、200%三份WPF预览与v1.0逐像素一致，图标/顶图原图不变

## 改动字段

实际VPX DAT身份/解码帧PTS/上传前BGRA稀疏覆盖；MOVIES/*原件保留；原文案/图片修正、F1/L3+Y及安装器UI保留

## 四项证据产物

- `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\MODIFIED_FILE.exe`
- `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\DIFF_FILE.json`
- `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\VERIFICATION.txt`
- `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\installer\ROLLBACK.sh`

归档/EXE及完整可逆配方：`build/release-candidate/MODIFIED_FILE.zar`、`MODIFIED_EXECUTABLE.exe`、`DIFF_FILE.json`；分别保留改件和额外回滚副本。

## 完整构建命令、输入与字面结果

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
LAYER MOVIE AMANDA01 frames=339
LAYER MOVIE AMANDA02 frames=338
LAYER MOVIE BT_SIGHTING frames=389
LAYER MOVIE CHAPTER01 frames=90
LAYER MOVIE CHAPTER02 frames=90
LAYER MOVIE CHAPTER03 frames=90
LAYER MOVIE CHAPTER04 frames=90
LAYER MOVIE CHAPTER05 frames=90
LAYER MOVIE CHAPTER06 frames=90
LAYER MOVIE CHAPTER07 frames=90
LAYER MOVIE CHAPTER08 frames=90
LAYER MOVIE CHAPTER09 frames=90
LAYER MOVIE CHAPTER10 frames=90
LAYER MOVIE CHAPTER11 frames=90
LAYER MOVIE CHAPTER12 frames=90
LAYER MOVIE CHAPTER13 frames=90
LAYER MOVIE CHAPTER14 frames=90
LAYER MOVIE CHAPTER15 frames=90
LAYER MOVIE CHAPTER16 frames=90
LAYER MOVIE CL_SIGHTING frames=332
LAYER MOVIE FINAL frames=1052
LAYER MOVIE GENERATOR frames=471
LAYER MOVIE INTRO frames=413
LAYER MOVIE NEWSCAST frames=1139
LAYER MOVIE AMANDA01 frames=339
LAYER MOVIE AMANDA02 frames=338
LAYER MOVIE BT_SIGHTING frames=389
LAYER MOVIE CHAPTER01 frames=90
LAYER MOVIE CHAPTER02 frames=90
LAYER MOVIE CHAPTER03 frames=90
LAYER MOVIE CHAPTER04 frames=90
LAYER MOVIE CHAPTER05 frames=90
LAYER MOVIE CHAPTER06 frames=90
LAYER MOVIE CHAPTER07 frames=90
LAYER MOVIE CHAPTER08 frames=90
LAYER MOVIE CHAPTER09 frames=90
LAYER MOVIE CHAPTER10 frames=90
LAYER MOVIE CHAPTER11 frames=90
LAYER MOVIE CHAPTER12 frames=90
LAYER MOVIE CHAPTER13 frames=90
LAYER MOVIE CHAPTER14 frames=90
LAYER MOVIE CHAPTER15 frames=90
LAYER MOVIE CHAPTER16 frames=90
LAYER MOVIE CL_SIGHTING frames=332
LAYER MOVIE FINAL frames=1052
LAYER MOVIE GENERATOR frames=471
LAYER MOVIE INTRO frames=413
LAYER MOVIE NEWSCAST frames=1139
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

## 打包与验证

```powershell
python -X utf8 tools/build_installer.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward" --build build/release-candidate --dotnet "C:/path/to/dotnet.exe"
python -X utf8 tools/record_installer_verification.py
```

实际SDK路径/命令和完整输出（含59项C#断言）保存在`build/installer/build-commands.json`与`VERIFICATION.txt`。本机SDK10.0.402，锁定依赖不变。

```text
INSTALLER PASS bytes=78266941 sha256=cd047569e618e7f3b999bebdad445bf5eb67d39372e613a7fe886d905cb6560a self-contained=true isolated-install-restore=PASS input=unchanged game-launched=false
INSTALLER VERIFICATION PASS baseline=0 modified=0 rollback=0 install-restore=PASS UI=3 artifacts=4 reopened modified=retained game-launched=false
```

上述打包与记录命令均退出0；两份发布EXE逐字节相同。资源差分1,567,487 bytes，EXE差分1,176,157 bytes，总计2,743,644 bytes。EXE新增覆盖原始数据约20MB，但确定性压缩后并非20MB载荷。

## 恢复及保留状态

- 原件ZAR SHA256：`9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c`
- 原件EXE SHA256：`26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`
- 新ZAR SHA256：`126238583edfab7b1190625937e8715a91de65d6116b150ca719cdc90770957b`
- 新EXE SHA256：`e1e43f2aff92e3f3ef7a03f2a9a7987dd976c835ac19720bcf7a77b8d5f58c9e`
- rollback-sample及安装器real-sample两文件恢复原身份；归档/EXE改件、安装器、手测sample保留
- 原九文件最终身份复核不变；独立恢复目录补齐7个未修改配套文件后，9文件original模式核对通过

旧安装器保留`build/movie-overlay-release/previous-setup.exe`（原SHA c6cfe00169454df35588046c923f09c884453458c97e246456d19fcd0214abba）；旧完整候选和报告保留`build/movie-overlay-release/baseline/`。已装v1.0时先用旧安装器恢复原版，不直接覆盖未知目标。

[用户手动测试](MANUAL_TEST.md) · [原生实现及边界](MOVIE_OVERLAY.md)。离线帧PNG、指令/安装恢复通过不等于游戏内/GPU验收。
