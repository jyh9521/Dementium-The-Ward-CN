# 来源记录

技术上游：https://github.com/jyh9521/Dementium-II-CN

锁定提交：c0ea10f93450972841e510ff82913920339bd058。
上游提交作者/维护者署名：BLFY / jyh9521；MIT copyright 2026 jyh9521，许可全文保留于LICENSE。

复用范围：tools/zar.py中的digest、filehash、write_json、Entry、index_rows、Zar、make_delta、apply_delta，保留原函数源码；tests/test_zar.py选取fixture、ArchiveTests、DeltaTests，test_vfs_index.py只改模块导入。

本作独立新增：内层TAR适配、文本枚举与防御性回写、身份扫描/原包验证/恢复记录。没有复用上游翻译、完整游戏数据、字体、原生偏移、F1菜单或安装器。

上游的加载器、字体、游戏内截图及通关结论不作为本作已验证结论；本作独立验证依据见TECHNICAL.md与docs/VERIFICATION.md。

第二阶段补充：tools/font_source.py的font_metadata/discover/resolve_fonts逐函数复用同一上游提交，MIT归属保持。字体为TakWolf Fusion Pixel，SIL OFL1.1。PE映射/边界double回放参考上游tests/native_replay.py的方法，本作重写坐标、数据布局和整EXE身份守卫，不复用其补丁偏移。

全量阶段补充：tools/art_delta.py及tests/test_art_delta.py原样复用同一c0ea10f提交的MIT代码。tools/build_image_text.py适配上游tools/image_text.py的可见墨迹居中、字形覆盖、输入按键保护及区域外像素校验方法；本作伪PNG双LZ4和Image双zlib后端均独立验证。tools/executable_text.py的固定槽守卫参考同一作者Dementium-II-CN提交d3fbc4130bca6a1376e36f9f67b569b08d402680（MIT），去除debug_menu等无关分支。当前审计没有额外正常UI字面量需要改写，因此其recipe entries为空；不会为了复用而移植旧地址或开发菜单。

本作UTF-8/BMP解码补丁、binfont扩展、原生离线回放、媒体DAT同步和字幕构建由本项目针对本作实际身份/调用链实现。参考上游术语不等于继承其通关或游戏内验收结论。生成的源依赖美术差分包含修改信息，不提交整张原始/生成商业纹理。


调试菜单恢复补充：参考同一锁定c0ea10f提交中tools/debug_menu.py与tests/native_replay.py的F1内部键码、身份/容量守卫、文字池及已有DIR64重定位复用方法；本作tools/debug_menu.py、debug_menu_text.py、replay_debug_menu.py及binfont连接均按本作原生指令和字段独立实现，没有复制上游地址、ImGui接口、TTF字库或鼠标输入补丁。原生菜单与命令回调来自本作原EXE，源码仓库只提交工具、短标签译文及技术元数据。具体覆盖与边界见docs/DEBUG_MENU.md及docs/DEBUG_MENU_TEXT.md。


安装器补充：MaterialWindow.xaml/.xaml.cs、SteamLocator.cs、Directory.Build.props、app.manifest和包锁定配置改编自同一c0ea10f提交（MIT jyh9521），保留其Material Design 3主题、圆角卡片、按钮样式、动效、检测、日志与确认弹层。InstallerEngine.cs为适配本作完整双文件身份及流式copy/add载荷的新实现，事务/备份/恢复模式参考旧引擎；不复用其资源宽松识别。tools/source_delta.py及build_installer.py独立生成/校验本作载荷，未包含整原始游戏。installer/licenses保留MaterialDesign、XAML Behaviors与.NET运行时第三方许可。installer/branding两图来自用户本轮上传；图标仅为原PNG的ICO封装，顶图字节原样复制，不宣称另有字体或美术授权。
