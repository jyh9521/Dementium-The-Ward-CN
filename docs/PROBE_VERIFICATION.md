# 第二阶段实际执行证据

只代表静态、资源处理及隔离原生指令回放；GPU/image/sprite/VFS/allocator明确使用边界替身。游戏内验收尚未执行。

```text
Phase 2 minimal localization verification - 2026-10-23
Changed field: loc/en/UISSFrontend.tbl:0000
New Game -> 新游戏; runtime bytes=818d8f; EXE unchanged.
No game process launched. Native replay uses isolated emulation and explicit boundary doubles.
MODIFIED_FILE: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\phase2\MODIFIED_FILE.zar
DIFF_FILE: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\phase2\DIFF_FILE.json
VERIFICATION: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\phase2\VERIFICATION.txt
ROLLBACK: C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\ROLLBACK_PROBE.sh

TESTS
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 -m unittest discover -s tests -q
INPUT: synthetic fixtures
OUTPUT (literal):
----------------------------------------------------------------------
Ran 72 tests in 0.116s

OK
EXIT: 0

BASELINE
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 tools/build_probe.py baseline --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward"
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
OUTPUT (literal):
BASELINE PASS original-glyphs=180 noop=byte-identical native-decoder=byte-widen UTF8-not-decoded=true
EXIT: 0

MODIFIED
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 tools/build_probe.py modified --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward"
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
OUTPUT (literal):
MODIFIED PASS field=loc/en/UISSFrontend.tbl:0000 logical=新游戏 runtime=818d8f text-records=1 added-glyphs=3 original-glyphs=preserved native-replay=PASS reproducible=true
EXIT: 0

ROLLBACK
COMMAND: "C:\Program Files\Git\bin\bash.exe" tools/ROLLBACK_PROBE.sh
INPUT: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\phase2\MODIFIED_FILE.zar
OUTPUT (literal):
ROLLBACK PASS isolated-copy=original-sha256 text=New Game font=original modified-and-sample=retained
EXIT: 0

INPUT
COMMAND: C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 tools/investigate.py check-input --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward"
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
OUTPUT (literal):
INPUT PASS all-files=original-sha256 game-not-launched=true
EXIT: 0

Native font loader: original glyphs=180, modified glyphs=183; real loader/relocation replay=PASS; image/GPU boundary doubled.
Original SHA-256: 9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c
Modified SHA-256: 0b05719819898d46f11517df26abeca5e15e23bfa0117ddb58659657428eef18
Rollback SHA-256: 9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c
Restored status: original archive byte-identical, New Game and original font restored on isolated copy; MODIFIED_FILE and manual sample remain changed.
Rebuild twice from identical inputs: byte-identical.
Manual game visual acceptance: NOT_TESTED.
```

本地完整native-loader指标与VFS读取轨迹见build/phase2/original-loader.json、modified-loader.json；可提交摘要见assets/probe/。原字库及完整封包不提交。
