# 独立 F1 调试菜单：本轮离线验证

日期：2026-10-23。所有命令均未启动游戏；Steam安装目录只读，九文件身份复核相同。

## 改动字段

loc/en/*; other-locale encoding; BMP font; decoder RVA 0xEA700; audio HUD RVA 0xBFF10; reviewed images; IVF/DAT; independent F1 raw48/action18; native enabled L3+Y; localized debug menu

## 真实产物

- `MODIFIED_FILE.zar`：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\debug-menu\MODIFIED_FILE.zar`；SHA-256 `274ebc955f4b105e3fb5c986fb73dc73b255a8d61b9f6dbfd258901c84d4981c`
- `DIFF_FILE.json`：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\debug-menu\DIFF_FILE.json`；SHA-256 `2b597a5a0b3d27f8ba959d86019389d4156a75c2fa6d2b5e82a5fcc4cee5fc92`
- `VERIFICATION.txt`：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\debug-menu\VERIFICATION.txt`；SHA-256 `3fbb8d47da0beee04bbf502040ff05b79e9791d72a32cf5cbc896edb4c667aa0`
- `ROLLBACK.sh`：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\debug-menu\ROLLBACK.sh`；SHA-256 `8d7436870375d464481e5d9c8d328de000e214ac97240ca84e89c05d99b70080`

- `MODIFIED_EXECUTABLE.exe`：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\debug-menu\MODIFIED_EXECUTABLE.exe`；SHA-256 `5c2f8a325023cdc43a010047a2026ab2b020b5b054faa0ba8ce684b081dee3da`

## 实际命令、输入与字面输出

### BASELINE

```text
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py baseline --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\debug-menu --locale zh-CN
CWD: C:\Users\noway\Downloads\Dementium-The-Ward-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
STDOUT:
BASELINE PASS records=278 archive-members=668 content-members=2555 noop=byte-identical input=unchanged decoder=byte-widen
STDERR:

EXIT STATUS: 0
```

### MODIFIED

```text
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py modified --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\debug-menu --locale zh-CN
CWD: C:\Users\noway\Downloads\Dementium-The-Ward-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
STDOUT:
MODIFIED PASS records=278 UTF8=roundtrip glyphs=884 dual-index=consistent reproducible=true native-replay=PASS game-launched=false
STDERR:

EXIT STATUS: 0
```

### ROLLBACK

```text
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py rollback --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\debug-menu --locale zh-CN
CWD: C:\Users\noway\Downloads\Dementium-The-Ward-CN
INPUT: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\debug-menu\MODIFIED_FILE.zar
STDOUT:
ROLLBACK PASS isolated-copy=original-sha256 text=New Game decoder=byte-widen font=original modified-and-sample=retained
STDERR:

EXIT STATUS: 0
```

## 回放与附加验证

```text
python -X utf8 -m unittest discover -s tests -q
----------------------------------------------------------------------
Ran 215 tests in 41.748s

OK
EXIT STATUS: 0

& "C:/Program Files/Git/bin/bash.exe" ./build/debug-menu/ROLLBACK.sh
ROLLBACK PASS isolated-copy=original-sha256 text=New Game decoder=byte-widen font=original modified-and-sample=retained
EXIT STATUS: 0

python -X utf8 tools/verify_sample.py --output build/debug-menu
SAMPLE PASS files=9 mode=localized hashes=exact game-launched=false
EXIT STATUS: 0

python -X utf8 tools/investigate.py check-input --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward"
INPUT PASS all-files=original-sha256 game-not-launched=true
EXIT STATUS: 0
```

最终改件再次回放：两个基址、160个入口条件、48个原生raw合并条件、650次名称复制、32次布尔查询、308项译文实际UTF-8解码与测宽。两种键位布局、重复/释放、busy消退无排队、秘密序列、原始XInput映射、上下/左右/确认/返回分派均通过。

恢复仅写额外rollback-sample：原New Game、原字库、单字节decoder、原调试门禁/无独立F1；原归档和EXE大小/SHA相同。修改包及sample仍保留。

- 恢复EXE SHA-256：`26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`
- 恢复归档 SHA-256：`9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c`

离线图形/音效/页面激活/游戏效果存在明确边界替身；摇杆为中性合成对象。真实设备、Steam Input、焦点捕获、菜单画面及命令副作用、完整流程仍待玩家手测。见 [手动验收](DEBUG_MENU.md#用户手动测试)。
