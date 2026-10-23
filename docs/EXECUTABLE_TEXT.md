# EXE player-visible text audit

日期：2026-10-23。只读输入为本作build21501403的4673536-byte x64 EXE，SHA-256 `26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`。没有启动游戏，没有写入Steam安装目录。

## 已验证：候选扫描边界

第一阶段`build/phase1/executable-string-candidates.json`总输入SHA-256 `01cfa8b31059a873b5136696e3c3d17a2819f0a2d1fcde84f3db5ac08226875f`，筛选file=Dementium.exe得到14980条候选。该清单包含机器指令误识别、SDK文字、路径、开发控制台、RTTI与少量自然语言，候选不等于玩家可见UI。

- `Display Resolution`、`Filters`、`Anti-aliasing`、`Graphics Options`不存在精确/大小写不敏感匹配。
- `Resolution`的两处候选来自spiller.toml默认配置和JSON schema字段，不是经证实的可译标签。保留配置键与枚举。
- 选项正常渲染的`C24E0`已经调用EA700；其读取的`UIOptionsNew.tbl`资源列入结构化翻译，不重复在EXE寻找/创造等价译文。
- 游戏相关EXE段中大量`Load ...`、`Invincible`、`ShowDebugUi`、`RelockAchievements`、武器/世界实体名称属于开发工具或机器标识候选，未列入普通玩家文本翻译。
- `ACTION!`、`RESTART!`、`EXIT!`已追踪至severity=2的日志调用；`Album`是成就机器ID；`Impossibru`是异常终止消息，不进入正常绘制。详见下表。
- 本轮没有获得必须修改且独立于资源表的普通玩家标签。`locales/zh-CN/executable-text.json`因此保留空entries，避免误改日志/API/路径/品牌/按键/机器ID。

这只覆盖已扫描的ASCII/UTF-16候选和已分析静态引用，不证明整个游戏绝无额外可见文字。没有观察到需要另移植ImGui中文字库的正常PC选项面板；也不据此宣称任意第三方debug界面支持中文。

## 可复用的受守卫适配模块

`tools/executable_text.py`复用jyh9521/Dementium-II-CN的同名成熟fixed-slot工具，来源commit `d3fbc4130bca6a1376e36f9f67b569b08d402680`（MIT），移除了不适用于本作的debug_menu分支，新增HUD资源byte容量验证。没有复制病房2的AppID、偏移、具体文本槽、哈希或原生作弊菜单。

`build_executable(data,recipe)`检查输入整文件大小/SHA、PE .rdata只读非可执行范围、零填充expected bytes、UTF-8+NUL容量与不重叠约束；`apply_executable_patch(...,reverse=True)`同时检查前后身份及byte守卫。实际空recipe绑定UTF-8运行时补丁输出SHA `5f2b955b9af968107cadb6af8ec5121be8dc39ae599b9b88cc215343035d007d`，可按runtime→literal顺序构建并逆序恢复，当前literal阶段byte-identical。未新增section或指针重定向。

## 已验证：open/unlock固定字段容量

静态入口`A94A0`（Evidence `ev_047120cee971102b5eabea42932402c690b789b4f3297d75b1afa5e8e0520b6a`）构建`loc/<语言>/open.*`路径并调用E9350读取原byte。根对象`+0x1af4`相关flag分支中，一条路径保存原byte指针到`+0x1b10`；另一条路径逐byte、不带上限地复制到`+0x1740`直到NUL，随后把`+0x1840`、`+0x1940`置空并设置显示flag。相关连续HUD字段间隔256byte。不能因为EA700支持4095个Unicode单位就取消这个更窄的byte门禁。

`validate_hud_capacity`对所有open/unlock目标文本强制UTF-8长度≤255byte且无嵌入NUL，保留一byte终止符。当前12项最大46byte（open.002），其余最大41，全部通过；逐项报告保存在忽略目录`build/full-research/executable-text-audit/hud-capacity.json`。没有扩大buffer或更改机器字段。

## 测试

`python -m unittest discover -s tests -p test_executable_text.py -v`：6项通过，包括合成只读.rdata合法替换/正反回滚、slot溢出/重叠/源bytes/整文件身份拒绝、255/258-byte边界、实际12条提示以及本作实际runtime→空literal→逆literal→runtime回滚链。

本作实际EXE没有新增文字修改，运行时解码补丁仍是唯一EXE修改。所有结果属于静态分析和离线字节验证，不是游戏内测试。

## REA复核后的分类证据

|候选|静态调用关系|结论|Evidence|
|---|---|---|---|
|ACTION!|C0D40→11FAA0(2,literal)→1F4560|stdout/OutputDebugStringA日志，不是EA700玩家标签|ev_4955aa3fbee9e448229d3da08999074948f4bb9dedc23a6fae5a6b67ad125d9a|
|RESTART! / EXIT!|C4530输入处理→11FAA0(2,literal)，然后修改状态flag|日志；普通按钮图像来自button76.png，不改字面量|ev_6ea0687030eb71279a8e72378f819cc678ab82365d14958fbf315539977c9921|
|Album|D7840→124520(stringview("Album",5))|SetAchievement机器ID；124520失败日志明确提及ID|ev_9b89fd8c774f687e18efeb7dbf404591a29e0062e621f85643ecacd7e420f711|
|Impossibru|D7840异常状态→1226E0非返回错误函数|不改诊断消息|ev_9a86c5da829321ffe24d940028b11b314c8f30be8f50e92b1f000829daa3b1f1|
|日志sink|1F4560使用OutputDebugStringA、vsprintf、vfprintf、fflush；非fatal severity返回|与正常字体/菜单绘制独立|ev_160e032e34c579e52faf65aaaf47b06c4d2e2cdd426ddcc458ed29ee268f6941|

REA全定义字符串检索`Display Resolution|Anti.alias|Filters|Graphics Options|Resolution|ACTION!|RESTART!|EXIT!|Album|Impossibru`的证据为`ev_3a6ec2d7364c854cb7c9db84368c3e5b90a4b5da2efd8f3e6e6ec0022e6d2f80`；Resolution匹配内容确为默认TOML及JSON schema。完整结果与上述函数局部证据保存在忽略目录`build/full-research/executable-text-audit/`。
