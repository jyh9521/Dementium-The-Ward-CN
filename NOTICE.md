# 来源记录

技术上游：https://github.com/jyh9521/Dementium-II-CN

锁定提交：c0ea10f93450972841e510ff82913920339bd058。
上游提交作者/维护者署名：BLFY / jyh9521；MIT copyright 2026 jyh9521，许可全文保留于LICENSE。

复用范围：tools/zar.py中的digest、filehash、write_json、Entry、index_rows、Zar、make_delta、apply_delta，保留原函数源码；tests/test_zar.py选取fixture、ArchiveTests、DeltaTests，test_vfs_index.py只改模块导入。

本作独立新增：内层TAR适配、文本枚举与防御性回写、身份扫描/原包验证/恢复记录。没有复用上游翻译、完整游戏数据、字体、原生偏移、F1菜单或安装器。

上游的加载器、字体、游戏内截图及通关结论不作为本作已验证结论；本作独立验证依据见TECHNICAL.md与docs/VERIFICATION.md。

第二阶段补充：tools/font_source.py的font_metadata/discover/resolve_fonts逐函数复用同一上游提交，MIT归属保持。字体为TakWolf Fusion Pixel，SIL OFL1.1。PE映射/边界double回放参考上游tests/native_replay.py的方法，本作重写坐标、数据布局和整EXE身份守卫，不复用其补丁偏移。
