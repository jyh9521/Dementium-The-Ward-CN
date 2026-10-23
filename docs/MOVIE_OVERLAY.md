# 原视频保留与逐帧中文覆盖层

## 已实现的构建路径

当前完整构建不再调用电影重编码器。`movie_layers.py` 从 SHA 锁定的原始电影离线解码，复用原译文/时轴及 `rewrite_titles` 的审定遮盖、中文标题、源渐隐和红饰保护规则。输出仅含中文覆盖所需的稀疏 RGB 像素：18 条对白、9 条画面译注、18 段章名（16 段独立、2 段内嵌）。

`movie_overlay.py` 在本作原生上传调用 RVA `BDBCA` 增加可恢复的 CALL 包装器：复制本帧原生 BGRA 到专用暂存区，写入稀疏中文层，仍调用原 `105D30` 上传。**全部 34 组 IVF/DAT/OGG、共 102 个成员保持逐字节原样**；没有更换码率、重编码视频、修改帧数、DAT 索引或原音。场内语音字幕使用原来的独立 PCM 路线，保持不变。

这是运行时解码图像覆盖，不是把新视频塞入补丁，也不是新增独立视频播放器。显示沿用原电影贴图的缩放、位置、渐隐与影院叠层，所以无需给影院文字队列另加状态切换。中文字体及原始译文未删减。

## 已验证的本作原生合同

仅支持原 EXE SHA256 `26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`。本作地址均独立验证，不取自病房2。

- 包装器读取 `C15A90` 的实际 Mux streamer，校验 vtable `314F68`，读取其 `+8150` VPX 子对象并校验 vtable `3150E8`。
- VPX `+81D0/+81E0/+81E8` 是实际打开的 DAT 路径、长度与容量，按 MSVC SSO 合同有界读取，匹配不区分 ASCII 大小写的 DAT 文件名。不用 `BD140` 新请求名称绑定旧媒体时钟。
- `103330` 把选定解码帧 `+70` 时间复制到描述符 `+50`（全局 `C15AF0`）。`BDA50` 选帧完成后才调用上传。包装器从该时间减去 VPX `+40` 循环/播放偏移，匹配原始 IVF 帧中心的半帧区间；不使用系统时间，也不把帧阈值 `378208` 当字幕时钟。
- 仅接受原 400×240、1600-byte stride、VPX `+8190` 非平面模式。该字段只比较 byte；`+8191` 归属及后续 padding 不影响覆盖。
- 独立执行原转换函数 `1C8D80` 的红/蓝/中性 YUV 哨兵，确认内存顺序 BGRA；层数据 RGB 转 BGR 写入，原 alpha 原样保留。完整帧复制保证非覆盖区采用游戏自身解码像素，而非 FFmpeg 重绘的背景。
- 标题遮盖包含全部审定 `erase_runs`，即使离线样本该像素已是黑色，避免两种转换器的微小差异留下英文边缘。字幕覆盖全部非零 alpha 像素。标题后续剧情的 `unchanged` 帧不施加遮盖。

### 暂存区寿命

`105D30` 构造栈上的 SurfaceLock，设置 `+50=源指针`、`+58=stride`，同步调用 texture+90 的 lock/unlock。路径 `105C70 → 1EA500 → 125DE0` 在返回前将源像素复制到映射 staging buffer（相同 stride 整块复制，否则逐行复制）；`105CB0 → 1EAA30` 随后处理 GPU 上传。因此包装器不把原解码缓冲改脏，也不依赖其随后释放行为；它只复用固定 384,000-byte 暂存区，无每帧堆分配、无缓存电影对象指针。驱动/GPU 实际呈现依然属于用户验收边界。

本轮 REA Evidence：`ev_b164537c81753fac62af69cf752c105c32e936ace2635b130828793886f36544`（选定帧描述符）、`ev_a2c739fc8d2b541cb187f8088b9774d50eae51e5f446f66ccb42453b369036a3`（解码图像转换）、`ev_ddbf25787b9dc67dc46223259b6b5af0a398c3fe504dfc5286c37d25ec1bdc22`（原转换器）、`ev_83e25726a7c7ceade9313d3837b9fe2ff8bf0f0df86992351cf45518ff57800c`（lock）、`ev_26cbf99d0553bb1047b73d31479ac37f3e776349b14cbfa3f996f20660d8d74a`（unlock）。完整复制函数与转换证据保存在本地 `build/movie-overlay-native/`。

## 格式与 PE 处理

`.locmov` 为 RX，仅保存包装器、覆盖表及复制后的原异常表；`.movbuf` 为 RW virtual-only 384,000 bytes，不把空缓冲打入载荷。没有 RWX 节，没有新 imports 或绝对地址 fixup。

MOV1 数据：16-byte `<4sIII>` magic/movie_count/width/height；每电影112 bytes（96-byte NUL-padded DAT 名称，4个u32：名称长度、帧数、帧表相对偏移、保留0）；每帧24-byte `<ddII>` start/end/覆盖串相对偏移/run_count；覆盖串连续 `{u32 BGRA字节偏移,u32 像素数,像素数×RGB三元组}`。偏移相对 MOV1 表头，完整覆盖串去重，不含完整原电影或背景帧。

包装器保存7个非易失寄存器、分配64-byte栈，保留调用参数和 Win64 shadow space。新增 RUNTIME_FUNCTION 与 UNWIND_INFO，旧异常表完整复制，按 RVA 排序。原头部空间不够时按 FileAlignment 扩展头部，平移所有原 section raw pointer 和调试目录 raw pointer，**RVA 不变**。签名/COFF符号/辅助指针等未支持变体拒绝。

回滚先恢复头部/原始 raw 布局及上传 CALL，完整 SHA 核对；再按原流程逆序撤销 debug、SFX 字幕、字面量、UTF-8。最终原 EXE 和归档完整 SHA 与原件一致。

## 离线验证

- 原34组媒体身份、102成员逐字节不变；全部24个有覆盖的片段、5913帧离线解码；3547帧覆盖、18对白/9译注/18标题全部有实际帧。
- 每个解码帧独立重放稀疏覆盖，RGB 与编译画面一致，任意 alpha 保留；标题源帧 SHA、装饰和保护区域守卫复用原规则。
- 安装到最终 EXE 的真实 `BDBCA` CALL 包装器，在两个 ASLR 基址逐帧执行全部3547覆盖，核对 BGRA、源不可变、调用/栈/寄存器/unwind；另测原 CALL 基线、未知媒体、异常时间/尺寸/stride/模式、帧末端、打开路径、旧请求/新媒体及循环偏移。原驱动上传是明确的替身边界。
- 全量构建两次逐字节比较；原生文本、SFX、F1/L3+Y继续回放；差分实际应用与隔离回滚；安装器重复发布及真实嵌入载荷检查→安装→重复安装→恢复。

当前命令、完整输出/退出码/哈希见 `build/release-candidate/VERIFICATION.txt`、`movie-replay.json`、`movie-assets/layers-report.json`，安装器见 `build/installer/VERIFICATION.txt`。这些离线结果不宣称已经在游戏中播放或通过 GPU/实际控制器验收。

复现沿用 [BUILDING.md](../BUILDING.md)，人工验收见 [MANUAL_TEST.md](MANUAL_TEST.md)。旧重编码版完整候选与安装器在本地 `build/movie-overlay-release/baseline/` 和 `previous-setup.exe` 保留作对照，不再作为当前交付。
