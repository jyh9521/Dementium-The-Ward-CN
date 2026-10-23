# `.binfont` 数据格式调查

日期：2026-10-23。只读输入 `CONTENT.TAR:fonts/d2font_12x15.binfont`，7620字节，SHA-256 `a4d07a4bf8b64737baaeae243e7aa0fec6c16dedc3f18a4eb19ed0f9e6ead183`。本文件先记录独立数据侧证据；运行时语义以EXE静态调用链交叉验证为准。

## 已验证：字节布局与离线解码

| 偏移 | 类型/长度 | 实际数据与观察 |
|---|---|---|
| 0 | u32 | 1；loader未使用，写出保留 |
| 4 | u32 | 8；字体基本行高/linefeed来源，不是页表指针 |
| 8 | 256*u32 | 仅第0项为1032，其余为0 |
| 0x408 | 32字节 | 256位位图，LSB优先；非零metrics槽位与置位项逐项一致 |
| 0x428 | 256*8字节 | 每个槽位八字节metrics；无效槽位全零 |
| 0xC28 | 20字节 | `<6H2I>=(0,1,128,256,128,256,0,32768)` |
| 0xC3C | 16字节 | `<4I>=(0x20000,4476,4431,4444)` |
| 0xC4C | 4431字节+1零填充 | zlib流；解压4476字节 |
| 外层解压+0 | 12字节 | `<3I>=(0x20000,4463,4476)` |
| 外层解压+12 | 4463字节+1零填充 | zlib流；解压131072字节 |
| 0x1D9C | 40字节 | 原样保留的尾部数据，见下 |

RGBA解码为128x256、每像素4字节；字形预览清晰，覆盖拉丁字符及西欧重音字符。图集含180个有效槽位。此结论由真实字节解压与预览支持，不依赖扩展名。

每个metrics的前u32按 `x=v&1023; y=(v>>10)&1023; height=v>>20` 拆分，后四字节为两个u8、两个i8。以 `N` (0x4E) 为例，`4b70a0000907ff03` 得到 `(x=75,y=28,height=10,width=9,advance=7,bearing_x=-1,bearing_y=3)`。矩形在图集中的字形与字符一致。180项矩形全部位于图集范围；EXE loader已确认x/y/height、width和两个有符号bearing的使用；advance(+5)另由查字/测宽调用链确认，不能只从loader读入推出。

压缩框架的压缩大小分别等于实际zlib流字节数；aligned字段等于 `align4(12+compressed_size)`。20字节图像头之后的u32是原始像素字节数，原图恰好为0x20000，不是flag。紧接着的两个frame都为`<uncompressed_size,compressed_size,aligned_total_size>`：外frame解开得到内frame，内frame解开得到RGBA。两个层次的zlib均完整结束，尾随仅零对齐。此项已通过415个内层tex资源交叉确认，见INNER_TEXTURE_AUDIT.md与PITFALLS.md中的历史POC修正。

尾部十个u32为 `(8,0,3112,7580,2,3112,4468,7582,0,2)`；其中3112是纹理起点，7580是尾部起点，4468是纹理总跨度。这些数值关系已验证，随后EXE loader静态交叉确认分区描述符及重定位规则，见下一节。

## 高置信推断与未确认项

- EXE loader确认256项一级页表、256项字形槽位按码点高/低字节索引；文本编码是否UTF-8仍须独立解码器调用链，字库布局本身不证明它。
- 图片loader 0x1400e9ee0读取两对宽高并计算比值，分别作为逻辑/纹理宽高；Evidence ev_75842c35919755f38710d6e6e49025cd59ec1e2e79ab522ed28b412050f658cb。GPU上传仍由边界double，非实机证明。
- metrics+5的advance由单独测宽路径验证；width与bearing已有loader交叉证据。
- 新页增加、atlas扩展和可变长重定位已按静态loader规则实现并离线往返验证；实际引擎读入、显示和裁剪仍须手动运行验收。

## 工具及测试

`tools/binfont.py` 提供有界解析、metric编解码、原样no-op回写、单字形RGBA切片及 `BinFont.write(glyphs,rgba,width,height)` 通用BMP页/扩图写出。未验证字段原样保留；压缩大小有限额，拒绝截断、错误帧、非零填充、页越界/重叠、缺席字形非零metrics和图集越界。

纯合成测试不包含商业字体数据，另覆盖扩图后的实际分配长度和拒绝旧长度：

```powershell
python -X utf8 -m unittest discover -s tests -p test_binfont.py -v
```

实际字体亦通过解析：`ORIGINAL_BINFONT_PASS 180 128 256 (131072, 4476, 4431, 4444, 131072, 4463, 4476) 40 True`。最后True表示原样回写逐字节相同；不是游戏内显示验收。

## 《病房2》复用评估

本作没有上游JSON+PNG字库接口。上游 `tools/font_pipeline.py` 的Pillow字形栅格化、字体身份/授权检查和按locale配置思路可复用；其atlas序列化、JSON字段、资源路由以及像素预算不适用于当前binfont，不应复制后直接使用。当前parser为目标格式适配层，未修改已验证的ZAR/TAR核心。

完整原始字体、RGBA与预览只留忽略目录 `build/phase2/research/`，不提交；当前工具与合成测试不内嵌原始字形或商业素材。

## 已验证：EXE loader与重定位交叉证据

- `build/phase2/evidence/font-entry.json`，Evidence `ev_5e3facf46f55f6e74e746045a97b097cc26805ec09fa011a6681218fc9ae3d17`，函数 `0x1400e9980`：固定从字体基址+8读取256项页表；每页256项metrics；x10/y10/height12位、width位于+4、signed bearing位于+6/+7。header+4赋给字体基本高度，另派生+1行高；不是页表地址。
- `build/phase2/evidence/0x1400ea2a0.json`，Evidence `ev_caa8210c9b1123fd044fa2abde2a8b9ed4fabc2d481ede50c80b79fb2bd4c3a5`：分区加载与重定位；末尾u32是分区数量，之前每分区16字节描述符 `<offset_with_compression_highbit,size,reloc_offset,reloc_bytes>`。本作font和texture两分区均未启用分区高位压缩；纹理自己的双层zlib是内层图片格式，不与此标志混淆。

原文件布局是：字体分区 `[0,3112)`、图片分区 `[3112,7580)`、字体重定位流 `[7580,7582)`、两字节零填充、两个16字节描述符、末尾count=2。字体descriptor为 `(0,3112,7580,2)`；图片descriptor为 `(3112,4468,7582,0)`。

重定位流逐u16读取：正signed值表示相对前项的offset增量；非正signed值与下一u16组成绝对offset `(first&0x7fff)|(next<<15)`。loader向目标u32指针加上分区实际内存相对全局地址池基址的偏移。原流只有delta8，因此修正页表第0项。新builder为每个非零页表槽位产生递增delta；所有槽位在8..1028内，差值均小于32768，无需绝对offset扩展形式。parser对当前支持的delta形式和页指针一一对应做严格检查。

### 扩展结构验证

实际原字体保留180项glyph/metrics/像素，将atlas扩至128x512，增加0x620F、0x65B0、0x6E38三个码点所在页。该结构实验新增字形像素为空，只用于验证新页与relocation，不是中文显示样本。

```text
EXPANDED_BINFONT_PASS original_glyphs=180 retained_pixels=180 new_pages=3 atlas=128x512 relocation_count=4 output_bytes=13268
```

本次构建新增三页并保留page0，原180项字形切片逐字节保持；新输出重新解析得到同样metrics、RGBA和4条重定位。双zlib重新压缩导致压缩字节与原版不同，但字形像素不变。无修改输入仍返回原始bytes，不改变原压缩流。以上是静态规则与离线处理验证，不是引擎内读入或显示证明。

## 第二阶段实际中文样本及原生loader回放

最小样本使用page0未占用槽81/8D/8F，不需要新增Unicode页。新字库183字形，atlas128x512；真实0x1400e9980与0x1400ea2a0在Unicorn读取新旧文件，原180字形尺寸/bearing保持，新增3字形正确，sprite数量256、页指针重定位通过。VFS、分配器、image/GPU与sprite构造边界double；不启动EXE进程，不证明GPU画面。

序列化+4在代码中命名base_height=8；实际Font+0x818默认由此+1，上层0x1400317b0又设为13。因此不将base_height作为最终运行时行距。实验完全保留这些字段及原EXE。
