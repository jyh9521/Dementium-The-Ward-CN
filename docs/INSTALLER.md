# 汉化补丁安装器 v1.1.1

## 用户操作

文件：`dist/Dementium-The-Ward-zh-CN-Setup.exe`。Windows x64 自包含程序，不需要另装 Python 或 .NET。界面沿用《病房2》Material Design 3 的卡片、紫色按钮、动效、操作日志与确认弹层；图标为用户图1，顶图为图2，均未生成或重绘。

1. 先退出游戏；自行备份重要存档。本安装器不访问存档或设置。若已安装旧v1.1，请先使用原安装器检查并恢复原版，再运行本版；保留旧安装器位于build/ui-feedback-release/baseline/Dementium-The-Ward-zh-CN-Setup.exe，不直接覆盖旧版改件。可优先对另建的原版完整副本安装测试。
2. 打开安装器，点击“自动检测”，或“浏览…”选择游戏根目录的 `rom.zar`。
3. 点击“检查资源”。只有 `rom.zar` 与同目录 `Dementium.exe` 都通过受支持完整大小/SHA校验后，安装/恢复按钮才可用。当前仅支持 Steam AppID3909960 / build21501403 原版，或本安装器生成的已安装状态；未知版本、其他模组和混合状态不会直接覆盖。
4. 点击“安装汉化”并确认。安装器先校验、备份至同目录 `cn-backup`、生成并核对两份临时结果，再提交；安装器不启动游戏。
5. 后续恢复时，重新选择同一个 `rom.zar`，检查资源后点击“恢复原版”。恢复校验通过后只清理安装器已知且身份正确的备份；备份目录中的未知用户文件保留。
6. 存放在受保护目录而无写权限时，安装器会询问是否以管理员身份重新打开，拒绝不会继续写入。建议至少留出约2GB空闲空间，实际门禁按源/目标大小计算。

两个文件必须成套。不要删除、篡改或混用 `cn-backup`。若检测到未知版本、缺失/损坏备份或中断事务锁，查看日志并保留现场，不手动把别的游戏版本当作恢复源。

当前交付未在Steam安装目录执行安装；真实安装/还原由用户选择后执行。开发验证只处理额外副本。程序界面预览不是游戏截图，游戏画面、F1/手柄、字幕和流程仍需人工验收。

## 本轮内容

- v1.1.1修复广播叠字/重复、显示模式英文及调试菜单列重叠，详见[UI_FEEDBACK_FIXES.md](UI_FEEDBACK_FIXES.md)。原声音/触发、原视频路线和安装器UI不变。

- 新增原视频保留路线：102个电影成员逐字节不变，运行时稀疏覆盖保留对白、画面译注、章节标题及渐隐。安装器UI/图标/顶图不变，仅更新版本与载荷。见[MOVIE_OVERLAY.md](MOVIE_OVERLAY.md)。

- 31条无内部标点的单句物品/交互说明仅移除末尾句号；文档、信件、谜题和对白保持原样。
- 撤回记事本、血迹白板、破损红字三张推补式重绘，完整保留原资源及mipmap；只保留原图独立可读文字的图片汉化。
- 保留独立F1和原手柄秘密序列启用后的L3+Y原生调试菜单。
- 可手动测试的修正副本位于 `build/ui-feedback-release/sample`。旧 `build/full`、`build/debug-menu` 是历史候选，不用于本轮文案/图片修正验收。

相关审计：[句末规范](PUNCTUATION_STYLE.md) · [图片复审](IMAGE_READABILITY_REVIEW.md) · [F1与手柄](DEBUG_MENU.md)。

## 构建与载荷

先按 [BUILDING.md](../BUILDING.md) 从用户自己的原版完成整包基线、两次修改构建和隔离恢复，再运行：

```powershell
python -X utf8 tools/build_installer.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward" --build build/ui-feedback-release --dotnet "C:/path/to/dotnet.exe"
```

需要.NET 10 SDK而不是仅runtime；本轮SDK10.0.402，MaterialDesignThemes5.3.2通过包锁定配置恢复。SDK路径可显式指定或通过DOTNET_EXE提供；不依赖旧项目中间产物。

源码不包含完整游戏EXE、ZAR、字库或媒体。安装器嵌入小型JSON清单和两个gzip二进制source-copy/add流，不嵌入整原版。COPY从用户自己的身份锁定源文件复制，ADD仅携带无法从源复用的修改字节。512-byte块索引只影响压缩效果，不改变结果的大小/SHA校验。

流头为8 bytes `LOCDLT1\0`；命令1为 `<u64 source_offset, u64 length>`，命令2为 `<u32 length, bytes>`，命令0结束并要求EOF。小端、严格边界；原件与输出均完整SHA-256核验，不能对未知原件盲打固定偏移。

每个流重复生成两次并比较；Python重新执行流核对完整目标；安装器也发布两次比较。真实嵌入资源再通过C#引擎在额外原件副本执行检查→安装→重复安装→恢复→原SHA复核；合成测试另外覆盖提交中断、坏载荷/坏备份、路径逃逸、硬链接/目录联接和未知文件保留。具体本轮数量和字面输出见生成的 `build/installer/build-report.json`、`build-commands.json` 及最终验证记录。

图1原PNG保存为 `installer/branding/icon-source.png`，ICO直接封装其原始PNG字节；图2保存为 `installer/branding/logo.png`，与附件逐字节一致。来源摘要在 `installer/branding-inputs.json`，许可来源在 [NOTICE.md](../NOTICE.md)、[LICENSING.md](../LICENSING.md) 和 `installer/licenses`。

本轮命令、字面输出、四产物路径、安装器SHA和恢复状态见[INSTALLER_VERIFICATION.md](INSTALLER_VERIFICATION.md)。
