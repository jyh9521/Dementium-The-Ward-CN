# v1.1.1：四项实测截图反馈

## 根因与已实施修正

| 用户现象 | 根因 | 修正及离线证明 |
|---|---|---|
| 拾取说明与广播叠字 | 播放标志不足以代表实际混音；没有排除模态顶屏 | 原PCM table、延迟、有效增益、顶屏/+64/+68守卫；执行BBBA0原开关分支，关闭后按当前采样位置恢复 |
| 出门后同句广播双行 | 同一cue ID的多个活动声源逐条绘制 | 每帧同ID只显示一个实际命中cue的源；gap-first不占去重标记 |
| 显示值HI-RES CRT漏英 | EXE固定字面量表为空，资源汉化未覆盖此路 | 四个原位受守卫槽改经典/经典CRT/高清/高清CRT；五语言×五模式×双基址selector实际执行；新增“高”入字库 |
| 调试菜单贴左且列重叠 | 原生名称X0、开关X64按英文布局 | 同尺寸原指令改X16/X112；21表650行双基址，最长名称78，最小列距18；原unwind/输入不变 |

开头房间广播是否原本可听，截图本身不能确定。未添加房间禁播规则，也未改原音、音效触发或播放时间；非零有效增益门禁不等同于人耳听感验收。

本作偏移、对象字段和字面量均独立核对，没有复制病房2偏移。音频说明见[AUDIO_SUBTITLES.md](AUDIO_SUBTITLES.md)，显示共享语言影响见[DISPLAY_MODE_LABELS.md](DISPLAY_MODE_LABELS.md)。

## 保持不变

- 原视频102个IVF/DAT/OGG成员字节不变，现有对白、画面译注、章节标题覆盖层保留。
- 安装器UI源码除版本元数据外不变；相同三种尺寸/缩放的WPF预览逐像素对比，图标/顶图原字节核对。
- 独立F1、秘密序列启用后的L3+Y、所有作弊回调/值以及显示枚举顺序不变。
- 不覆盖上一轮用户测试样本build/release-candidate/sample，新样本在build/ui-feedback-release/sample。

## 离线与实际验收分离

自动化没有运行游戏进程或写Steam目录。原生指令模拟的GPU绘制、虚函数边界用替身，不宣称实际渲染/可听性/实体输入已经验收。手测步骤见[MANUAL_TEST.md](MANUAL_TEST.md)。

验证记录、安装器身份及提交状态见[INSTALLER_VERIFICATION.md](INSTALLER_VERIFICATION.md)。源/改/回滚完整字面输出在build/installer/VERIFICATION.txt；独立只读审查在build/ui-feedback-release/review.md。
