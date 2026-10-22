# 《病房》Steam PC 简体中文汉化工程

Dementium: The Ward，第一阶段：技术调查与资源处理基线（2026-10-23）。**目前没有可安装的中文补丁。**

## 当前目标

- Steam AppID **3909960**；本机实测 build **21501403**。不是《病房2》，不沿用其支持版本或 EXE 偏移。
- Windows x64 `Dementium.exe`；输入身份见 `assets/original-identity.json`。
- Steam 安装目录只读；未启动游戏、未做游戏内验收。
- ZAR1：668 成员；内层 CONTENT.TAR：2555 成员（2522 文件）。英文文本 131 资源、278 记录；当前译文覆盖率 0%。

## 第一阶段交付

- [调查与结论](TECHNICAL.md) · [文件格式](docs/FILE_FORMATS.md)
- [迁移评估](docs/MIGRATION_ASSESSMENT.md) · [覆盖率与源身份](assets/inspection/coverage.json)
- [离线验证记录](docs/VERIFICATION.md) · [已知问题](docs/KNOWN_ISSUES.md)
- [重现命令](BUILDING.md) · [翻译规范](TRANSLATING.md) · [术语起点](GLOSSARY.md)

《病房2》的 ZAR、双索引和稀疏差分核心已按函数复用，并在本作原包验证。文本、字体与图片路线不相同：文本在 TAR 内，字库是 `.binfont`，319 个 `.PNG` 扩展名成员并非标准 PNG。

**New Game → 新游戏：**已定位 `CONTENT.TAR/loc/en/UISSFrontend.tbl:0000`，资源回写条件成立；中文运行时解码、binfont 码点映射与补字仍未确认，因此尚不具备中文显示最小闭环。当前仅保存 ASCII 离线探针，不生成假定可运行的中文包。

## 快速复现

Python 3.11+，当前工具仅使用标准库，实测 Python 3.14.2：

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 tools/investigate.py scan --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward"
python -X utf8 tools/record_verification.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward" --bash "C:/Program Files/Git/bin/bash.exe"
```

输出在 Git 忽略的 `build/phase1/`。完整文本清单仅本地生成，不提交原版资源、字体、EXE 或完整文本副本。源码不含 F1 菜单、安装器与 Release。详见 [许可与来源](LICENSING.md)。
