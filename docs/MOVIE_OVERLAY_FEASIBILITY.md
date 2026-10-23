# 保留原视频的字幕方案调查

> 本页保留实施前调查快照。后续v1.1已实现原视频上传前稀疏覆盖，当前实现与证据见[MOVIE_OVERLAY.md](MOVIE_OVERLAY.md)。

日期：2026-10-23。调查对象为本作 Steam build21501403；未启动游戏，未写入 Steam 安装目录。此次只调查，不替换现有安装器。

## 已验证：容量消融实验

用身份锁定的原始 rom.zar 重建，保留当前候选的全部 53 项非电影成员修改；102 个 MOVIES 成员（34 组 IVF/DAT/OGG）逐字节保留原版，排除当前 48 项电影修改。使用与当前安装器相同的 source-copy/add 生成器：

| 项目 | 当前完整候选 | 保留原电影的实验副本 |
|---|---:|---:|
| 资源补丁载荷 | 165,935,904 bytes | 1,567,487 bytes |
| 相差 | | 164,368,417 bytes |
| 安装器体积 | 241,513,533 bytes | 尚未构建 |

若仅做算术替换，安装器约 77,145,116 bytes，接近二代；**这不是新版安装器的实测容量**，不包括后续叠字代码、标题层及发布压缩变化。实验归档没有电影汉化，因此不是可交付版本。现有 dist 安装器保持原样。

原件 SHA256：`9a9ceffb4bbf5fd9a22d5b9d0b87b963ab3abf1bf4afa7e49c5bdf44875fd42c`。
完整候选 SHA256：`6c7000b22354ed1b10ac7ac4d0e2892b6e1c1b6ecdae078246723cdb00b269db`。
实验归档 SHA256：`126238583edfab7b1190625937e8715a91de65d6116b150ca719cdc90770957b`。

基线无修改往返一致；实验差分实际应用后与目标 SHA 一致；独立副本恢复到原件 SHA，实验归档保留改变。完整命令、字面输出、退出状态在本地 `build/movie-overlay-research/VERIFICATION.txt`，测量在 `measurement.json`。

```powershell
python -X utf8 tools/research_movie_payload.py baseline --source 'C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward/rom.zar' --candidate build/release-candidate/MODIFIED_FILE.zar --output build/movie-overlay-research
python -X utf8 tools/research_movie_payload.py modified --source 'C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward/rom.zar' --candidate build/release-candidate/MODIFIED_FILE.zar --output build/movie-overlay-research
python -X utf8 tools/research_movie_payload.py rollback --source 'C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward/rom.zar' --candidate build/release-candidate/MODIFIED_FILE.zar --output build/movie-overlay-research
```

工具仅允许 build 下且不包含输入的输出目录，拒绝不匹配的原件/候选身份；不修改 EXE，不安装补丁。回滚为把原件复制到独立实验副本，不代表未来电影 hook 的代码逆向恢复测试。

## 已验证的静态入口

本作地址均为该 EXE 的 RVA，不能照搬二代偏移。原 EXE SHA256：`26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`。

- `BD140` 接受影院对象 RCX、电影 stem RDX、模式 R8D；将名称写入对象 `+B4` 及字符串 `+60`，并发送媒体命令。请求名称变化不等于新媒体已就绪，必须防止新 stem 与旧媒体时钟交叉绑定。
- `BDA50` 通过全局 `C15A90` 媒体对象的 `vtable+38` 取得 double 时钟，依此取视频帧。全局 `378208` 是帧选择阈值，不应直接用作字幕当前时间。
- `BD510` 绘制电影与现有 `textures/movies/<stem>.png` 叠层；最后 sprite draw 后、renderer end 前存在候选字幕绘制位置。原函数未调用已知文字入口。
- 现有 `EA700/EA950/EADC0` 字体链和已扩展 binfont 有复用基础；但已有 SFX HUD hook 的覆盖范围不证明影院也会经过该 hook。

复用证据：`MOVIE_FORMAT.md` 中的 REA Evidence `ev_468c524115c3848ce132542478a57da7438e0b62615b4ca6b527716cf2cc6c07`、`ev_96a835be3588b7c7b7dbcd5d87007cee0fa3b1b04db99584cc8886d909b103c8`、`ev_0b6ac17f70be5ac5b608e75145f87f19c7f17519d1719d101ab00193d033e4ef`；以及原件匹配的 `build/full-research/movie-format/analysis-snapshot.json`。详细 ABI/状态审查保存在本地 `native-findings.md`。

### 媒体时钟补充核对

本轮原件匹配的 REA/Ghidra 独立反编译再次确认 `1011F0`，Evidence `ev_f1fafa97cb04fadfaff643c2f7ac8641f4858fa3f985f24e8148e06f7c54baa5`；本地完整记录 `clock-rea.json`。

原件构造器把 MuxMediaStreamer vtable 设在 `314F68`，其 `+38` 指向 `1011F0`；VPX vtable `3150E8` 的 `+38` 指向 `102EA0`。直接读取原件 PE 映射并独立反汇编确认：

- `1011F0` 优先选择对象 `+8148` 子对象，否则选择 `+8150`；调用子对象 `vtable+38`。
- 有 `+8148` 子对象时，还把该子对象 `+50` double 加入结果。因此应复用 Mux 时钟，不能随意取系统时间或只取 VPX 时钟替代。
- 本地 Unicorn 实际指令回放在两个基址、两种分支共 4 例通过：子时钟替身返回 12.5，`+50=3.25` 时结果为 15.75，否则为 12.5；RBX/栈保持。子时钟、实际播放及 GPU 是未覆盖边界。证据：`clock-disassembly.txt`、`clock-replay.json`。

## 高置信可行性与未完成事项

**高置信推断：保留原视频，以原生时钟驱动独立字幕层，是值得实现的主路线。** 尚未安装或实现这条路线，不声称已具备游戏内效果。

必须同时处理：

1. 对白底部字幕、画面词顶部译注，复用现有审核译文和时轴；按媒体就绪/停止/切换清空，不持有已释放的 streamer。
2. 章节标题已经嵌入视频画面；中文叠字不能简单覆盖英文而留下重叠。需独立验证局部遮盖、中文标题与源渐隐同步，或小型稀疏标题层；禁止删掉现有标题汉化来换体积。
3. 影院函数会遗留渐隐 alpha（`3A5684`）及 blend 状态（`6BC3A8..C0`）。文字绘制前必须核对并保存/设置/恢复；文字队列 `3FC3A0+4C` 与状态 `3FC399` 也有约束。
4. 原 SFX 字幕应保持；影院字幕应使用影院入口而非假定 HUD 同帧执行。需测字幕开关、跳过、暂停/恢复、重播、EOF、连续切片、画幅缩放与 ASLR/栈展开。
5. 后续补丁完成后才重建安装器，运行完整离线回放、差分应用和代码回滚测试，再由用户进行实际影院验收。

## 二代对照

当前本地二代构建使用 `EN/*.SUB` 独立字幕资源，无电影重编码步骤；嵌入的三个 gzip 载荷分别为 754,729、6,819、1,334,835 bytes，总计 2,096,383 bytes，安装器 78,509,081 bytes。二代同样采用自包含 .NET/WPF/MaterialDesignThemes；它提供的是可借鉴的界面/资源组织，不是本作已存在同样 SUB 读取路径的证据。
