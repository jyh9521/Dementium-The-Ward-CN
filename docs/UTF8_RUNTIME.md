# UTF-8 / BMP runtime adapter

日期：2026-10-23。对象限 Steam AppID3909960 / build21501403 / x64 EXE4673536字节，原SHA-256 `26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`。

## 已验证：本作独立坐标与调用链

REA从本作原EXE和phase2匹配分析快照恢复，未执行游戏进程。局部证据保存在忽略目录 `build/full-research/evidence/`。

|路径|已观察到的关系|Evidence|
|---|---|---|
|字节入口|RVA EA700，完整函数EA700–EA940共577字节；6参数，第5参数byte指针，第6参数byte长度/-1|ev_82c40e8fb278ed1ffc601f0237cc6c45cbad200665bdf15e3e9dc198bdade658|
|统一编译|EA950唯一已分析直接caller为EA700；读取ushort并编码为 `(codepoint<<8)\|7` 绘制指令|ev_df898e139d04bb64d6497bff89421dfc71d9744c9bbc1de967b5377ea2656573|
|物品|D28A0拼接loc/<语言>/item.*，读资源后传EA700，继而EADC0|ev_ca4867cc7a0a0b0b6c9b5ab7f0141335d137c8f9542fd7e1ba4253f96c812077|
|检查文档读取|BDCE0拼接loc/<语言>/examine.*，E9350读入对象+c0的vector|ev_1f233c3b578f0059fbeaf442f74b7ecf81c5a698cfb3f28777a4861823a5fbf9|
|检查文档显示|BE190把vector begin及end-begin的显式byte长度传EA700，再EADC0|ev_f0d97216dac5ff2c4ccdff51e23decf4d8b0d0b096e302a810bddd44fec4a226|
|制作人员|2F920读credits.tbl，两次EA700编译、EADC0绘制|ev_88aaf0b37a1bcc7aa791337dc9f6d6ed3f84c77e363eae65977995a581179072|
|测量|E9E10读取ushort并调用E9D30；查BMP高字节page、低字节slot|ev_ae836a94303b69ff1e25403202aa70070f215215ded8002e135d64ed219dd13c|
|绘制|EADC0按指令中16位码点查页/sprite，调用11FCF0，再按metric推进|ev_0f3591f049c558de865c6de2ad46b3fa6ec983a9f011c5a4ecb74cf04c148cd4|

EA700与EADC0的已分析直接caller集合相同（17项）：2F920、31BC0、B6A20、B7270、B76D0、B90D0、BE190、BF7A0、BFF60、C1CB0、C1FE0、C24E0、C72B0、CF880、D0BD0、D28A0、D5CB0。该静态集合不证明不存在未知间接调用或独立PC设置渲染器。

## 补丁设计与恢复

`tools/runtime_patch.py`不借用病房2偏移，只借其精确身份守卫、PE边界检查、稀疏差分与隔离指令回放方法。原函数文件偏移957184，整函数SHA-256 `47e570d74b334532fb420a77d4194975a877d8d0d507c3f40db4a3fbf41c0bdc`。`patch_bytes`检查整EXE大小/SHA、Machine8664、ImageBase、RVA↔offset映射、异常表函数边界；未知输入拒绝。

替换只在577字节内：保留前28字节prologue（保存非易失寄存器、分配原栈帧），保留EA8F5起原compiler call和epilogue。原Windows unwind元数据无需改动，PE sections、imports、relocations、文件长度不变；buffer LEA和compiler JMP采用PC相对寻址，合成ASLR重映射回放通过。

UTF-8解码支持ASCII、严格2/3-byte BMP；拒绝过长编码及surrogate。非法byte确定性替为ASCII `?`并消费1 byte，4-byte非BMP编码逐byte替换。NUL终止保留；显式长度以输入byte计，恰在多byte中途截断时不会越过byte边界读取。输出count是已解码ushort数量，所有原前4参数不变，原控制码单位不变。

复用原全局4096-ushort buffer `RVA D1BC40`，最多4095单位+NUL。运行时防御性截断；构建器必须调用`validate_text`，对超4095、NUL、surrogate、nonBMP明确拒绝，因此正常生成资源不依赖截断。原共享buffer的线程/重入属性不变。所有资源文本均应写UTF-8；保留的credits西欧姓名也必须从已确认的原单字节编码转UTF-8，不能保留Latin-1裸byte。

`patch_bytes`返回修改bytes与带before/after及输入输出SHA的recipe；`rollback_bytes`先核验修改SHA和expected bytes，恢复后核验原SHA。只在忽略目录写副本，不直接写安装目录。

## 自动化证据

运行 `python -m unittest discover -s tests -p test_runtime_patch.py -v`，5项通过。Unicorn映射真实原/补丁EXE字节，并不创建EXE进程。

- 原版UTF-8新游戏成为9个byte值；补丁后成为3个Unicode BMP单位。
- ASCII、中西文混合、1/2/3-byte边界、控制码、非法byte/overlong/surrogate/nonBMP、显式byte长度0–4、嵌入NUL。
- 4095汉字（12285 byte）完整通过，4096汉字防御性截断，构建validator拒绝4096。
- compiler入口全部6参数、Win64 call对齐、输出NUL、所有8个非易失整数寄存器、返回栈平衡通过。
- 把同一真实补丁映像改映射至0x150000000，PC相对解码/编译转交通过。
- 合成binfont包含“新游戏，”的真实BMP页；原advance和measure指令得到每字advance3+spacing1，总16；原draw dispatch得到sprite调用位置0/4/8/12并推进至16。仅sprite submission/end-batch作为边界桩，未把真实GPU加载宣称为验证成功。
- 原版/修改身份拒绝、精确回滚及函数外bytes完全不变通过。

## 剩余门槛与构建约束

- A94A0的open.*触发路径会把byte串复制到HUD字段1740/1840/1940等相邻256-byte区域。该路径静态证据 `ev_047120cee971102b5eabea42932402c690b789b4f3297d75b1afa5e8e0520b6a`。全量资源导入必须限制这些提示/关联字段的UTF-8 byte长度，或另行验证/补丁；4095-unit总体限制不替代每个UI固定byte槽限制。
- 原compiler按空格/换行分词，不会自动按每个汉字断词。译文应基于实测字距写入显式换行，避免无空格长句超过viewport。
- 字库扩图的双zlib frame展开尺寸应随RGBA尺寸增长；旧POC固定0x20000的解释已发现错误并单独修复。此前GPU边界桩不足以证明实际纹理加载，正式样本必须用修正后的binfont构建和加载尺寸校验。
- 真实画面、纹理上传、控制器、存档及完整流程保持待手动验收。没有启动游戏，没有修改Steam目录。

## 排版常量（真实调用点，而非屏幕像素验收）

- `BDCE0`设置examine区域：x=0、width=428；无图片 y=120、height=240；有图片 y=128、height=72。`BE190`传该width给compiler，用已编译行数×font+0x818计算显示y，有图倾向底部对齐，无图居中。未观察到该draw函数的滚动/分页；超高内容会把起始y挪出区域，应由构建期行数门禁拒绝，不依赖自动滚动。
- `31B97`把字体+0x818设为float13.0，原绘制器换行按此值推进。credits临时设16.0再恢复。字体字距+0x820由原font初始化决定，当前离线测量原值1.0。
- `D28A0`物品说明compiler width=280，draw x=74；item页面其余背景/图标占位仍需画面验收，不单由width推出垂直容量。
- `B90D0`交互按键提示compiler width=100、居中align=2、draw(x,y)=(214,220)。该路径与`BF7A0`三段HUD提示不同，后者每段width428、相隔一行font行距；不可把100误用为全部open/unlock正文宽度。
- `BE190`明确使用vector的byte长度；全量中文的预换行按Unicode字符/字体metric计算，再UTF-8编码，不能用byte数量当字符宽度。
## 全量locale回放接口

`tools/verify_locale_runtime.py::verify_locale_runtime(original_exe, patched_exe, original_font_bytes, full_font_bytes, records, runtime)`接受构建实际输出，先严格比对patched EXE与受守卫runtime patch期望产物，再把传入文件的完整PE映像映射到Unicorn。它对每个记录执行NUL与显式byte长度两种解码，逐行比较原E9E10可见glyph测宽与`locale_data.line_width`，并调用`replay_font.verify_loader`验证原/全量字库的页表、重定位、sprite矩形与bearing。

空格宽度按原E9980已观察初始化设置font+0x824=space glyph advance。换行先分行，颜色/控制码不作为可见glyph计宽，但资源与解码校验保留全部单位。原E9E10会给1..10的控制单位额外加spacing1，报告同时保留`raw_native_width`与`visible_native_width`差异，而不是静默把两者混为一谈。该差异对credits对齐仍需画面验收。原图像/GPU和sprite边界继续显式列为桩，不把字库loader回放等同GPU验收。

`python -m unittest discover -s tests -p test_verify_locale_runtime.py -v`：2项通过，覆盖跨BMP页、空格、CRLF、颜色控制码、原/新真实loader、输入身份与记录ID覆盖门禁。
