# 许可与来源

- 自编工具及复用的MIT工具按根目录LICENSE（Copyright 2026 jyh9521）分发。
- 原创译文按LICENSE-translations.md约定；原文/source字段保留用于版本绑定与校对，原版游戏文字不纳入本项目译文许可。
- 技术参考：jyh9521/Dementium-II-CN，锁定commit c0ea10f93450972841e510ff82913920339bd058；来源作者署名与逐函数复用见NOTICE.md及docs/MIGRATION_ASSESSMENT.md。
- 原始游戏EXE、归档、字体、纹理、音视频及其他商业素材属于原权利人，不随源码提交。结构化译文中的短source字段仅用于上下文校对和身份绑定，不改变原文权利归属；完整提取资源和完整原始清单只留本地。
- 字体使用本机已安装、SHA锁定的Fusion Pixel12px简中字库，TakWolf，版本2026.10.16，SIL OFL1.1；许可全文保留assets/fonts/Fusion-Pixel-OFL.txt。可复现生成所需字形、图片标签与字幕，不提交字体二进制或含原游戏字形的完整字库。
- build/、dist/、out/、work/为忽略目录，原件副本、完整文本清单与含整TAR的实验差分只能留本地。
- AGENTS.md与docs/LOCALIZATION_STANDARD.md为本地规范，Git忽略，不提交。


安装器界面沿用上述MIT上游，第三方依赖许可见installer/licenses；Windows x64自包含运行时及MaterialDesignThemes固定依赖打包在安装器内。两张branding图片由用户指定提供用于本安装器，未生成或重绘，不扩张其原有权利声明。源码仅跟踪用户指定branding、代码与元数据；dist和源依赖差分载荷仍在忽略目录，不提交整原件/生成游戏资源。

v1.1的稀疏电影中文字形沿用同一Fusion Pixel源字库；其完整OFL许可也嵌入安装器的installer/licenses/Fusion-Pixel-OFL.txt，与assets/fonts中的原许可一致。覆盖数据和改后EXE仅留build/dist，不跟踪完整原电影或完整原游戏程序。
