# 四处发布修正（2026-10-24，版本仍为1.0）

## 唯一游戏内容改动

1. `movie-titles.json`：CHAPTER15副标题由“初次交锋”改为“初次相遇”，章节编号、装饰、时间与渐隐配方不变。
2. `3d/tex/exit01a.tex`：清除原背景/旧字残迹，只保留白底绿色“出口”；32×16尺寸不变。
3. `3d/tex/code03.tex`：按用户游戏内截图及补充要求绘制“有胆你就来！”，保留红色不规则手写涂鸦风格与透明背景。全角感叹号已纳入母稿。历史“不可独立辨读”判断仅对旧低分辨率调查成立，本轮使用用户明确指定的截图/译文，不借关联文档补写。
4. `3d/tex/soda01.tex`：正面、侧面均将SODA替换为“汽水”、POPP替换为“泡泡”，保持红/青色、斜排描边与做旧风格。

美术使用内置image_gen制作、离线裁切/缩放导入；正式构建只读取原图SHA绑定的RGBA XOR差分，不依赖生成服务或本地生成图片。具体提示词、母稿SHA、导入尺寸与区域保存在三个art JSON的prompt/import_recipe字段。code03允许仅该贴图透明通道更新；exit/soda保留源alpha。所有mipmap通过既有守卫重建。

## 已验证

- 与上一已试玩 `build/framed-artwork-release` 比较：仅上述三项内层贴图变化，其他2552内层成员逐字节相同；全部外层原视频/索引/音轨保持原字节。
- 24段稀疏电影覆盖输出仅CHAPTER15变化；移除电影覆盖层后两份EXE逐字节相同。正文、字幕、字体、输入、选项、其他美术与运行时代码不变。
- 完整构建重复两次一致；基线、修改、额外副本恢复命令均退出0；修改产物及sample保留。
- Python271项通过。原测试含5个硬编码Steam EXE引用；本机已装旧汉化，直接跑原命令曾出现8项原版身份错误。本轮测试通过 `build/release-four-fixes/run_tests.py` 在内存中把这5个路径重定向至完整SHA核验的原件副本，测试代码本身未绕过身份守卫，全部271项执行通过。
- 最终EXE的场内字幕回归24例、2基址通过；原门牌/字框/死亡双状态/受保护小字回归通过。
- 安装器C#59项通过，实际嵌入新载荷在额外副本完成安装、重复安装和恢复，原两文件完整SHA恢复；存档/配置不动。
- 两次source-copy/add流相同，两次发布EXE相同。三种尺寸/缩放预览与上一1.0安装器PNG字节相同，图标、顶图、界面代码未变。
- 自动化未启动游戏；本轮纹理的实际游戏内显示由用户验收。

## 交付身份

- 文件：`dist/Dementium-The-Ward-zh-CN-v1.0-Setup.exe`
- 字节：78497853
- SHA256：`5bd98a3d21403bada448ef154fcda22914f12b98cb9294b802d8d4aa5c505939`
- 产品/界面版本1.0，PE版本1.0.0.0。
- `dist/Dementium-The-Ward-zh-CN-Setup.exe`为相同字节副本。
- 玩家只需新安装器，不需要Python或独立.NET运行时。
- 安装器只接受原版或本次改件。已经安装上一同名1.0者，先用旧安装器恢复原版，再运行新安装器；供本机恢复的旧文件保留在 `build/release-four-fixes/previous-installer/Dementium-The-Ward-zh-CN-v1.0-Setup.exe`，SHA为`beea24d0709979ce4ebf74595f0f518a8db67e495945b585cfb36030e87dedce`。

## 重建与证据

本轮原版输入为 `build/release-four-fixes/original-input`，从现有原版备份复制全部9文件并完整校验assets/original-identity.json；不向Steam目录写入。其他机器可提供同身份的干净原版目录。

```powershell
python -X utf8 tools/record_locale_verification.py --game build/release-four-fixes/original-input --output build/four-fixes-release
python -X utf8 tools/verify_ui_feedback.py --game build/release-four-fixes/original-input --build build/four-fixes-release
python -X utf8 tools/build_installer.py --game build/release-four-fixes/original-input --build build/four-fixes-release --dotnet C:/path/to/dotnet.exe --output dist/Dementium-The-Ward-zh-CN-v1.0-Setup.exe
```

本地完整字面命令、输入、输出和退出码：`build/four-fixes-release/VERIFICATION.txt`、`build/installer/VERIFICATION.txt`。严格范围对比：`build/four-fixes-release/four-fixes-scope.json`。四交付证据文件为build/installer下MODIFIED_FILE.exe、DIFF_FILE.json、VERIFICATION.txt与可执行ROLLBACK.sh；恢复脚本只操作额外rollback-sample，不覆盖改件。正式安装后的恢复使用安装器“恢复原版”。
