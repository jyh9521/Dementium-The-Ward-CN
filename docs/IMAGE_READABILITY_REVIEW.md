# 图片原文可读性复审（2026-10-23）

> 2026-10-24 更新：用户提供游戏内清晰截图并指定将 IF YOU DARE! 改为“有胆你就来！”。本轮仅解除 code03 的历史保留项，并新增 soda01“汽水／泡泡”两面美术差分；notepad、wboard02 继续整资源保留。当前美术差分为28张（25 inner +3 outer）。下文为2026-10-23复审记录，code03的旧处置已由本次明确反馈取代。见 [四处发布修正](RELEASE_FOUR_FIXES.md)。

## 结论与证据等级

本次采用用户要求的严格标准：只凭该张原图能独立清楚辨读的文字汉化；关联文档、同型清晰材质或上下文不能替代该图像的文字证据。查看原像素与最近邻放大只用于审阅，不使用生成式超分辨认字。

**确认存在应撤回的推补式重绘，共3张。** 旧版notepad把关联examine文字当作微缩封面译文；血迹白板借用了清晰版信息；破损红色笔迹的旧完整转录也不满足本次严格标准。这不是“原图可读已验证”。现已移出构建并删除活跃delta；历史研究仍由Git历史保留。

|撤回资源|旧中文/旧转录来源|本次处置|
|---|---|---|
|`3d/tex/notepad.tex`|旧中文“你为什么／要这么做？”来自关联examine文档；32×32封面本身不足逐字支持|原压缩资源及全部mipmap逐字节保留；关联文档正文不改|
|`3d/tex/wboard02.tex`|原血迹遮挡使三条完整标签缺乏独立证据；旧版借清晰wboard01重绘|整张原图保留，不补清血迹下文字|
|`3d/tex/code03.tex`|旧文档称“IF YOU DARE!”；破损红色涂写不足明确完整辨读|撤销确定转录；整张原图及alpha保留|

## 保留的26张美术差分

以下为逐张查看原图及旧中文差分后的保留项；这里的“已验证”仅表示源文字可读和离线像素守卫，不表示游戏内观感或UV验收。

|资源|可读源文字／范围|证据等级|
|---|---|---|
|`TEXTURES/MAP/BG.PNG`|Redmoor Hospital|已验证：该图源字可读|
|`TEXTURES/HUD/THATWASYOURLASTBREATH.PNG`|THAT WAS YOUR LAST BREATH|已验证：该图源字可读|
|`TEXTURES/HUD/THATWASYOURLASTBREATH2.PNG`|THAT WAS YOUR LAST BREATH|已验证：该图源字可读|
|`3d/tex/sign04.tex`|EXAMINATION ROOM / LINEN / STAIRS / MAINTENANCE / STAFF ONLY BEYOND THIS POINT|已验证：该图源字可读|
|`3d/tex/sign05.tex`|SECURITY / AUTHORIZED PERSONNEL ONLY / PATIENT WARD / LOUNGE|已验证：该图源字可读|
|`3d/tex/sign09.tex`|CAFETERIA / EMERGENCY / SURGERY / BASEMENT|已验证：该图源字可读|
|`3d/tex/sign01.tex`|PHARMACY|已验证：该图源字可读|
|`3d/tex/sign06.tex`|ROOF ACCESS / ROOF|已验证：该图源字可读|
|`3d/tex/sign07.tex`|ROOF ACCESS / MORGUE|已验证：该图源字可读|
|`3d/tex/mirror03.tex`|MURDERER|已验证：该图源字可读|
|`3d/tex/alert01.tex`|ALERT|已验证：该图源字可读|
|`3d/tex/poster01.tex`|YOU ARE SPECIAL!!!|已验证：该图源字可读|
|`3d/tex/poster02.tex`|KIDS ARE LIKE SUNSHINE!|已验证：该图源字可读|
|`3d/tex/exit01a.tex`|EXIT|已验证：该图源字可读|
|`3d/tex/graf01.tex`|KILLER / murder / DIE / Daddy / Amanda / Justice|已验证：该图源字可读|
|`3d/tex/sign08.tex`|Pat’s Pantry / Suzy’s Apparels / Duencil DRUG|已验证：该图源字可读|
|`3d/tex/wboard01.tex`|EVERYONE SHOULD / NIGHT SHIFT SCHEDULE / SMILE!（仅清晰版；其余姓名班表与涂写保留）|已验证：该图源字可读|
|`3d/tex/boxes01.tex`|MEDICAL SUPPLIES（其他日文不补译）|已验证：该图源字可读|
|`3d/tex/boxes01b.tex`|MEDICAL SUPPLIES（血迹原像素保留）|已验证：该图源字可读|
|`3d/tex/ammo_snp.tex`|RIFLE|已验证：该图源字可读|
|`3d/tex/falarm2.tex`|FIRE（下方微字保留）|已验证：该图源字可读|
|`3d/tex/boxes02.tex`|FRAGILE（品牌、符号与日文保留）|已验证：该图源字可读|
|`3d/tex/boxes02b.tex`|FRAGILE（血迹原像素保留）|已验证：该图源字可读|
|`3d/tex/vend01.tex`|SNACKS!|已验证：该图源字可读|
|`3d/tex/vend01a.tex`|SNACKS! / PUSH（商品袋微字保留）|已验证：该图源字可读|
|`3d/tex/vend03.tex`|COOL|已验证：该图源字可读|

## UI、微字与影片范围

- 49张程序化UI图片原图重新解码并查看：16张返回／确定等图例、18张章节图、11张键盘手柄说明、4张Y轴图例。所有对应源标签可读，保留汉化；按键图标与绑定不改。
- 原先保留的低清EXAMINE008/009/046、药盒、纸张、布告栏等继续保持原图；没有把关联文本回填到这些图片。32项小字原审计见SMALL_PRINT_AUDIT.md；本次三项撤回优先于历史汇总中的26 inner / 29 total计数。
- 影片章名字卡的英文可读；电影画面词采用顶部译注而非透视图内修补。已复核新闻画面、EXIT及检查室门牌原帧接触表，维持现有9条短画面词译注；字幕／语音转写是另一路数据，不冒充图片原文。
- 未运行游戏；本次实际输入为`build/debug-menu/rollback-sample/rom.zar`，SHA-256 `9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c`。

## 可复现守卫与离线回归

`art-patches.json`现在有26个patch（23 inner + 3 outer）与3个`preserve_source`条目。build_art会校验三张原资源SHA、拒绝patch与保留清单冲突，报告原资源逐字节保留；三个撤回的活跃delta文件已删除。测试同时锁住这三个资源不再进入汉化。

命令：`python -X utf8 -m unittest discover -s tests -p test_build_art.py -q`。字面结果：`Ran 15 tests in 0.048s`、`OK`，退出0。

命令：`python -X utf8 tools/verify_art_readability.py --archive build/debug-menu/rollback-sample/rom.zar`。真实原包两次build_art构建一致，并在重建CONTENT.TAR后再次比对撤回三项原资源，结果：`IMAGE READABILITY PASS retained=26 withdrawn=3 repeated=identical preserved-after-tar=byte-identical no-game-launch`，退出0。报告：`build/image-readability/art-review-verification.json`。

审阅用本地证据（Git忽略）：`build/image-readability/contact-0..4.png`为29张原图／旧改图；`ui-source-0..4.png`为49张UI原图；`*-source.png`保存本次从身份锁定原包解出的原尺寸审阅图。完整构建／恢复证据由本轮安装器构建记录另行保存。
