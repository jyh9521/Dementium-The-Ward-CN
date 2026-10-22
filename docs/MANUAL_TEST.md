# 用户手动测试：只看主菜单

状态：样本离线验证完成；以下步骤由用户执行。本阶段没有自动启动游戏，也没有写Steam安装目录。

## 1. 确认副本

路径：`C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\phase2\sample`

副本包含原EXE/DLL与修改后的rom.zar；不要将样本复制到Steam安装目录。原版AppID3909960、build21501403。样本中Dementium.exe应仍为SHA：

`26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`

rom.zar SHA见 `build/phase2/build-report.json` 的modified_sha256及PROBE_VERIFICATION.md。

## 2. 手动启动与截图

1. 保持Steam已运行，并将游戏语言设为English（样本仅替换loc/en首条）。
2. 在资源管理器打开上述sample目录，**手动双击此副本里的Dementium.exe**。
3. 进入主菜单，检查首项是否为“新游戏”；观察三字是否完整、顺序正确、无方框/重叠/上下裁切。其余菜单仍为原文。
4. 本轮只检查主菜单，不点击“新游戏”开始流程，也不操作存读档。副本未隔离游戏的全局配置/存档位置，不能当作独立存档环境。
5. 保存一张包含整个主菜单的截图，并记录分辨率、窗口/全屏状态及异常；然后退出副本。
6. 若显示要求通过Steam启动，或进菜单前报错，请记录提示/日志与当前目录，停止本轮；不要替换安装目录来绕过该结果。

## 3. 可选原样恢复对照（仅副本）

关闭副本后，在PowerShell执行：

```powershell
$root = "C:/Users/noway/Downloads/Dementium-The-Ward-CN"
& "C:/Program Files/Git/bin/bash.exe" "$root/tools/ROLLBACK_PROBE.sh"
Copy-Item -LiteralPath "$root/build/phase2/ROLLBACK_COPY.zar" -Destination "$root/build/phase2/sample/rom.zar"
Get-FileHash -LiteralPath "$root/build/phase2/sample/rom.zar" -Algorithm SHA256
```

恢复后的SHA必须为 `9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c`。此步骤恢复的是sample；MODIFIED_FILE.zar仍保留。随后手动启动同一副本，可对照New Game原文。重新构建modified会再次准备中文样本；运行后新产生的日志应先移至build内独立记录位置，构建工具不会擅自清空未知样本文件。

## 验收报告最小字段

- 样本rom.zar SHA
- 分辨率/窗口状态
- 首项截图与是否完整显示“新游戏”
- 其余菜单是否保持/异常提示及日志

这次主菜单验收不等于全量文本、游戏流程或存档兼容验收。
