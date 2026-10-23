# 门牌、框内居中与死亡提示返工

## 原因与证据

**已验证**：sign06右侧ROOF、sign07右侧MORGUE在原atlas中是整个横排词逆时针旋转90度，不是逐字直排。旧中文直排造成用户截图中的屋顶字样转歪；现在将横排美术按原方向装入。sign05旧安保标题还伸入了原授权说明区域，截图确有标题下半部分混入授权牌。本次拆开两个文字区域，未改变场景/UV/资源尺寸。顺时针解包预览是离线采样，不是实际GPU验证。

**已验证**：可见7W/7E等牌面被误归为保留ID。本次补齐西1楼—西7楼、东1楼—东7楼共14项，数字和对应关系、箭头不变，内部关卡标识不修改。

## 43处框内定位

旧导入把裁剪矩形居中，不保证文字墨迹居中。`locales/zh-CN/art-alignment.json`现在记录源框体/文字槽、墨迹搜索区域、颜色分类和可编辑区域。`tools/center_artwork.py`在作者阶段搬移既有美术字的像素，按真实墨迹边界重新定位，排除孤立材质噪点；旧位置使用已审阅的原风格材质修复板，不使用纯色盖底或新点阵字体。

覆盖sign01、sign04—09及警报、出口、镜面字、火警、清凉、步枪、清洁/血迹易碎贴纸。带箭头的顶部牌以保留箭头后的文字槽定位；安保/授权文字分别定位；斜贴纸保持倾角，血迹版恢复全部原血迹保护像素。

每条delta保存源墨迹框、最终墨迹框、框体和中心差。原生整数像素网格的水平/垂直差均不超过0.5px（宽高奇偶不同时的最小差）；不声称所有缩放下视觉完全相同。构建器重算中心差并核对实际框内像素指纹，偏心/像素漂移停止构建。边框、螺钉、箭头、人物符号和编辑区外像素继续受守卫保护。

海报弧形字、涂鸦和无独立框的包装字保留原构图，不强行移到整图中央。49张程序化UI继续通过已有墨迹中心/输入符号保护及纵轴原生坐标回归。

## 死亡提示共用母稿

上行改为“你已咽下”，下行为“最后一口气”。只生成一次母稿，第二状态由`tools/paired_artwork.py`派生，文字/装饰/尺寸/坐标完全共用，不独立重绘。

原版双图实际差异框为`[93,109,334,138]`，仅位于LAST BREATH区域。原版中性亮字样本测得RGB倍率约`0.9380278824 / 0.7742192762 / 0.7968161895`，仅作用于母稿的象牙白反射层，不将旧英文形状差场叠入中文。构建器从第一状态重算第二状态并逐像素校验。上方红字、装饰和背景几何共用。

## 不明原文硬保护

箱子原生日文/拟日文小字缺乏完整逐字转录证据。生成式放大会重构笔画，不能作为原文可读证据，不据此猜译。

- boxes01/boxes01b：原生`[0,0,64,32]`。
- boxes02/boxes02b：原生`[0,0,128,32]`。

这些区域明确加入delta的`protected_regions`，构建和TAR重建后核对原像素相同。只导入已确认文字附近的材质修复，不导入生成图重构的小字。notepad、code03、血迹wboard02整资源撤回规则保持。

## 破折号

遍历locale根目录全部JSON显示target，两处双破折号分别在病历和影片字幕，均改为` - `，包括句末字幕的末尾空格。source、资源ID、控制码不改；文档译文指纹只更新此次明确授权的标点。回归拒绝显示target重新出现U+2014。

## 复现与验收

正常构建仅需原版、locale差分和既有依赖，不依赖生成服务、旧导入PNG或修复板。可选导入工具只供作者使用。完整原/改游戏资源和审阅图都留在Git忽略的build目录。

```powershell
$game = "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward"
python -X utf8 -m unittest discover -s tests -q
python -X utf8 tools/record_locale_verification.py --game "$game" --output build/framed-artwork-release
python -X utf8 tools/verify_sign_feedback.py --game "$game" --build build/framed-artwork-release
python -X utf8 tools/verify_sample.py --output build/framed-artwork-release
& "C:/Program Files/Git/bin/bash.exe" ./build/framed-artwork-release/ROLLBACK.sh
```

美术返工阶段未启动游戏或更新安装器；用户约20分钟简测后，已按其要求另行生成v1.0安装包，见INSTALLER_VERIFICATION.md。新待测副本为build/framed-artwork-release/sample。原生指令、像素、重复构建与隔离恢复不等于场景/GPU验收；用户退出旧进程后，用新副本检查屋顶、东西楼1—7楼、其他框内文字、死亡双状态、字幕与病历标点。
