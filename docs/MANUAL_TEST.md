# 用户手动测试：全量离线候选

本项目工具没有启动游戏或写Steam安装目录。以下启动、游戏操作和截图均由用户执行；当前只有离线验收。

## 1. 核对新副本

副本路径：C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\full\sample

```powershell
$root = "C:/Users/noway/Downloads/Dementium-The-Ward-CN"
python -X utf8 "$root/tools/verify_sample.py"
Get-Content -LiteralPath "$root/build/full/VERIFICATION.txt"
```

预期SAMPLE PASS files=9 mode=localized hashes=exact game-launched=false。原版仅支持AppID3909960/build21501403。当前EXE和rom.zar都经过修改，不再使用旧phase2的原EXE哈希；准确身份见build-report.json。

## 2. 由用户启动副本

1. 备份自己现有存档/配置，关闭已运行的游戏。副本并不隔离全局存档、配置或Steam云状态。
2. 保持Steam运行、游戏语言English（中文使用en槽位）。在资源管理器打开上述sample目录，手动双击其中的Dementium.exe。
3. 进入菜单后核对实际进程路径，避免把Steam重定向的原版当作中文副本：

```powershell
Get-CimInstance Win32_Process -Filter "name='Dementium.exe'" | Select-Object ExecutablePath,CommandLine
```

实际路径应在build/full/sample。若出现要求Steam启动、重定向、报错或崩溃，记录提示、进程路径与日志后结束本轮；不向Steam安装目录复制改件。

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
& "C:/Program Files/Git/bin/bash.exe" "$root/ROLLBACK_LOCALE.sh"
Copy-Item -LiteralPath "$root/build/full/rollback-sample/rom.zar" -Destination "$root/build/full/sample/rom.zar"
Copy-Item -LiteralPath "$root/build/full/rollback-sample/Dementium.exe" -Destination "$root/build/full/sample/Dementium.exe"
python -X utf8 "$root/tools/verify_sample.py" --restored
```

预期SAMPLE PASS files=9 mode=original hashes=exact game-launched=false。恢复原归档SHA9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c、原EXE SHA26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e。

MODIFIED_FILE.zar与MODIFIED_EXECUTABLE.exe仍保留；需中文副本时从这两文件复制回sample并重新运行verify_sample.py。任何上述步骤都不以Steam安装目录为目标。
