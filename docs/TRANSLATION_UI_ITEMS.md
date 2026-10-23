# 界面与物品文本翻译记录

## 范围与状态

- `locales/zh-CN/strings-ui-items.json` 共233条：155条表格记录及78条物品、开门、解锁、查看文档记录。
- 196条译文，37条制作人员姓名、公司名称保留原文，分别标记 `translated`、`preserved-name`。
- 查看文档范围为实际存在的 `examine.000` 至 `examine.046`，缺失编号未擅自补造。
- 每条保留源ID、资源名、资源SHA-256、原文、字节偏移、原控制码清单等元数据。没有生成新的源身份值。
- 校验：233条ID唯一、目标非空、原文元数据逐字段不变；原文与译文的换行序列及0x01–0x08控制码顺序完全一致。
- 本项为文本对照初译与静态校验，不代表资源回写、原生解码或游戏内排版验收。未启动游戏，未操作安装目录。

## 术语

参考《病房2》术语表的通用词；本作资源与剧情细节独立翻译。

| 原文 | 本作译文 |
|---|---|
| Flashlight | 手电筒 |
| Nightstick | 警棍 |
| 9mm Handgun | 9毫米手枪 |
| Shotgun | 霰弹枪 |
| Electric Buzz-saw / Buzz-saw | 电锯 |
| Machine Gun | 机枪 |
| .357 Revolver | .357口径左轮手枪 |
| Sniper Rifle | 狙击步枪 |
| Keycard | 门禁卡 |
| Small / Iron / Gold / Silver / Bronze Key | 小 / 铁 / 金 / 银 / 铜钥匙 |
| Notepad | 记事本 |
| Gramophone Record | 留声机唱片 |
| Door Handle | 门把手 |
| Photograph Fragment | 照片碎片 |
| Maintenance Glove | 维修手套 |
| Amanda | 阿曼达 |
| West / East Building | 西楼 / 东楼 |
| Courtyard West / East | 西庭院 / 东庭院 |
| Checkpoint | 检查点 |
| Graphics Options | 画面设置 |
| Demented | 癫狂（最高难度名称） |

## 待场景核对

- `UIOptionsNew.tbl` 的 DISPLAY、CONTROL TYPE、QUIET、KEYBOARD、MODERN、CLASSIC、Filter 当前按设置项常用含义翻译；需要确认归属与字符宽度。
- nursery暂译“育婴室”；玩具钢琴支持儿童用途，但未见场景，暂不改成其他专用房间名称。
- Demented译“癫狂”保留与游戏名称的语义呼应；不据此推断难度参数。
- `examine.046` 的 `Mommy x` 按母亲亲吻落款意译“妈妈，吻你”；x不是该记录的数字谜题信息。
- 照片碎片中的10、31、07原样保留；9毫米、.357、3楼等关键信息保持不变。
- `examine.040` 和 `.041` 保留原双重强调控制段，分别包裹“留声机 / 唱片”和“门 / 把手”，不合并控制码。
- 解锁文本中的 `small / key` 同样保留两个强调段，以“小 / 钥匙”承接。
- 制作人员姓名及公司名原样保留，岗位、标题和感谢语已译；不添加汉化人员署名。
