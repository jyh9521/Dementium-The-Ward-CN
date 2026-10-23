# Movie / sound format investigation

日期：2026-10-23；本作Steam build21501403，原EXE SHA-256 `26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`。所有行为均为只读安装输入、离线解析/ffmpeg解码/静态反编译，没有启动游戏，没有烧录字幕，没有修改电影或Steam文件。

## 已验证：34组电影结构

外层ZAR含34组同stem的`.IVF`、`.DAT`、`.OGG`。IVF/DAT合计9350帧，全部400×240、VP90、rate30/scale1。完整逐文件大小/SHA身份沿用`assets/inspection/archive-manifest.json`；配对及无修改往返报告在忽略目录`build/full-research/movie-format/movies.json`。

IVF为little-endian，32-byte文件头`<4sHH4sHHIIII>`：`DKIF`、version0、header_size32、FourCC`VP90`、u16 width、u16 height、u32 rate、u32 scale、u32 frame_count、u32 reserved0。之后每帧为`<u32 payload_size,u64 timestamp>`的12-byte帧头，再接payload。时间以`timestamp*scale/rate`秒计算。本数据帧时间严格递增、无额外尾部。

DAT文件头24byte：

|偏移|类型|已验证含义|
|---|---|---|
|0|u32|版本1|
|4|u32|帧数，与IVF frame_count一致|
|8|u64|所有IVF payload_size的最大值，不是音频大小|
|16|f64|fps=rate/scale，原数据均30.0|

后接frame_count×24byte的`<f64 time,u64 flagged_offset,u64 payload_size>`：

- `time`是秒，原资源时间表保留约6位小数，与IVF时间差≤0.5微秒。
- `flagged_offset & 0x7fff_ffff_ffff_ffff`是该帧在IVF内**12-byte帧头的绝对文件偏移**，首帧32，不是payload起点。
- `flagged_offset >> 63`是关键帧标志。全部34资源的9350项与ffprobe独立VP9 packet flags完全一致（`codec-keyframes.json`）。
- `payload_size`与对应IVF帧头size完全相同；不含12-byte帧头。

`tools/movie.py`逐帧校验所有成员bounds/count/order/time/maxsize，34组DAT无修改重建均byte-identical。合成增长测试会同时更新后续offset、payload size、max size，并保留原time字节。

## 已验证：原生消费逻辑

REA恢复匹配原EXE快照，不运行游戏。证据保存在`build/full-research/movie-format/`。

|函数|静态观察|Evidence|
|---|---|---|
|103210|读DAT进vector，检查首u32=1；读32byte IVF头，检查version0/header32；保存width/height，计算scale/rate，读取DAT+0x10|ev_22274ba3321351d9d897edcd434ba31094cb905406bff22fbb58406859b43f40|
|103640|读取DAT帧数、DAT+8的max size传decoder；查表时间选择目标前最近bit63关键帧；清除bit63后seek；逐帧读12byte IVF头和payload；以timestamp×scale/rate标记解码帧|ev_0b1d801d8928a229ff390dfd084c90626c764ff39929f4148dbea432567dfca8|
|1042B0|媒体工厂创建MuxMediaStreamer/VPXMediaStreamer，并构造同stem.dat/.ivf（后续音频分支仍在大函数里）|ev_d9f623dc106eceb7740bd1f47e459254f43503bfa88f2235f9e033ec98d82ad2|
|BD140|UIMSCinema加载/保存电影stem、切换播放状态|ev_468c524115c3848ce132542478a57da7438e0b62615b4ca6b527716cf2cc6c07|
|BDA50|取媒体时钟，按帧时间更新图像、结束或跳过处理|ev_96a835be3588b7c7b7dbcd5d87007cee0fa3b1b04db99584cc8886d909b103c8|
|BD510|影院画面/`textures/movies/<stem>.png`叠图绘制，不调用已知文字入口|ev_0b6ac17f70be5ac5b608e75145f87f19c7f17519d1719d101ab00193d033e4ef|

103640接受的单帧payload上限为0x10000000；buffer分配使用DAT最大尺寸字段的低u32。工具因此拒绝超上限数据，而不让u64值静默截断。媒体工厂完整dossier大于MCP传输限制，保留完整Evidence；`constructor-view.json`只取前14000 UTF-16单位，不能把这个局部视图说成完整控制流审计。

## 重编码后的DAT同步条件

可以为**相同codec、尺寸、rate/scale、帧数及逐帧timestamp**的新VP9 IVF重建DAT。`rebuild_dat(original_dat,original_ivf,new_ivf,keyframes)`先验证原配对，再强制这些条件不变；只更新DAT最大payload与逐帧offset/size/关键帧标志。`keyframes`必须由新文件的独立codec probe提供，不能沿用原GOP。`probe_ivf_keyframes`检查ffprobe packet count/size/PTS与自建IVF解析一致后返回标志。

这确认了容器同步实施条件，不是对任意VP9编码选项的引擎兼容验收。本轮没有实际重编码原电影或烧录字幕；重编码可能改变VP9 profile/pixel-format/GOP，下一步应保留原codec特征并做libvpx离线解码、逐帧timestamp/画面对比及可逆归档差分。

## 字幕入口状态

已知EA700/EA950/EADC0文字链的17个直接caller中没有影院BD140/BD510/BDA50；本次搜索已定义字符串未发现subtitle/SRT/ASS资源路由。影院更新与绘制路径只见媒体时钟、视频帧及电影贴图，没有观察到现成时间轴字幕绘制入口。

这是**有边界的未发现**，不是证明引擎绝对不存在字幕实现。当前不能把18条电影字幕JSON写入归档就宣称会显示；需要后续字幕hook或经验证的离线烧录方案。SFX口语更需要按音效触发字幕，电影DAT时间轴不覆盖它们。

## 已验证：177个FLAC离线解码

`tools/movie.py`从身份锁定的ZAR成员读取177个FLAC（26 MUSIC、151 SFX），逐条ffprobe得到声道/采样率/duration，再用ffmpeg `-xerror`完整解码为mono16k WAV；全部退出码0，总时长1549.800118秒。逐项源SHA/大小/duration/原采样参数/规范化PCM SHA及本地WAV路径在`build/full-research/movie-format/flac.json`。规范化FLAC PCM与34电影OGG已提取PCM哈希无完全相同项。

151个SFX用已缓存faster-whisper-small、CPU int8、VAD、beam5作候选筛查（不联网），原结果在`flac-asr-small.json`。发现电影之外的明确口语候选：

- `SFX/EMERGENCY/EMERGENCY_01_MONOMIX_8HZ_8BIT.FLAC`：广播“This is an emergency. Everyone must evacuate the building...”
- `SFX/ENEMYBT/TALK01LO.FLAC`：small识别“I am stronger than you.”
- `TALK02LO`：“defeat me”；`TALK04LO`：“I OWN YOU”；`TALK05LO`：“You cannot defeat me.”

这些候选已交给字幕审校任务做large-v3复核；广播尾句large-v3已更正为“Locate the nearest stairwell.”，非small误识的“Locate in your cell”；极短/变声台词由独立审校继续复核，不把small单模型输出当定稿。其它小模型输出含BAM/MMMM/笑声等明显幻觉风险，未直接翻译。WHISPER/SINGING/GHOSTLY的VAD筛查没有稳定英语输出，不等于证明无语义；电影FLASHBACK与WHISPER的混音关联仍由独立音频复核调查。26条MUSIC本轮只做完整解码与身份记录，不声称已审听其每一秒或排除所有人声。

## 复现

```powershell
python -X utf8 tools/movie.py --archive 'C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward\rom.zar' --manifest assets/inspection/archive-manifest.json --out build/full-research/movie-format --ffmpeg (Get-Command ffmpeg).Source --ffprobe (Get-Command ffprobe).Source
python -m unittest discover -s tests -p test_movie.py -v
```

字面结果：`MOVIES PASS 34 paired DAT/IVF byte-identical no-op`、`FLAC PASS 177 decoded`；均退出码0。3项合成格式/增长回写/拒绝漂移测试通过。原电影、音轨、WAV、ASR原文与完整归档均留在Git忽略的build目录。
