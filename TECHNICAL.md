# 第一阶段技术调查（历史基线）

当前全量阶段进展见 [UTF-8适配](docs/UTF8_RUNTIME.md)、[binfont格式](docs/BINFONT_FORMAT.md)、[图片审计](docs/IMAGE_AUDIT.md)、[内层纹理](docs/INNER_TEXTURE_AUDIT.md)、[电影格式](docs/MOVIE_FORMAT.md)与[音轨审计](docs/MOVIE_AUDIO_AUDIT.md)。下文是第一阶段当时的事实与未确认项，保留历史，不作为最新状态。

日期：2026-10-23。对象为 Steam PC《病房》；静态/离线结果，不是游戏内结果。

## 已验证事实

1. 本机 appmanifest_3909960.acf：AppID3909960、build21501403；游戏目录有9个文件。清单只记录公开技术身份，不保存Steam账户字段。
2. `Dementium.exe`：4673536字节，PE32+ / Machine0x8664 (x64)，SHA-256 `26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`。REA open_binary 独立确认同一身份与架构，随后关闭；没有执行目标。
3. `rom.zar`：662255104字节，SHA-256 `9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c`；ZAR1、668成员、1MiB头。成员表无重复/越界/重叠，数据512对齐，未知字段均0。
4. `~INDEX`：602记录；601记录对应包内成员，一项 `/LICENSES.TXT` 对应安装目录112737字节文件。索引 flags=0，关联包内大小一致；并非每个ZAR成员都出现在VFS目录中。
5. `CONTENT.TAR`：73072640字节，原包偏移0x100000，SHA-256 `a13ad7b06b4f2f3148bea87de30f026c2c6d43edfe41a93c5b976bc103bc7a82`；TAR头校验通过，2555成员/2522文件/33目录。
6. 五种语言 `loc/{en,de,es,fr,it}/`，各131文本资源：8张TBL、123个 examine/item/open/unlock文档。每语言278非空记录。英语252个不同原文，130资源纯ASCII，credits中存在单字节重音名，不能直接全包按UTF-8读取。
7. 字体位于内层 `fonts/d2font_12x15.binfont`，7620字节，SHA-256 `a4d07a4bf8b64737baaeae243e7aa0fec6c16dedc3f18a4eb19ed0f9e6ead183`。EXE文件偏移0x3040c8有相同路径字面量。没有上游 JSON/PNG 字库接口。该路径证据仅证明常量存在，尚未追踪实际加载/绘制调用链。
8. 319个 `.PNG` 扩展名成员全部以 `7a00000020000000` 开头，**不是标准PNG签名**；没有将扩展名计作成功解码图片。FLAC177个有 `fLaC` 签名；IVF/OGG/DAT各34个，另有shader与INI/TOML。全部真实前16字节和哈希见清单。内层还含415个tex、92个art和场景/动画等二进制。
9. 完整原包无修改ZAR/TAR/text回写字节相同；一个ASCII记录变长后重提取、未改成员、控制码、顺序、差分双向校验全部通过。另用跨TAR块增长验证外层与VFS大小同步。
10. 恢复副本SHA与原包完全一致，Steam安装9文件复核一致，modified探针保留。未修改EXE。

## 高置信推断

- 可以复用《病房2》ZAR与VFS索引核心，但需要新的内层TAR适配。
- 单字节重音字节与西欧编码兼容；Latin-1可以无损形成调查视图。不能据此区分Latin-1/CP1252，更不能推出UTF-8中文可用。
- 内层二进制字体和非PNG纹理意味着旧JSON atlas生成器不能直接连接本作。

## 尚未确认

- binfont字段、glyph编码/索引、度量、位图编码与可扩展数量。
- 真正的文字解码、字宽/按钮复制容量、fallback、中文查字与换行机制。
- 外层自定义图片容器的压缩算法/宽高字段（某些头部值像尺寸，尚无解码证据）。
- 文字是否存在EXE硬编码、电影字幕或图像中；局部文本清单不是全可见文字覆盖证明。
- TAR启动加载、重定位后资源实际读取、存读档、裁剪和完整流程。所有原生偏移未迁移。

## New Game → 新游戏门槛

已确认源记录 `loc/en/UISSFrontend.tbl:0000`，成员大小361、字段8字节、TAR数据偏移72625664、原包绝对偏移73674240。UTF-8中文是9字节，但**不能以此认定本作支持UTF-8**。

资源定位和重建、身份守卫与恢复已经具备；中文编码和三个字形的构建/查字尚未具备验证依据。因此本阶段不生成中文探针。下一步是只读定位binfont loader和实际文本decoder，建立最小字形工具，再做仅一条译文的离线样本与用户手动游戏内验收。

## 证据入口

`assets/original-identity.json`、`assets/inspection/`为可提交的身份与结构元数据；完整原文/候选扫描/实验原包位于忽略的 `build/phase1/`。详见 `docs/FILE_FORMATS.md`、`docs/MIGRATION_ASSESSMENT.md`、`docs/VERIFICATION.md`。

## 独立 F1 恢复（离线候选）

原生入口、键码、action归一化和命令表已在本作重新定位；当前源码已增加独立 F1、保留原启用门禁的 L3+Y 与简中标签。具体补丁、身份/容量守卫、重定位、验证边界及手动验收见 [DEBUG_MENU.md](docs/DEBUG_MENU.md)。历史入口调查文档保留当时未启用的结论，不代表当前源码状态。
