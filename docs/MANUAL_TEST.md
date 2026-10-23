# 用户手动测试：全量离线候选

> 纵轴布局测试候选（本轮未生成安装包）：`build/yaxis-alignment/sample`，使用`verify_sample.py --output build/yaxis-alignment`。安装器操作见[INSTALLER.md](INSTALLER.md)。全文使用最新候选；历史build/full及build/debug-menu不用于本轮验收。

本项目工具没有启动游戏或写Steam安装目录。以下启动、游戏操作和截图均由用户执行；当前只有离线验收。

## 本轮纵轴布局优先测试

本轮旧安装器不含新修正，请使用下面的新sample，不要重复安装旧安装器来测本项。

1. 原先测试进程退出后，再启动build/yaxis-alignment/sample中的Dementium.exe，核对进程路径。
2. “纵轴：正常”与“纵轴：反转”应在同一水平线，左侧按键图标与文字间有明显留白，图标垂直居中。
3. 切换键盘/手柄图例以及窗口/全屏，确认按钮图案完整、未缩放变形，输入及设置切换仍正常。
4. 新副本回归上一轮已修复内容；旧build/ui-feedback-release/sample没有覆盖，便于对照。

技术与离线组合预览见[YAXIS_LAYOUT.md](YAXIS_LAYOUT.md)。

## 上轮四项截图反馈回归

1. 开头房间先实际听广播：本补丁没有按地点禁播或改原声触发；静音/未起播/零有效增益的声源不再产生字幕。声音是否原本可听仍以实听为准。
2. 打开记事本与钥匙拾取、文档、背包/暂停页：场内广播字幕隐藏，不与说明叠字；关闭页面按当前声音位置恢复，不回放过期句。
3. 出门后广播同一句只出现一行；继续听完整循环并切关，检查重复声源和不同播放进度不再上下双行。
4. 显示选项轮换应为经典、经典CRT、高清、高清CRT，效果与原模式对应。
5. F1菜单应离左边缘有留白；简易生命修改与开启/关闭分列，逐页检查武器/章节等子菜单。F1独立入口、秘密序列启用后的L3+Y均回归。

## 上轮通用回归参考（既有安装器不含本次纵轴修正）

1. 建议先对最新 `build/yaxis-alignment/sample` 测试，不必先改 Steam 安装目录；本轮只测新sample，既有安装器不含本次纵轴修正。
2. 若实际目录已装旧 v1.1，请先用旧安装器检查资源→恢复原版，再用 v1.1.1 安装。不要直接覆盖旧版两文件或删除 `cn-backup`。保留的旧安装器为 `build/ui-feedback-release/baseline/Dementium-The-Ward-zh-CN-Setup.exe`。
3. 电影内容顺序优先：INTRO/AMANDA01内嵌章名→独立章节卡→NEWSCAST上下同时字幕→GENERATOR对白→门牌顶部译注。检查英文标题不残留、红饰未遮挡、渐隐正确、剧情开始后遮罩消失。
4. 对电影执行跳过/重播、连续切片、暂停/恢复（游戏该路径支持时）；检查前片字幕没有黏在下一片，声音/画面时轴没有累计漂移。
5. 测试16:9与窗口/全屏及可用的其他画幅；中文应跟随电影缩放，而非固定桌面像素。
6. 然后回归原场内广播/首领字幕、F1菜单及秘密序列启用后的L3+Y，步骤见[调试菜单](DEBUG_MENU.md#用户手动测试)。统一使用最新样本，不使用历史调试样本。
7. 最后退出游戏，在副本上恢复原版并重新检查资源；保留存档、设置和未知用户文件。

实际GPU显示、帧时、声音同步以及实体手柄仍由用户验收。离线生成的PNG是覆盖层参考，不是本轮游戏截图。

## 1. 核对新副本

副本路径：C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\release-candidate\sample

```powershell
$root = "C:/Users/noway/Downloads/Dementium-The-Ward-CN"
python -X utf8 "$root/tools/verify_sample.py" --output "$root/build/yaxis-alignment"
Get-Content -LiteralPath "$root/build/yaxis-alignment/VERIFICATION.txt"
```

预期SAMPLE PASS files=9 mode=localized hashes=exact game-launched=false。原版仅支持AppID3909960/build21501403。当前EXE和rom.zar都经过修改，不再使用旧phase2的原EXE哈希；准确身份见build-report.json。

## 2. 由用户启动副本

1. 备份自己现有存档/配置，关闭已运行的游戏。副本并不隔离全局存档、配置或Steam云状态。
2. 保持Steam运行、游戏语言English（中文使用en槽位）。在资源管理器打开上述sample目录，手动双击其中的Dementium.exe。
3. 进入菜单后核对实际进程路径，避免把Steam重定向的原版当作中文副本：

```powershell
Get-CimInstance Win32_Process -Filter "name='Dementium.exe'" | Select-Object ExecutablePath,CommandLine
```

实际路径应在build/yaxis-alignment/sample。若出现要求Steam启动、重定向、报错或崩溃，记录提示、进程路径与日志后结束本轮；不向Steam安装目录复制改件。

## 3. 手动验收清单

- 主菜单新游戏、继续/存读档、难度、设置、物品说明；观察缺字、重叠、居中、上下裁切和所有分辨率/窗口方式。
- 键盘与各手柄操作图，检查中文说明与实际键帽/连线/布局一致。
- 记事本、病历、长文档、含配图查看页、彩色高亮及密码信息；确认换行/末行完整，谜题数字和字母不变。
- 医院地图、死亡画面、门牌/涂鸦/海报/白板、箱子与售货机；小尺寸纹理需在实际镜头下检查。
- 16段独立章名与INTRO/AMANDA01内嵌章名淡入/淡出、全部有对白电影、新闻与出口/检查室门牌顶部译注；检查字幕时轴、原音、跳过/重播及黑场。新闻TV及场景标牌英文并未透视重绘。
- 紧急广播、五种首领台词及歌声字幕；检查暂停恢复、循环、多个声音同时播放、打开文档/菜单、切关/结束音频后字幕消失。
- 完整流程、存读档和退出重进；局部菜单截图不等于通关验收。

报告记录：样本EXE/rom.zar SHA、分辨率、输入设备、章节/存档位置、复现步骤、完整截图及日志。字幕听校尤其关注GENERATOR高置信推断句；所有语音转写都未宣称人工实听验收。

## 4. 仅副本恢复对照

先退出副本。以下只恢复额外副本，再由用户选择覆盖sample两文件：

```powershell
& "C:/Program Files/Git/bin/bash.exe" "$root/ROLLBACK_LOCALE.sh" "$root/build/yaxis-alignment"
Copy-Item -LiteralPath "$root/build/yaxis-alignment/rollback-sample/rom.zar" -Destination "$root/build/yaxis-alignment/sample/rom.zar"
Copy-Item -LiteralPath "$root/build/yaxis-alignment/rollback-sample/Dementium.exe" -Destination "$root/build/yaxis-alignment/sample/Dementium.exe"
python -X utf8 "$root/tools/verify_sample.py" --output "$root/build/yaxis-alignment" --restored
```

预期SAMPLE PASS files=9 mode=original hashes=exact game-launched=false。恢复原归档SHA9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c、原EXE SHA26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e。

MODIFIED_FILE.zar与MODIFIED_EXECUTABLE.exe仍保留；需中文副本时从这两文件复制回sample并重新运行verify_sample.py。任何上述步骤都不以Steam安装目录为目标。
