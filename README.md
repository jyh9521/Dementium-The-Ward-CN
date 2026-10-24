# 《病房：封闭病区》Steam PC 简体中文汉化工程

Dementium: The Ward，Steam AppID **3909960**，受支持原版 **build21501403 / Windows x64**。

已进行通关验收，暂未发现任何问题。

## 下载与安装

前往 [GitHub Releases](https://github.com/jyh9521/Dementium-The-Ward-CN/releases)。

- 支持 Steam Windows x64，AppID **3909960** / **build21501403**。
- 退出游戏，运行安装器，自动检测或选择游戏目录中的 `rom.zar`，依次点击“检查资源”与“安装汉化”。玩家无需 Python 或独立 .NET 运行时。
- 恢复原版：使用同一安装器检查资源，再点击“恢复原版”；保留 `cn-backup`，存档和设置不变。
- 若安装过早期同名 v1.0 候选，先用对应旧安装器恢复原版，再安装本次版本。
- 本次包含第十五章“初次相遇”、出口牌、红色手写字与汽水机四处修正。详见 [v1.0 版本说明](docs/RELEASE_V1_0.md)。

安装器 SHA-256：`5bd98a3d21403bada448ef154fcda22914f12b98cb9294b802d8d4aa5c505939`（78,497,853 字节）。

## 内容与技术

- 英语槽位278条表格/文档记录：241条翻译，37条制作人员姓名/公司保留。
- 独立验证本作UTF-8/BMP解码、binfont双zlib/重定位、字体生成、ZAR/TAR双索引与恢复；不是移植病房2旧偏移。
- 52张界面图片及23张场景纹理本地化；保护键帽、楼层数字/东西楼对应关系、密码、血迹与UV布局。
- 保留全部原视频/索引/音轨；运行时稀疏覆盖保留16段独立章名、2段内嵌章名、电影中文字幕及新闻/门牌画面译注；场内字幕仍按PCM采样位置触发。
- 独立 F1 原生调试菜单入口，保留原秘密序列启用的 L3+Y；根菜单和全部子菜单名称、布尔状态简体中文。
- 原版其他四语仅转为UTF-8以适配全局解码器，逻辑原文不变、不计作中文译文。
- 原件、完整归档、EXE、字体与媒体输出只在忽略目录；不写Steam目录，不自动启动游戏。

## 构建与验证

Python3.11+、锁定依赖、SHA锁定的Fusion Pixel12px字体及ffmpeg/ffprobe9.0.2。无需研究阶段的识别模型或美术生成服务即可重建。

```powershell
python -m pip install -r requirements.txt
python -X utf8 -m unittest discover -s tests -v
python -X utf8 tools/record_locale_verification.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward" --output build/framed-artwork-release
python -X utf8 tools/verify_sample.py --output build/framed-artwork-release
```

本次输出为build/framed-artwork-release/sample/；基线/修改/隔离恢复命令与字面输出保存于该目录VERIFICATION.txt。此前build/full、build/debug-menu为历史样本，未包含本轮文案/图片修正，勿混用。重复构建比较、全部原输入身份、文本/字形、未改成员、索引和原生指令回放均由工具校验。

## 安装器

`dist/Dementium-The-Ward-zh-CN-v1.0-Setup.exe`（v1.0，包含四处发布修正）：病房2同款Material Design 3界面，采用用户提供图标与顶图；自动检测/选择rom.zar、检查资源、安装汉化、恢复原版。仅支持受支持原版或本版已安装文件的完整身份；存档/设置不变，不启动游戏。[使用与重建](docs/INSTALLER.md)。

本轮31条短说明去掉末尾句号；真正文档/信件/对白不变。确认旧版3张重绘证据不足，已撤回并原样保留，见[图片复审](docs/IMAGE_READABILITY_REVIEW.md)。

## 文档

- [构建与恢复](BUILDING.md) · [手动测试](docs/MANUAL_TEST.md) · [已知边界](docs/KNOWN_ISSUES.md)
- [UTF-8解码](docs/UTF8_RUNTIME.md) · [binfont](docs/BINFONT_FORMAT.md) · [场内字幕](docs/AUDIO_SUBTITLES.md)
- [界面图片](docs/IMAGE_AUDIT.md) · [场景纹理](docs/INNER_TEXTURE_AUDIT.md) · [小字审计](docs/SMALL_PRINT_AUDIT.md)
- [原视频覆盖层](docs/MOVIE_OVERLAY.md) · [电影格式](docs/MOVIE_FORMAT.md) · [对白审计](docs/MOVIE_AUDIO_AUDIT.md) · [画面审计](docs/MOVIE_VISUAL_AUDIT.md) · [章名重建](docs/MOVIE_TITLE_REBUILD.md)
- [F1调试菜单与手动验收](docs/DEBUG_MENU.md) · [文本层](docs/DEBUG_MENU_TEXT.md) · [历史入口调查](docs/DEBUG_MENU_RESEARCH.md)
- [术语](GLOSSARY.md) · [上游与许可](NOTICE.md) · [许可边界](LICENSING.md) · [历史调查](TECHNICAL.md)

显示模式采用用户指定的“经典/高清”（含CRT变体）；原EXE部分语言共享该字面量，影响范围及原生selector验证见[显示模式命名](docs/DISPLAY_MODE_LABELS.md)。
