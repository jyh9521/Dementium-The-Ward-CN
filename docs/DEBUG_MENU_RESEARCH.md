# 隐藏调试菜单：离线入口调查

> 后续状态：该文保留入口调查当时的未启用结论；现在的独立F1、手柄原启用门禁及简中菜单候选见[恢复实现与手测](DEBUG_MENU.md)。

日期：2026-10-23。仅针对Steam AppID3909960/build21501403的原版x64 EXE：4673536 bytes，SHA-256 `26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`。下面地址均为RVA；首选ImageBase为0x140000000。

**结论：完整原生菜单保留，原始手柄解锁/进入路径也保留；具备恢复键盘入口的技术基础。本轮没有制作或启用恢复补丁，没有启动游戏，没有修改Steam目录或现有汉化待测副本。**

## 已验证：不仅是残留命令名

- UIManager构造B9930在BA234无条件调用C6C00，菜单对象位于manager+4F60；RTTI/vtable明确为`UISSDebugMenu`、`tUIScreen<25>`。
- C6C00把根命令表2EA510写入menu+D20，条目数70，每项16 bytes（name pointer、callback pointer）；建立12行左右两列按钮回调。入口不是ImGui。
- C71F0负责页面初始化，C62A0逐条查询状态与填充标签；C72B0通过本作EA700/EADC0文本路径绘制12行名称与数值。C67A0/C69C0调用表中callback执行减少/增加/确认，另有子菜单堆栈与返回代码。
- 根表包含Invincible、RefillHealth、AddAllItems、AddAllMaps、Weapons、CompleteMission、关卡子菜单及环境参数。命令存在不等于每条操作的实际游戏效果已验收。
- `ShowDebugUi`回调C5F60切换3FC40B，读取者为HUD绘制路径BFE9E；**它不是打开菜单的入口开关**。

## 已验证：原始手柄入口

在`UISSFrontend`更新CF730中，原字符串3122F0为：

```text
TTSSLRLRST
```

它是内部按键符号，不是要求键盘输入这些英文字母。XInput wButtons →原始转换跳表→GenericInputProfile字段→raw64→B6C00 action32的逐阶段原指令回放，确认Xbox标识对应：

| 符号/用途 | 实际按键 | wButtons | raw位 | UI action位 |
|---|---|---:|---:|---:|
| T | Y | 0x8000 | 2 | 7 |
| S | X | 0x4000 | 3 | 8 |
| L | LB | 0x0100 | 8 | 12 |
| R | RB | 0x0200 | 9 | 13 |
| 进入组合的按住部分 | 左摇杆按下 L3 | 0x0040 | 14 | 16 |

因此原始代码表达的操作顺序是：

1. 在Frontend接收输入期间，依次新按并释放 **Y、Y、X、X、LB、RB、LB、RB、X、Y**。
2. 匹配完成后，CF730翻转全局3FC398，并调度提示音资源01000069。再次完整输入会关闭，而不是永久解锁。
3. 进入实际游戏的UIMSInGame输入路由后，**按住L3，再新按Y**，请求打开调试菜单。

这是原始代码/受控离线回放得出的入口，**尚未进行真实手柄、Steam Input、画面或音效验收**。不能把上述顺序描述为已经现场按键成功。

### 入口条件与生命周期

C0D40被UIMSInGame更新C1060调用，其准确条件为：

```text
manager+64 == 0
AND (request_3FC416 != 0 OR debugEnabled_3FC398 != 0)
AND (
    ((held & 0x10000) != 0 AND (pressed & 0x80) != 0)
    OR (pressed & 0x40000) != 0
    OR request_3FC416 != 0
)
```

满足后清除request_3FC416，经声音边界调用BBCB0(manager, manager+4F60)请求切换屏幕。

- BB6E0调用B6C00把raw64转换为action32，写manager+40 held、+44 pressed、+4C release、+48 repeat；因此这里的“新按”是上升沿，而非持续按住。
- manager+64忙碌/转场标志会阻止入口。BB6E0的上层输入捕获分支也可能清除pressed，真实焦点/输入捕获仍须实机核对。
- 序列识别遇到不匹配符号或0xC27F屏蔽组的输入会复位进度。代码没有基于该页面帧计数的序列超时判断。
- 3FC398位于零初始化区域，本轮写引用检查找到CF730的toggle，没有据此声称配置/存档持久化；进程重新初始化后不应假定仍解锁。
- 渲染函数3FF20在该标志开启时生成带` *debugEnabled`的窗口标题；这是另一个可供用户后续观察的线索，不是本轮真实窗口截图。
- 菜单输入C75D0：上下选择、左右减少/增加、确认、返回；键盘导航的逻辑映射有箭头、Enter/Space、Esc，但未验收实际鼠标命中、滚动、布局或所有命令副作用。

## 已验证：为何不是默认F1

真实注册链为1F6120的RegisterClassExW →1F7920 →1F7B40 →DesktopD3D12WindowDriver.vtable+8=1F1F00。WM_KEYDOWN/UP通过1F1210转换VK为Kore::KeyCode，再进入原生输入回调。

- F1的VK0x70转换为Kore0x1C，而不是0x70。两张默认布局表2EAF80/2EB160各30项，均没有F1、raw14或raw48的绑定；所以不能把C0D40的action18判断直接称为“原生F1”。
- 3FC416还有一个直接请求路径：F8E50在keydown且映射含raw48时置1；B6C00也把raw48映射为action18。但默认键表没有生成这个位的条目。
- 默认布局表虽含序列所需部分raw位，F8E50对纯raw8/9键按下还有限定当前屏幕的白名单，Frontend不在其中。因此只看表得到的M/Tab、R、Z、X组合，不能当作可用键盘解锁步骤。

### 键盘模拟手柄：代码存在，但启动明确关闭

126330在inputDriver+418非零时把键盘映射为手柄字段，另继续调用普通键盘callback。静态映射及原指令条件回放确认：S→Y、A→X、Q→LB、W→RB、C→L3。因此在**启用这个模拟器的分析fixture**中，序列对应`SSAAQWQWAS`、入口对应C+S。

但实际启动流程不是这个状态：

- FA670构造先置+418=1。
- PCSimpleInputProfile vtable3134C8的slot+68为F8BC0 setter。
- FA60A加载该slot，FA611清EDX，FA616以false调用setter，**把+418从1改为0**，然后FA627注册普通键盘callback。
- 两个ASLR基址下直接执行原FA60A..FA619与原F8BC0，均得到1→0；这段验证没有函数边界double。

所以`SSAAQWQWAS`/C+S不是本轮交付的可用默认按键，也没有修改文件启用它。仅恢复整个模拟器会额外引入普通游戏键盘与模拟手柄重叠，不能不加分析就作为最终恢复方案。

## 恢复可行性与《病房2》对照

**高置信推断：可以基于本作现存菜单恢复方便的键盘入口，无需重建整套作弊界面。** 已有对象构造、文本绘制、页面生命周期、命令调度及实际进入条件，不是只剩字符串。

后续可单独实现的优先方案是：受版本/SHA/原字节守卫的F1新按入口，复用本作既有菜单请求/切屏函数，保留转场门禁、实际InGame上下文和原菜单生命周期。F1默认不自动开启任何作弊项；退出、重复按键、暂停/文档页、输入捕获、保存状态及与当前UTF-8/音频HUD补丁叠加都应独立验证。不要只翻转ShowDebugUi，更不要为了一个热键启用整套键盘手柄模拟。

可以复用《病房2》的版本门禁、上升沿测试、完整输入链回放、逆向恢复与中文标签维护经验；不复用它的RVA、结构偏移或ImGui/鼠标补丁。本作当前证据是自绘UISSDebugMenu，不等于《病房2》那套界面。

本轮**没有生成F1恢复EXE、注入模块或安装器**，现有汉化构建与sample身份保持原状态。屏幕真正显示、输入设备兼容、菜单命令效果及游戏流程仍未测试。

## 可复现离线验证

源码工具只接受原始EXE的完整大小/SHA，输出限制到仓库build/，不运行Windows游戏进程，不修改EXE，不调用实际XInput、窗口、音频或Steam API。

```powershell
python -X utf8 tools/research_debug_menu.py --exe "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward/Dementium.exe"
```

实际字面输出（退出0）：

```text
DEBUG RESEARCH PASS bases=2 opening-cases=26 sequence-toggles=4 raw-bits=128 VK-cases=30 xinput-bit-cases=32 keyboard-mode-cases=20 startup-disable=2 input=unchanged executable-modified=false game-launched=false
```

默认报告`build/debug-menu-research/replay.json`已重开核验。0x140000000/0x180000000两基址覆盖26个入口条件、4次秘密序列toggle、128个raw单bit、30个VK转换、32个XInput onehot、20个键盘模拟模式及2个真实启动关闭回放。

**回放边界：**入口验证把FD620/FD730声音调用和BBCB0屏幕激活请求设为double；没有执行GPU绘制或真实页面转场。XInput验证在原始提取/跳表/字段存储/raw合成/action归一化阶段之间显式传递捕获值，不执行实际轮询线程与回调脚手架。序列回放使用合成对象和归一化动作；物理手柄映射由独立原指令阶段交叉确认，不能合并冒充一次真实设备端到端运行。

追加测试：`python -X utf8 -m unittest discover -s tests`，200项通过。`investigate.py check-input`确认原安装九文件SHA相同；`verify_sample.py`确认原有中文sample九文件身份未变。

## REA证据索引

完整局部反编译/指令和实验报告仅在忽略目录`build/debug-menu-research/`；反编译文本不是原始源码。主要Evidence：

| 结论 | Evidence ID |
|---|---|
| 菜单构造/类名/根表/按钮 | ev_3cb289da0d25bd4ef8d6db0d1fe59410f1eca72518ef60a6f6780146d51040f0 |
| UIManager无条件构造 | ev_af52630f0ca1131cf3206730eed6732e59b48da6e92809a8bd201c661e1e25ca |
| 进入条件 | ev_0077ca32edf271136c23a91aaa9c048889cceaa44a3b0fa8929c54db28ae7877 |
| 秘密序列与toggle | ev_3030eb98c7fa9b9df92e6bf23268b9b536cb8af18fc57072c7434613f273eb45 |
| 菜单绘制 | ev_5dab18968c0f74283214765d1074cefc1e060ca73011d240210fa944eac4d974 |
| raw归一化 | ev_21e8be96109f32400f34ac05c027362925e12172fe1bce5cfe80d7d1efe4db77 |
| held/pressed/dispatch | ev_7ec562936fe1f2ba8e8972da9d6c7cf1ceadbb62bf4c5e4fa341c50f5443a0db |
| VK转换 | ev_e0696612ed6006b931339209f84772a1c16f83e889b9ceb3aee7df826b6d14ca |
| 默认布局与raw48请求 | ev_313fa400de5b6f3c8755db76bcba2f81e8eae5f9413ac610dfc1113eae95164f |
| 键盘模拟路径 | ev_3ae412be79199cf4ee804d6da8d78bf701a6be1aecb34e36c2b6115f5846fb51 |
| 实际启动false调用 | ev_a111954897002d51f2a4ae5b7e5ce3fcdfb88c2e192f2ec8d5e724883410872e |
| XInput提取/调度（伪代码有临时表恢复限制，已按原指令回放复核） | ev_3886875c1b669f7706cb70c5c9712031fc0b844648bbf3ea7e78061c25283bfb |

尚未确认项：真实设备/Steam Input映射、菜单画面与触控/鼠标布局、全部命令副作用、后续F1补丁的具体实现与叠加验收。
