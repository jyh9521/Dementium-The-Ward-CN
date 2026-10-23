# 原电影画面文字审计

只读原始IVF，未启动游戏。先前34组first/middle/last合计102帧之外，现追加**全部34组每0.5秒（30fps下每15帧）提取，共633张400×240原帧、68页接触表，全部逐组查看，ffmpeg解码退出0**。完整RGB SHA、源身份、抽样帧号和解码命令在本地build/full-research/movie-dense-half及结构化movie-frame-audit.json。原帧/接触表仅保留Git忽略目录，不提交完整电影或原帧。

## 已验证新增可见英文

- 16个CHAPTER01..16电影的中央原IVF帧本身包含红色章号及白色英文副标题；并非只有外部PNG包含文字。改好PNG不能单独充当IVF画面已覆盖的验证。
- NEWSCAST电视新闻中明确可读REDMOOR NEWS、MURDER、WOMAN MURDERED、CHILD SURVIVES。主要连续字样通过额外逐秒样本复核，不把18.97秒低清单帧误猜成MOTHER/WIFE。
- AMANDA02中间样本背景门上有很小的绿色EXIT，属于原电影场景文字，不是对白字幕。
- 加密审计确实发现原三点抽样漏项：AMANDA01开头章3、INTRO开头章1；CL_SIGHTING约9.0–10.0秒双门EXAMINATION ROOMS；BT_SIGHTING背景EXIT。嵌入章名现扩展为18部电影（仍只有16个独立章节），其后剧情逐像素原样透传。
- AMANDA02的EXIT在4.5–6.0秒样本清晰；BT_SIGHTING在3.0–3.5秒及9.5–10.5秒可见；检查室/出口均交由画面词译注，原电影场景保留，不伪称透视重绘。
- 其余12组每半秒样本未发现可靠可读英语标题或剧情字幕条；INTRO低清黑门牌、NEWSCAST红门牌/电视机壳、FLASHBACK留声机铭牌不可靠完整转录，明确保留不猜。FLASHBACK红墙放大是手印，未误转录为文字。
- **没有逐帧穷尽视觉审查**：半秒间隔仍可能漏掉更短快闪；黑暗、压缩、微字和遮挡可能不可读。章名变更的逐帧像素验证不等于所有电影逐帧文字识别，更不是游戏内验收。

## 新闻字样的抽样时间

|原字样|约可见抽样时间|建议译文|
|---|---|---|
|REDMOOR NEWS|3.5–6.5秒、35–35.5秒|雷德穆尔新闻|
|MURDER|7.5–13.5秒|谋杀案|
|WOMAN MURDERED|14–23秒|女子遇害|
|CHILD SURVIVES|24–33秒|女童幸存|

上表为0.5秒抽样可见时间，不是逐帧准确淡入淡出边界；淡变交叉处不猜精确首末帧，画面词采用独立译注而非运动透视替字。

## 逐组结果

|资源|半秒样本数量|观察|
|---|---|---|
|`MOVIES/AMANDA01.AVI.REFORMATTED.AVI.IVF`|23帧|embedded-chapter-title；CHAPTER THREE / The Infant Ward|
|`MOVIES/AMANDA02.AVI.REFORMATTED.AVI.IVF`|23帧|readable-environment-sign；EXIT|
|`MOVIES/BT_BOSS.AVI.REFORMATTED.AVI.IVF`|22帧|no-readable-english-in-half-second-samples；|
|`MOVIES/BT_SIGHTING.AVI.REFORMATTED.AVI.IVF`|26帧|readable-environment-sign；EXIT|
|`MOVIES/CHAPTER01.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER ONE / The Admittance|
|`MOVIES/CHAPTER02.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER TWO / The Rooftop|
|`MOVIES/CHAPTER03.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER THREE / The Infant Ward|
|`MOVIES/CHAPTER04.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER FOUR / The Cleaver|
|`MOVIES/CHAPTER05.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER FIVE / The Courtyard|
|`MOVIES/CHAPTER06.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER SIX / The Electric Buzz-saw|
|`MOVIES/CHAPTER07.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER SEVEN / The Main Security Room|
|`MOVIES/CHAPTER08.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER EIGHT / The Flashback|
|`MOVIES/CHAPTER09.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER NINE / The Hole in the Wall|
|`MOVIES/CHAPTER10.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER TEN / The Torn Photograph|
|`MOVIES/CHAPTER11.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER ELEVEN / The Guard Tower|
|`MOVIES/CHAPTER12.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER TWELVE / The Cleaver's Return|
|`MOVIES/CHAPTER13.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER THIRTEEN / The Door with No Handle|
|`MOVIES/CHAPTER14.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER FOURTEEN / The Wheelchair's Return|
|`MOVIES/CHAPTER15.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER FIFTEEN / The First Encounter|
|`MOVIES/CHAPTER16.AVI.REFORMATTED.AVI.IVF`|6帧|burned-in-chapter-title；CHAPTER SIXTEEN / The Final Encounter|
|`MOVIES/CL_BOSS.AVI.REFORMATTED.AVI.IVF`|14帧|no-readable-english-in-half-second-samples；|
|`MOVIES/CL_SIGHTING.AVI.REFORMATTED.AVI.IVF`|23帧|readable-environment-sign；EXAMINATION ROOMS|
|`MOVIES/COURTYARD.AVI.REFORMATTED.AVI.IVF`|27帧|no-readable-english-in-half-second-samples；|
|`MOVIES/ELEVATOR01.AVI.REFORMATTED.AVI.IVF`|33帧|no-readable-english-in-half-second-samples；|
|`MOVIES/FINAL.AVI.REFORMATTED.AVI.IVF`|71帧|no-readable-english-in-half-second-samples；|
|`MOVIES/FLASHBACK.AVI.REFORMATTED.AVI.IVF`|32帧|no-readable-english-in-half-second-samples；|
|`MOVIES/GENERATOR.AVI.REFORMATTED.AVI.IVF`|32帧|no-readable-english-in-half-second-samples；|
|`MOVIES/INTRO.AVI.REFORMATTED.AVI.IVF`|28帧|embedded-chapter-title；CHAPTER ONE / The Admittance|
|`MOVIES/LAIR.AVI.REFORMATTED.AVI.IVF`|34帧|no-readable-english-in-half-second-samples；|
|`MOVIES/MOLLUSCA01.AVI.REFORMATTED.AVI.IVF`|18帧|no-readable-english-in-half-second-samples；|
|`MOVIES/MOLLUSCA02.AVI.REFORMATTED.AVI.IVF`|13帧|no-readable-english-in-half-second-samples；|
|`MOVIES/NEWSCAST.AVI.REFORMATTED.AVI.IVF`|76帧|burned-in-broadcast-headlines；REDMOOR NEWS / MURDER / WOMAN MURDERED / CHILD SURVIVES|
|`MOVIES/WG_BOSS.AVI.REFORMATTED.AVI.IVF`|21帧|no-readable-english-in-half-second-samples；|
|`MOVIES/WG_BOSS2.AVI.REFORMATTED.AVI.IVF`|21帧|no-readable-english-in-half-second-samples；|

## 可复现命令

```powershell
python -X utf8 tools/audit_movie_frames.py --archive 'C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward\rom.zar' --dense-resource 'MOVIES/NEWSCAST.AVI.REFORMATTED.AVI.IVF'
```

字面结果：`MOVIE FRAMES PASS groups=34 samples=102 decode=0 dimensions=400x240 source=unchanged`；新闻补充输出`DENSE MOVIE FRAMES PASS samples=38 source=MOVIES/NEWSCAST.AVI.REFORMATTED.AVI.IVF`。完整源SHA、所选帧号、RGB SHA及实际解码命令在本地frames.json/dense-frames.json；不将音频审计或离线静帧查看说成游戏内验收。


## 全34组半秒加密审计复现

```python
import json
from pathlib import Path
import sys
sys.path.insert(0, "tools")
from audit_movie_frames import audit_dense_resource
archive = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward\rom.zar")
manifest = json.loads(Path("assets/inspection/archive-manifest.json").read_text())
movies = json.loads(Path("locales/zh-CN/movie-subtitles.json").read_text(encoding="utf8"))["movies"]
for row in movies:
    audit_dense_resource(archive, manifest, row["resource"][:-4]+".IVF",
                         Path("build/full-research/movie-dense-half")/row["movie"], "ffmpeg", 0.5)
```

实际合计：`DENSE ALL PASS groups=34 samples=633`；每组报告均decode_exit_status=0。已查看68张接触表；未改媒体翻译或主包。嵌入章名的修复与全部片源hash/剧情透传证据见MOVIE_TITLE_REBUILD.md。
