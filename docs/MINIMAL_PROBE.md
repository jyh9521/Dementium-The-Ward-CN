# 第二阶段：New Game最小汉化实验

2026-10-23。当前状态：离线构建/恢复完成，游戏内视觉验收NOT_TESTED。

## 实际修改

- `loc/en/UISSFrontend.tbl:0000`：New Game → 新游戏；运行字节81 8D 8F；源记录仍是真实Unicode中文。
- `fonts/d2font_12x15.binfont`：新加3个原本空缺槽位；180个原字形的metrics/像素及整个原128x256RGBA区域保持；扩为128x512。
- TAR成员顺序与未改成员保持；ZAR只改变CONTENT.TAR与派生~INDEX，二者大小一致。表格其他24行及全部278记录中的其他277条保持。
- EXE、DLL和其他安装输入不改；样本目录复制9文件，只有rom.zar为新产物。没有F1、原生补丁、安装器或Release。

## 已复用与新适配

- 沿用第一阶段从《病房2》复用的ZAR解析/双索引/稀疏差分/哈希核心及测试。
- 逐函数复用上游font_metadata、discover、resolve_fonts，保留MIT与OFL许可；字体源SHA固定。
- Pillow字体覆盖/栅格化、原图保留及locale配置模式沿用成熟方法；本作新增binfont序列化、双压缩/分区/重定位适配。
- 原生PE映射及确定性边界回放借鉴上游方法，所有地址由本作独立调查并以整EXE SHA守卫；不把地址当补丁复用。

## 验证层级

1. 72项纯合成测试：字库位域/帧边界/新增页/relocation，glyph覆盖/非空/越界/原像素，slot冲突/逆映射，输入版本及链接输出拒绝，以及既有封包测试。
2. 原包/原字体no-op字节相同，完整输入9文件SHA复核一致。
3. 重提取确认仅1条逻辑译文；未改成员、名称顺序、控制码与双索引通过。
4. 同输入构建两次逐字节一致，差分正向/逆向与额外文件副本恢复通过。
5. 原生指令回放：真实表解析、字节扩展、查字/测宽；真实font loader与真实重定位核心，原180/新183字形读取一致。VFS/分配/GPU/sprite构造边界被替代，不是完整运行引擎。
6. 图集直取离线预览已检查，仅证明墨迹可辨；实际游戏显示仍待用户手动测试。

## 产物

build/phase2/sample为手动启动副本；MODIFIED_FILE.zar为保留的改包，DIFF_FILE.json为绑定输入/结果身份的本地可逆差分；ROLLBACK_COPY.zar与rollback-sample/rom.zar均恢复原SHA。tools/ROLLBACK_PROBE.sh执行隔离恢复，不覆盖保留样本或Steam目录。

详见PROBE_VERIFICATION.md与MANUAL_TEST.md；身份与回放摘要可提交，完整游戏/字体/含整TAR的差分保持Git忽略。
