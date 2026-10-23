# 全量离线候选验证

日期：2026-10-23。AppID3909960 / 本机Steam build21501403。没有启动游戏或修改Steam安装目录。

## 改动与身份

loc/en/*; other-locale encoding; BMP font; decoder RVA 0xEA700; audio HUD RVA 0xBFF10; reviewed images; IVF/DAT

- 文本278记录：241翻译、37姓名/公司保留；字体180→855 glyphs，79页，新增675项。
- UI：49程序化＋3美术＝52；场景纹理26。
- 电影：18个含章名文件（16独立章名＋2嵌入章名），18对白cue＋9画面词译注；SFX/歌声10cue。
- 内层基础图像507/507可见审计（504完整codec＋3独立只读基础层adapter）；34部影片633帧半秒样本查看。抽样不等于逐帧无遗漏证明。
- 原版其他四语1112记录只转码，原/新decoded stream相同；没有假称测宽/markup全量验收。
- EN native replay：278记录、670行，完整字库loader/relocation与字宽通过。
- 原始rom.zar SHA-256：`9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c`。
- 修改rom.zar SHA-256：`3f375b415d0465497c70320dc1a332686b9c923880213afed94581d7bd9b6d3e`。
- 修改EXE SHA-256：`02ee5ef7378e39f00f6ece2b020243c1266c132f49924ee047e19cf472344d32`。
- 197项测试通过；shell包装器语法/实际恢复退出0，verify_sample九文件通过，原安装九文件SHA复核一致。

## 四个本地交付物

- MODIFIED_FILE.zar: `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\full\MODIFIED_FILE.zar`（900461416 bytes；SHA-256 `3f375b415d0465497c70320dc1a332686b9c923880213afed94581d7bd9b6d3e`）
- DIFF_FILE.json: `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\full\DIFF_FILE.json`（317854751 bytes；SHA-256 `22df4036e0f6ba7f0fb37734e284aab0d2d616e14efb4ae9130b5b1c83d0cec9`）
- VERIFICATION.txt: `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\full\VERIFICATION.txt`（2598 bytes；SHA-256 `5d8b03deb07fa746c29cefc61306165f54a349a2a4d4b95d4f63f9630dff36f3`）
- ROLLBACK.sh: `C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\full\ROLLBACK.sh`（443 bytes；SHA-256 `8d7436870375d464481e5d9c8d328de000e214ac97240ca84e89c05d99b70080`）

完整EXE、归档、差分（包含变更TAR/媒体）、字体与图像仅在忽略目录，不提交。modified与手动sample均保留修改状态。

## 实际命令、输入和字面输出

### BASELINE

```text
C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py baseline --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\full --locale zh-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
BASELINE PASS records=278 archive-members=668 content-members=2555 noop=byte-identical input=unchanged decoder=byte-widen
EXIT STATUS: 0
STDERR: (empty)
```

### MODIFIED

```text
C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py modified --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\full --locale zh-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
MODIFIED PASS records=278 UTF8=roundtrip glyphs=855 dual-index=consistent reproducible=true native-replay=PASS game-launched=false
EXIT STATUS: 0
STDERR: (empty)
```

### ROLLBACK

```text
C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py rollback --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\full --locale zh-CN
INPUT: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\full\MODIFIED_FILE.zar
ROLLBACK PASS isolated-copy=original-sha256 text=New Game decoder=byte-widen font=original modified-and-sample=retained
EXIT STATUS: 0
STDERR: (empty)
```

## 附加复核

```text
C:/Program Files/Git/bin/bash.exe -n build/full/ROLLBACK.sh
OUTPUT: (empty)
EXIT STATUS: 0
C:/Program Files/Git/bin/bash.exe build/full/ROLLBACK.sh
ROLLBACK PASS isolated-copy=original-sha256 text=New Game decoder=byte-widen font=original modified-and-sample=retained
EXIT STATUS: 0
python -X utf8 tools/verify_sample.py
SAMPLE PASS files=9 mode=localized hashes=exact game-launched=false
EXIT STATUS: 0
python -X utf8 tools/investigate.py check-input --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward"
INPUT PASS all-files=original-sha256 game-not-launched=true
EXIT STATUS: 0
```

## 恢复与边界

恢复在额外rollback-sample写入原版rom.zar及EXE，New Game、原180字形和byte-widen decoder身份恢复；不覆盖modified或sample。完整三步再现时，修改构建独立重复一次并比较全部输出。

媒体保持VP9/400×240/原帧数/PTS/音轨，DAT独立重算关键帧/offset/size。字幕/章名允许区域外解码YUV逐字节相同；章名处理覆盖18文件2192帧，573帧后续剧情原样透传，保留红装饰/源fade及独立章名首尾黑场。另从编码后的INTRO/AMANDA01提取帧45确认中文章名。

以上为离线资源、媒体和真实指令回放。GPU提交、实际进程、听校、真实并发、完整剧情与存读档仍待用户手动验收；步骤见MANUAL_TEST.md。新闻TV/门牌英语采用顶部画面词译注，不冒称透视重绘；有意保留的专名/谜题/低清笔迹见KNOWN_ISSUES.md。
