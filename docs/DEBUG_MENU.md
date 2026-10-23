# 独立 F1 与简体中文原生调试菜单

日期：2026-10-23。当前手测包已更新为release-candidate，包含短说明句号调整与三项图片撤回；此前debug-menu输出为历史候选。只支持 AppID3909960 / build21501403；原 EXE SHA-256 为 `26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`。

## 实现与复用来源

复用 jyh9521/Dementium-II-CN 锁定 commit `c0ea10f93450972841e510ff82913920339bd058` 的完整身份门禁、F1 内部键码、原生菜单保留、UTF-8 数据池、已有重定位复用、逐层差分与独立恢复方法。没有采用其 ImGui、TTF、结构偏移或 hook 地址。本作入口依据 [本作调查](DEBUG_MENU_RESEARCH.md)，实现见 `tools/debug_menu.py`、`tools/debug_menu_text.py`。

### 已验证：文件及受控原指令层面

- Win32 F1 经本作转换器得到 Kore `0x1C`。`F8E50` 键盘回调入口增加无栈 leaf bridge，仅为 F1 设置/清除现存 raw48（全局 `3FC3F8` 的 bit48），其他键回到原逻辑；不启用键盘模拟手柄、不改两种键盘布局、不占用普通按键。
- 不置 `3FC416` 请求锁存位，避免在主菜单按键后排队到游戏中。原 `B6C00` 将 raw48 归一化为 action18，原 held/pressed 链生成上升沿，持续按住与系统重复 keydown 不生成多次进入。回放执行原 `3ED86..3EEF6` 的键盘/手柄合并、`3F00A` 的raw对象写入及 `BB6E0..BB74E` 内的原 `B6C00` 调用与边沿运算；摇杆使用中性合成状态，物理轮询/鼠标归一化不包含在内。
- `C0D80` 以原地12字节 BT/JNC/JMP 改写，保持在原函数的 unwind 范围内，不把非叶栈帧跳转到无 unwind 的新代码区；它仅在原全局 debugEnabled 未开启、request 未置位的路径补查 action18 新按。原忙碌/转场门禁、InGame 调用上下文及原生屏幕切换保留。F1 不写 debugEnabled 或任何作弊项。
- 手柄原逻辑不变：Frontend 依次 Y、Y、X、X、LB、RB、LB、RB、X、Y 切换启用状态；实际游戏内按住 L3 再新按 Y 进入。F1 不依赖这段序列，也不代替手柄解锁状态。
- 21 张本作命令表共325个名称指针（根70、子菜单255）、306个不同标签以及八个布尔回调的16处状态引用采用简体中文。章节/关卡 ID 原样保留；数字、格式及实际 callback 不改。
- 标签进入原生64字节行字段前守63 UTF-8 bytes，布尔状态守15 bytes。新字符纳入通用 binfont 生成管线，原字形保留。表指针仅复用原 DIR64 重定位；状态 LEA 保持 RIP 相对。
- 新增 `.locdbg` 为 RX（非可写）；代码为无栈 leaf/tail bridge，不新增 imports，不改变原函数 prologue/unwind。文字池随该只读 section 映射。ASLR 两基址独立回放。
- 调试层先逆向恢复，再恢复音频 overlay、固定字面量及 UTF-8 层；归档也恢复原 SHA。完整改件与待测副本保留。

地址均为本作 RVA，不是病房2偏移。离线回放会在声音、屏幕激活、格式输出或游戏 callback 边界使用明确替身，不能当作真实设备、GPU、转场或作弊效果验收。详细覆盖以生成的 `debug-replay.json`、`debug-text-replay.json` 为准。

## 重建与验证

仓库根目录执行：

```powershell
python -X utf8 -m unittest discover -s tests -q
python -X utf8 tools/record_locale_verification.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward" --output build/release-candidate
python -X utf8 tools/verify_sample.py --output build/release-candidate
& "C:/Program Files/Git/bin/bash.exe" ./build/release-candidate/ROLLBACK.sh
python -X utf8 tools/investigate.py check-input --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward"
```

基线只读校验原件和无修改往返；修改阶段从原件完整重复构建并比较；恢复阶段只写 `build/release-candidate/rollback-sample`。`VERIFICATION.txt` 记录实际命令、输入、字面输出、退出状态与四个产物路径。含完整游戏资源的改件、差分和样本只在忽略目录保留，不提交。

## 用户手动测试

1. 先运行 `verify_sample.py --output build/release-candidate`。待测目录为仓库 `build/release-candidate/sample`，不再使用旧 `build/full/sample` 检验本次功能。
2. 自行备份存档/配置。保持 Steam 运行、选择 English，从该 sample 手动启动 `Dementium.exe`；用 [通用手测说明](MANUAL_TEST.md) 中的进程路径查询确认没有重定向到 Steam 原版。工具没有启动游戏；副本也不是独立存档沙盒。
3. 不输入秘密序列，进入正常游戏后短按 F1；应打开简体中文原生调试菜单，且无敌等开关应保持原状态。按住 F1 不应反复触发；以 Esc/手柄返回退出，释放后再次 F1 应可进入。F1 是入口，不额外实现菜单内 F1 关闭。
4. 检查上下选择、左右减/增、Enter/Space 确认、Esc 返回；检查全部根菜单和子菜单、开/关状态、章节/关卡 ID、长名称、字体、分页末行和裁切。先用可逆显示项测试，记录每次状态；关卡跳转/物品/完成任务等操作不要用作正常进度存档。
5. 在 Frontend、暂停、地图、文档、转场和输入捕获情形各按/长按 F1，再返回正常游戏；检查没有排队打开、重复触发、卡住或输入泄漏。实际焦点、Steam Input 和真实转场仍由本步骤核验。
6. 重启副本，不用 F1，先确认未启用时 L3+Y 不进入；在 Frontend 输入 Y、Y、X、X、LB、RB、LB、RB、X、Y，再进入游戏按住 L3 新按 Y。确认进入中文菜单；再次秘密序列关闭后，手柄组合应重新受门禁控制，而 F1 仍独立可用。
7. 同时检查中文正文、文档、音频字幕和存读档没有回归；退出重启后不要假定手柄启用状态持久化。
8. 退出副本后执行上面的 ROLLBACK.sh。恢复结果是额外目录的原 `rom.zar` 和 `Dementium.exe`，原哈希相同；改件和 sample 不被覆盖。若需原版对照，先完整复制九文件sample到另备测试目录，再用这两个恢复文件覆盖该副本内对应文件，勿写 Steam 安装目录。

记录 EXE/归档 SHA、分辨率、输入设备/Steam Input 配置、当前页面、复现步骤及截图。真实画面、物理设备、菜单副作用和完整游戏流程仍待手动验收。
