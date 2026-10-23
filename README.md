# 《病房》Steam PC 简体中文汉化工程

Dementium: The Ward，Steam AppID **3909960**，受支持原版 **build21501403 / Windows x64**。

当前为全量汉化的可复现离线候选构建，**未启动游戏，尚待玩家实际画面与流程验收**。已提供自包含安装器候选，尚未发布正式Release。

## 内容与技术

- 英语槽位278条表格/文档记录：241条翻译，37条制作人员姓名/公司保留。
- 独立验证本作UTF-8/BMP解码、binfont双zlib/重定位、字体生成、ZAR/TAR双索引与恢复；不是移植病房2旧偏移。
- 52张界面图片及23张场景纹理本地化；保护键帽、楼层ID、密码、血迹与UV布局。
- 保留全部原视频/索引/音轨；运行时稀疏覆盖保留16段独立章名、2段内嵌章名、电影中文字幕及新闻/门牌画面译注；场内字幕仍按PCM采样位置触发。
- 独立 F1 原生调试菜单入口，保留原秘密序列启用的 L3+Y；根菜单和全部子菜单名称、布尔状态简体中文。
- 原版其他四语仅转为UTF-8以适配全局解码器，逻辑原文不变、不计作中文译文。
- 原件、完整归档、EXE、字体与媒体输出只在忽略目录；不写Steam目录，不自动启动游戏。

品牌、人员姓名、解谜字母/数字、运输符号及不可可靠辨读的小字有独立清单，不将它们虚构为确定台词。媒体转写包含明确分级的推断，详见调查文档。

## 构建与验证

Python3.11+、锁定依赖、SHA锁定的Fusion Pixel12px字体及ffmpeg/ffprobe9.0.2。无需研究阶段的识别模型或美术生成服务即可重建。

```powershell
python -m pip install -r requirements.txt
python -X utf8 -m unittest discover -s tests -v
python -X utf8 tools/record_locale_verification.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward" --output build/release-candidate
python -X utf8 tools/verify_sample.py --output build/release-candidate
```

本次输出为build/release-candidate/sample/；基线/修改/隔离恢复命令与字面输出保存于该目录VERIFICATION.txt。此前build/full、build/debug-menu为历史样本，未包含本轮文案/图片修正，勿混用。重复构建比较、全部原输入身份、文本/字形、未改成员、索引和原生指令回放均由工具校验。

## 安装器

`dist/Dementium-The-Ward-zh-CN-Setup.exe`（v1.1）：病房2同款Material Design 3界面，采用用户提供图标与顶图；自动检测/选择rom.zar、检查资源、安装汉化、恢复原版。仅支持受支持原版或本版已安装文件的完整身份；存档/设置不变，不启动游戏。[使用与重建](docs/INSTALLER.md)。

本轮31条短说明去掉末尾句号；真正文档/信件/对白不变。确认旧版3张重绘证据不足，已撤回并原样保留，见[图片复审](docs/IMAGE_READABILITY_REVIEW.md)。

## 文档

- [构建与恢复](BUILDING.md) · [手动测试](docs/MANUAL_TEST.md) · [已知边界](docs/KNOWN_ISSUES.md)
- [UTF-8解码](docs/UTF8_RUNTIME.md) · [binfont](docs/BINFONT_FORMAT.md) · [场内字幕](docs/AUDIO_SUBTITLES.md)
- [界面图片](docs/IMAGE_AUDIT.md) · [场景纹理](docs/INNER_TEXTURE_AUDIT.md) · [小字审计](docs/SMALL_PRINT_AUDIT.md)
- [原视频覆盖层](docs/MOVIE_OVERLAY.md) · [电影格式](docs/MOVIE_FORMAT.md) · [对白审计](docs/MOVIE_AUDIO_AUDIT.md) · [画面审计](docs/MOVIE_VISUAL_AUDIT.md) · [章名重建](docs/MOVIE_TITLE_REBUILD.md)
- [F1调试菜单与手动验收](docs/DEBUG_MENU.md) · [文本层](docs/DEBUG_MENU_TEXT.md) · [历史入口调查](docs/DEBUG_MENU_RESEARCH.md)
- [术语](GLOSSARY.md) · [上游与许可](NOTICE.md) · [许可边界](LICENSING.md) · [历史调查](TECHNICAL.md)

显示模式采用用户指定的“经典/高清”（含CRT变体）；原EXE部分语言共享该字面量，影响范围及原生selector验证见[显示模式命名](docs/DISPLAY_MODE_LABELS.md)。
