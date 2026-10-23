# 纵轴图例：间距、冒号与同水平线

## 用户实测与根因

用户截图确认旧“纵轴”紧贴按键，标签比动态“正常”偏上，且冒号丢失。四种输入图例是428×240独立贴图，状态值不是同图，而由原生选项函数C24E0绘制。

## 已验证坐标与修正

只读原EXE完整SHA锁定为26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e。Unicorn实际执行原caller片段C2BAE..C2BC9、C2C7F..C2CA2（双ASLR基址），捕获107DC0图像位置(-68,0)及EADC0状态文本位置(125,220)。绘制/GPU边界用替身，不运行游戏。

生成binfont中“正常/反转”字形墨迹为cell内Y3..14，故屏幕逻辑墨迹Y223..234。旧标签墨迹Y221..232、原图标Y220..235；三者中心不齐。

- 四种KEYBOARD/NX/PC/PS4的标签改为“纵轴：”，框[161,222,193,236]，实际墨迹Y223..234。
- 原15×15按键图标从[140,220,155,235]整体下移1px至[140,221,155,236]，逐像素复制，不重画/缩放按键图案。
- 图标与标签间留6个原生像素；冒号墨迹后到动态状态留4px。图标、标签、正常/反转的可见中心均为Y228.5。
- 只改变4个图例及ZAR的关联~INDEX元数据（若成员尺寸变化）；CONTENT.TAR、字体、EXE、输入行为、其他选项及电影保持原样。

## 可复用基础设施

`tools/build_image_text.py`新增可选relocations：源/目标都受允许区域约束，尺寸相同，拒绝保护区、跨移动覆盖和标签遮盖；从源图快照复制，支持单次源/目标自重叠。最后再次验证目标逐像素相等。原无移动配方保持原行为。技术能力不绑定具体语言；本地化目标与坐标只在locale JSON。

`tests/test_yaxis_alignment.py`先在旧代码/数据复现4测试7个断言失败，再通过图标移动/越界/保护/重叠及四设备对齐回归。`tools/verify_yaxis_layout.py`结合真实caller、生成binfont、4个源身份锁定Texture容器和离线组合预览，核对正常/反转两状态；预览不是游戏截图。

## 本轮交付与手验

本轮不生成安装包，不修改dist中现有v1.1.1安装器；该旧安装器不包含本次修正。新测试副本为build/yaxis-alignment/sample，旧build/ui-feedback-release/sample保留。

```powershell
$game = "C:/Program Files (x86)/Steam/steamapps/common/Dementium - The Ward"
python -X utf8 tools/record_locale_verification.py --game "$game" --output build/yaxis-alignment
python -X utf8 tools/verify_yaxis_layout.py --game "$game" --build build/yaxis-alignment --previous-build build/ui-feedback-release
python -X utf8 tools/verify_sample.py --output build/yaxis-alignment
```

先由用户退出旧测试进程，启动新副本；在设置/背包控制图切换正常与反转，确认按键、纵轴：及状态值同水平线、间距舒适。键盘及可用实体手柄、不同缩放/窗口方式仍由用户验收。源码和数据提交推送，但安装打包等待用户确认。

## 本轮离线结果

- Python257项通过；4设备×2状态组合与双ASLR原caller回放通过。
- 相较上一轮仅4张YAXIS及~INDEX改变；EXE/字体/CONTENT.TAR保持字节相同。
- 新ZAR SHA256：`5fef92b88ad8ee2d82b1b94ae685296c4b2452c6bd508fcdcd6f840e2e5fddbe`。
- BASELINE/MODIFIED/ROLLBACK均退出0；原完整SHA恢复，modified与sample保留；四产物及实际命令/字面输出在build/yaxis-alignment/VERIFICATION.txt。
