# 《病房》Steam PC 简体中文汉化工程

Dementium: The Ward，当前阶段：**仅 New Game → 新游戏的最小离线实验**（2026-10-23）。尚未游戏内验收，不是正式汉化发行包。

## 输入与范围

Steam AppID **3909960**，本机实测 build **21501403**，Windows x64。原件身份见 `assets/original-identity.json`；不套用《病房2》的版本、EXE偏移或F1功能。

- 278条英语记录中仅改1条：`CONTENT.TAR/loc/en/UISSFrontend.tbl:0000`。
- 仅两个内层成员改变：菜单表与 `.binfont`。EXE及其他输入文件保持原样。
- 原180字形及原图集像素保留；追加Fusion Pixel12px三字，图集128×256→128×512。
- 本作菜单不是UTF-8解码；逻辑译文保持真实中文，构建期可逆映射到未使用单字节槽位 `81 8D 8F`。这是有限字槽POC，不是全游戏中文编码方案。
- 原版目录只读，样本位于 `build/phase2/sample/`，未启动游戏。

## 重现

Python 3.11+及锁定依赖；本机已安装并按哈希验证的Fusion Pixel字体。详见[构建说明](BUILDING.md)。

```powershell
python -m pip install -r requirements.txt
python -X utf8 -m unittest discover -s tests -q
python -X utf8 tools/record_probe_verification.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward" --bash "C:/Program Files/Git/bin/bash.exe"
```

所有构建、测试、指令仿真与恢复均不执行游戏。完整原件、字库、样本与差分只留Git忽略目录；不包含安装器或Release。

## 文档

- [第二阶段调查与最小实验](docs/MINIMAL_PROBE.md) · [中文解码证据](docs/TEXT_DECODING.md)
- [binfont格式](docs/BINFONT_FORMAT.md) · [字体来源](docs/FONT_SOURCE.md)
- [手动测试步骤](docs/MANUAL_TEST.md) · [实际验证记录](docs/PROBE_VERIFICATION.md)
- [第一阶段原始调查](TECHNICAL.md) · [上游迁移评估](docs/MIGRATION_ASSESSMENT.md)
- [文件格式](docs/FILE_FORMATS.md) · [已知问题](docs/KNOWN_ISSUES.md) · [许可](LICENSING.md)
