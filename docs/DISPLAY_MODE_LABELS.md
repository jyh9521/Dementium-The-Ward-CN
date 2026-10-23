# 显示模式固定标签修复

## 已验证

玩家截图的 `HI-RES CRT` 不来自 CONTENT.TAR 文本表，而来自 EXE 固定字面量。旧 `executable-text.json` 条目为空，漏掉了这一路；菜单标题“显示”仍已汉化，值却保留英文。

本作 build21501403 的原生 selector 在 RVA `0x2F8A0`，通过全局语言值 RVA `0x3FC3C0` 选择五项指针表；默认 English 表为 RVA `0x304AF0`。原生 mode 0 仍为 Debug，mode 1—4 顺序及行为完全保留：

| mode | 原值 | 简中 | 文件偏移 | 已审计槽字节 |
|---|---|---|---|---|
| 1 | RETRO | 经典 | 0x303B48 | 8 |
| 2 | RETRO CRT | 经典CRT | 0x303B50 | 12 |
| 3 | HI-RES | 高清 | 0x303B5C | 12 |
| 4 | HI-RES CRT | 高清CRT | 0x303B68 | 16 |

槽包含原字面量和其后全部连续 NUL，不含下一个非零字节；中文 UTF-8 加终止符均能原位容纳。复用本仓库严格完整 SHA/size、原字节/NUL guard、.rdata 非可写/非可执行边界与反向恢复工具，不扩展文件、不改代码/指针/重定位/显示参数。

病房 2 当前 `locales/zh-CN/executable-text.json` 的实际四值为“复古/复古CRT/高清/高清CRT”，而资源表另有 CLASSIC→经典；本作根据玩家希望采用“经典/经典CRT/高清/高清CRT”。仅参考命名和固定槽方法，偏移、容量、入口全部由本作独立核对。

RETRO 槽被 English/German/Spanish 共用，HI-RES 被 English/French/German 共用，HI-RES CRT 被 English/German 共用；共享引用将显示同一中文值，这是原地字面量替换的明确影响，未修改其他非共享语言字面量。当前汉化替代 English；不是为其他语言另做一套显示值。

## 离线回归

`tests/test_executable_text.py` 先以空 recipe 复现 RETRO 漏英（红测），再检查四项数据映射。Unicorn 回放原 selector 全部 5 语言 × 5 模式 × 2 加载基址，共 50 次，核对实际返回指针、English 实际 UTF-8 值和原枚举顺序。PE DIR64 按实际重定位表调整，禁止用 Python 重新实现分支替代指令回放。完整恢复链从改件回到 runtime baseline，再回原 EXE；严格比较 SHA。

离线通过不等于实际 UI 显示验收；手动需要轮换四种模式，确认“经典/经典CRT/高清/高清CRT”与原分辨率/CRT 效果对应，且切换及保存行为不变。未启动游戏，未向 Steam 目录写入。
