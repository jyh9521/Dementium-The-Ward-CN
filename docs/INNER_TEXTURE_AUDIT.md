# CONTENT.TAR 内层图片格式与可见文字审计

> 2026-10-23严格可读性复审优先：已撤回notepad、wboard02、code03三项重绘；当前23 inner + 3 outer美术差分。下文旧转录与计数保留研究历史，不代表当前可读性确认；详见[IMAGE_READABILITY_REVIEW.md](IMAGE_READABILITY_REVIEW.md)。

## 已验证范围

只读扫描本机 build21501403 的415个`.tex`和92个`.art`，共507个成员。工具`tools/engine_image.py`成功解码504个：全部415个`.tex`和89个`.art`。生成14张接触表并全部查看，重要文字候选另打开原尺寸PNG查看。预览、中间图像与接触表仅在Git忽略的`build/full-research/inner-textures/`。清单`locales/zh-CN/inner-image-inventory.json`只包含资源名、尺寸、哈希、头部字段和视觉分类，不含商业图像二进制。

最初调查只读。随后26项可读场景文字已生成源依赖差分并在build副本重建；原Steam安装目录仍只读，游戏未启动。另三个fmt5/8的基础层已由独立适配器与真实原生转换loop逐像素交叉验证，合计507/507基础图像可见审计；不是三个未知文件按名字猜无字。详见INNER_IMAGE_EXTRA.md。

## 已验证格式

`.tex`先有4字节不透明flags；`.art`没有这4字节。之后共同结构：

| 相对offset | 结构 | 观测含义 |
|---|---|---|
|0|`<6H2I>`，20字节|pixel_format、mip_count、可见宽/高、分配宽/高、未解释字段、总分配像素数|
|20|u32|全部mipmap层的原始像素字节长度；不是固定magic|
|24|三u32+zlib|外层frame：解开长度、压缩长度、含12字节头和0至3零对齐字节的总长|
|外层解开后|同样frame|第二层zlib解开得到所有mipmap像素|

已支持pixel_format0=RGBA8（每像素4字节）、1=RGB8（每像素3字节）。每级分配宽高均按右移级数并下限1计算；总字节长是各级分配像素之和乘bpp。显示预览用可见宽高裁切，每行stride依据分配宽，而不是可见宽。

`3d/tex/acunit01.tex`有4层，256×128起始，raw_size174080，说明不能把字库原图的0x20000误认成所有图片共有常量。

`art/menu/UIMSInGame_PlayerHud_gritlayer.art`可见108×64，分配128×64，raw_size32768；按分配stride读取即可解码为无正文的HUD遮罩。分配尺寸不是可见尺寸的重复字段。

工具验证两个有界zlib流、声明长度、EOF、流尾、零对齐和文件末尾，拒绝多余流或未解释尾部。`rebuild()`及`write(original_pixels)`保持原压缩字节；`write(changed_all_mips)`仅接受完整原尺寸mipmap像素，保留prefix/header全部元数据并重新压缩和计算frame长度。本轮合成测试覆盖修改回写，真实资源只做无修改读取/重建。

## 三个由独立只读适配器补充的格式

|资源|头部format|原始长度|状态|
|---|---:|---:|---|
|`art/flares.art`|5|8192|128×32，LA8，四个光环/光斑，无字|
|`art/sunglow.art`|5|2048|32×32，LA8，径向亮度渐变，无字|
|`art/splat01.art`|8|5440|64×64基础层L=A8飞溅，无字；1344字节尾部保留|

没有把长度当格式结论：原F9340内部fmt5/8两条转换loop已在Unicorn执行并与适配器全部基础像素一致；三图均已实际查看。splat01尾部32²/16²/8²诊断视图亦为缩小飞溅，但最末64字节未计入headercount的原因尚未确认，不给它伪造正式mipmap字段语义。三个文件只读/no-op原字节相同，不提供未知结构回写。

## 278条之外的确切玩家文字

以下在原尺寸图片中确认，不在现有表格/文档278条内；因此现有278条覆盖率不能用作全游戏总覆盖率。

|资源basename|确认字样/类型|处置|
|---|---|---|
|`alert01.tex`|ALERT|可本地化警报牌|
|`code02.tex`|DEAD|可能是字母谜题答案；在输入链路确认前保留Latin解谜答案|
|`code03.tex`|IF YOU DARE!|可本地化挑衅文字；不改变配套密码|
|`exit01a.tex`|EXIT|出口标识|
|`graf01.tex`|KILLER/murder/DIE/Daddy/Amanda/Justice|儿童涂鸦，剧情词需翻译，Amanda保持阿曼达|
|`mirror03.tex`|MURDERER|剧情镜面文字|
|`notepad.tex`|WHY DID YOU DO IT?|和examine.008首句提示一致|
|`poster01.tex`|YOU ARE SPECIAL!!!|墙上海报|
|`poster02.tex`|KIDS ARE LIKE SUNSHINE!|墙上海报|
|`sign01.tex`|PHARMACY|药房导向牌|
|`sign04.tex`|EXAMINATION ROOM/LINEN/STAIRS/MAINTENANCE/STAFF ONLY BEYOND THIS POINT|检查室/布草间/楼梯/维修区/员工限制文字|
|`sign05.tex`|SECURITY/AUTHORIZED PERSONNEL ONLY/PATIENT WARD/LOUNGE|安保区/仅限授权人员/病房/休息室|
|`sign06.tex`|ROOF ACCESS、7W至2W、右侧竖排ROOF|通往屋顶/西楼楼层ID/屋顶；已放大复核，不是MORGUE，保留左箭头|
|`sign07.tex`|ROOF ACCESS、7E至2E、右侧竖排MORGUE|东楼对应牌；已放大复核，与sign06竖排词不同；保留右箭头，E/W不能删除|
|`sign08.tex`|Pat’s Pantry/Suzy’s Apparels/Duencil DRUG|商店名/商品招牌，专名拼写需保持或统一音译|
|`sign09.tex`|CAFETERIA/1E/1W/EMERGENCY/SURGERY/BASEMENT|食堂/楼层ID/急诊/手术室/地下室|
|`wboard01.tex`|顶部灰字EVERYONE SHOULD；左上红色两行NIGHT SHIFT / SCHEDULE；右上蓝字SMILE!；姓名与班表|已放大分别核对三个标签的原文；顶部不是NIGHT SHIFT。三个标签译大家都该/夜班排班表/微笑！，姓名、排班简称和涂写原样保留，不猜完整转录|
|`wboard02.tex`|同白板血迹覆盖版本，配套三个语言标签|原血迹遮挡源RGBA逐像素恢复并保护；被遮文字不补画成清晰新信息，未改姓名/班表/涂写|

还有包装/品牌/小字候选32项，见清单`small-print-or-brand-text`分类，包括bulletin01..03、paper001/002、notes01、clipbrd、药盒、医疗用品纸箱、报警器和自动售货机。部分字迹仅作装饰或低清不可读，未将这些候选擅自写成确定台词。

字母积木、字母盒、数字密码、电梯和密码键盘、照片数字10/31/07列为保护类；视力表和Rx/医疗符号不能机械翻译成汉字以免改变图案语义。

## 本地离线音频工具核验

- `ffmpeg -version`：9.0.2-full_build，实际可执行，包含常见音视频解码器。
- `faster_whisper`实际导入成功，版本1.2.1；torch2.14.0+cpu，CUDA=False。
- 本地HuggingFace缓存存在Systran faster-whisper small/medium/large-v3完整snapshot及model.bin：small snapshot `536b0662742c02347bc0e980a01041f333bce120`，medium `08e178d48790749d25932bbc082711ddcfdfbc4f`，large-v3 `edaa852ec7e145841d8ffdb056a99866b5f0a478`。
- 后续离线转写必须使用本地snapshot路径和`local_files_only=True`，CPU int8；本轮环境核验没有下载模型，没有向外部服务发送游戏音频。

## 复现与验证

```powershell
python -X utf8 tools/engine_image.py --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --out build/full-research/inner-textures --inventory locales/zh-CN/inner-image-inventory.json
python -X utf8 -m unittest discover -s tests -p test_engine_image.py -v
```

结果：`INNER IMAGES {'decoded': 504, 'unsupported': 3} total 507 contact-sheets 14`；11项合成测试通过。离线首级预览不等于完整材质渲染、游戏内可读性或场景通过验收。
