# 门牌与美术返工离线验证

最新样本：`build/framed-artwork-release/sample`。未启动游戏，安装器未更新。

- 全部267项测试通过。
- 原包无修改往返逐字节一致，278条记录；完整重复构建一致。
- BASELINE / MODIFIED / ROLLBACK均退出0，四产物已重新打开并校验。
- 最终26个美术资源与源依赖差分/完整mipmap匹配；43个框内墨迹位置，14个楼层牌，死亡两状态为共同母稿的亮度/光泽关系；4处不明小字区域原像素完全一致。
- 全部显示target的U+2014余量0，两处明确修改为` - `。原source与控制码保留。
- localized sample全部9文件身份匹配；24个字幕/菜单用例、双ASLR基址回放通过。
- 额外执行实际ROLLBACK.sh，仅两文件隔离副本恢复原SHA；modified与待测sample保留。
- `rollback-sample`有意只含EXE和ZAR，不对其调用默认要求9文件的verify_sample；其两文件分别对照完整原版身份表校验。

## 身份

ZAR SHA256：`bf4d6c52b7912f6216bd4662a15ba0948048f38dabbde2f734945506339c005f`。

EXE SHA256：`d426d3065b7fdf530d3fd48c9f117d3bb7339bf67c1252f600b68e5f32a8b7f0`。

## 实际命令与字面结果

### BASELINE

```text
C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py baseline --game C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\framed-artwork-release --locale zh-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
BASELINE PASS records=278 archive-members=668 content-members=2555 noop=byte-identical input=unchanged decoder=byte-widen
EXIT STATUS: 0
```

### MODIFIED

```text
C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py modified --game C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\framed-artwork-release --locale zh-CN
INPUT: C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward
MODIFIED PASS records=278 UTF8=roundtrip glyphs=884 dual-index=consistent reproducible=true native-replay=PASS game-launched=false
EXIT STATUS: 0
```

### ROLLBACK

```text
C:\Users\noway\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 C:\Users\noway\Downloads\Dementium-The-Ward-CN\tools\build_locale.py rollback --game C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward --output C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\framed-artwork-release --locale zh-CN
INPUT: C:\Users\noway\Downloads\Dementium-The-Ward-CN\build\framed-artwork-release\MODIFIED_FILE.zar
ROLLBACK PASS isolated-copy=original-sha256 text=New Game decoder=byte-widen font=original modified-and-sample=retained
EXIT STATUS: 0
```

完整字段、逐电影字面输出、输入与退出码：`build/framed-artwork-release/VERIFICATION.txt`及`verification-extra.json`。

四产物：MODIFIED_FILE.zar、DIFF_FILE.json、VERIFICATION.txt、ROLLBACK.sh，均在同一输出目录；本地差分含源依赖数据，不提交Git。

实际GPU、场景UV、全部缩放、死亡状态过渡和完整流程仍由用户验收。
