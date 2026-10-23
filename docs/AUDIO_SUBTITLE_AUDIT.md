# 非电影音频：全量语音筛查、字幕与分类

## 范围与边界

原版外层ZAR含177个FLAC：26个MUSIC和151个SFX，均已由`tools/movie.py`校验成员SHA-256、ffprobe读取并ffmpeg解码为build目录内的单声道16k PCM。177种PCM哈希全部不同，因此没有将不同音轨按文件名或时长错误去重。

全部177轨又完成一次**无VAD**的local small筛查，MUSIC也逐轨完整覆盖，不只扫描既有候选。总时长约25.83分钟（MUSIC20.56分钟、SFX5.27分钟）。输出133轨非空假设、44轨空假设；这绝不是“133轨有对白”，因为器乐、喘息、雷声及蜂鸣会产生大量识别幻觉。

结构化交付在`locales/zh-CN/audio-subtitles.json`：177个原始resource/SHA/时长、逐项分类、可播放中文cues与证据状态。原始FLAC、WAV和长篇识别假设仅在Git忽略的`build/full-research/`，不随翻译源数据提交。音轨从未改写，Steam目录从未写入，也未启动游戏。

## 已确认用于字幕的词句

这里的“确认”指未变换原音的多模型ASR一致与翻译审校，不等同于人工听校或游戏内字幕验收。播放cue统一标`translated-asr-consensus`；只有这些cue进入native overlay资源。

|资源|英文|译文|
|---|---|---|
|`SFX/EMERGENCY/EMERGENCY_01_MONOMIX_8HZ_8BIT.FLAC`|This is an emergency. Everyone must evacuate the building.|紧急情况！所有人员立即撤离大楼。|
|同上|Locate the nearest stairwell.|请找到最近的楼梯间。|
|`SFX/ENEMYBT/TALK01LO.FLAC`|I am stronger than you.|我比你更强！|
|`SFX/ENEMYBT/TALK02LO.FLAC`|You cannot defeat me.|你打不败我！|
|`SFX/ENEMYBT/TALK03LO.FLAC`|You are weak.|你太弱了！|
|`SFX/ENEMYBT/TALK04LO.FLAC`|I own you.|你属于我！|
|`SFX/ENEMYBT/TALK05LO.FLAC`|You cannot defeat me.|你打不败我！|
|`SFX/SINGING/SINGING_8HZ_8BIT.FLAC`|And that is all I know,|而我只知道这些。|
|同上|I know my mother,|我认得妈妈。|
|同上|I know, I know my pa.|我认得，我认得爸爸。|

共7个声音资源、10个cue。SINGING原时长6.662秒，字幕到5.34秒，后面保留原有回响；循环字幕应以clip原时长而非最后cue结束时间为周期。小模型有时将pa识为father，不改变中文爸爸的含义。歌词不被补写成已确认剧情人物的身份陈述。

## VAD漏检与完整性纠正

初次small+VAD对151 SFX的筛查漏掉短促的TALK03与SINGING，甚至广播末句误作Locate in your cell。因此没有把VAD空结果当作没有词句。

- TALK03：small/medium/large无VAD均恢复You are weak。
- SINGING：medium/large无VAD逐词恢复同一歌词；全量small无VAD也恢复其完整含义。
- 广播末句：medium/large及全量small无VAD一致为Locate the nearest stairwell，旧错误不作为译文保留。
- 随后对全部177轨无VAD扫描，所有新增非拟声词候选以及精确No哭喊对照继续large复核，覆盖计数与完成状态记录在locale的coverage字段，避免只凭最初几个候选封版。

## 为什么不把所有非空ASR写成字幕

以下是已实际观察到的负对照：

- `SFX/SE/BEEP2C_EDIT_11HZ_8BIT.FLAC`原始总时长仅0.073651秒，识别时间范围约0.04秒，却被small写成Thank you for watching，large写成Thank you。四词整句在此长度上不可能是可信时间对齐结果。
- 雷声、门锁、心跳、开火、上膛和切换声也反复触发Thank you/Thanks for watching；large甚至在FLINCH效果上生成Subtitles by the Amara.org community，或在音乐上生成transcript署名。这些是识别器样板幻觉，不是发现的游戏文本。
- MUSIC的small可能反复产生I don’t know what I’m talking about，而large对同源给出完全不同的Thanks for watching。没有稳定词句便不虚构歌词。
- ENEMYCL/LAUGH01三模型各给Yes, yes, Mark / Yes, that’s what I want / Yes, that’s right, I’m home，不能拿其中任意整句当剧情对白；保留笑声/处理人声分类。
- 喘息、死亡、退缩及咆哮的No/NOOO/AAARR/GRR等在模型间变化。将这类呼喊作为非词汇痛呼/怪物发声处理，不为每一次呻吟强加剧情字幕。

**已验证事实**是资源身份、完整执行的解码/扫描、各模型实际输出及时间范围。**高置信推断**是“该候选属于非词汇效果/识别幻觉而非可用剧情句”。分类不冒充人工听过每一音轨，也不将低概率潜在词强行包装成已翻译对白。

## WHISPER倒放与FLASHBACK关联

单独WHISPER原音产生互斥识别：medium One year of so many years、large I’m here to make it；倒放后两模型在无prompt条件下均给出**I am whispering now**。电影FLASHBACK在逆转、逆转+0.8速、逆转±3半音四类变体中，两模型也都恢复相同句子。

将WHISPER与FLASHBACK的mono16k PCM做归一化FFT互相关，峰在0.0/4.5045/9.009秒，系数约0.720757/0.422039/0.208264。支持同一处理人声重复混入电影的高置信推断，不是PCM字节相同，也不证明录音的制作背景。

因此WHISPER/FLASHBACK归类`processed-reversed-voice-effect`，保留原音；恢复句和解释性中文“我现在正在低声说话”只存metadata，不作为玩家实际听到的前向剧情台词烧录或overlay。详见`docs/MOVIE_AUDIO_AUDIT.md`。

## 复现方式

全量扫描不依赖一次性的私有候选清单。先用提交的原版清单和工具生成FLAC元数据/WAV，再直接`--all`：

```powershell
$game = "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward"
python -X utf8 tools/movie.py --archive "$game\rom.zar" --manifest build/phase1/archive-manifest.json --out build/full-research/movie-format --ffmpeg (Get-Command ffmpeg).Source --ffprobe (Get-Command ffprobe).Source
python -X utf8 tools/review_audio_sources.py --inventory build/full-research/movie-format/flac.json --model "C:\Users\noway\.cache\huggingface\hub\models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120" --out build/full-research/all-audio-small-novad-fixed --all --threads 8 --single-temperature
```

small筛查使用temperature0、beam5、max_new_tokens256、condition_on_previous_text=False、language=en、无VAD、无prompt。256为每个解码窗口的token上限，不是音频裁切；所有原始音频窗口仍被送入识别。原先默认多温度fallback在器乐上反复生成长串假设，首次慢筛只处理第一轨后被终止并改用上述固定配置；未将未完成旧筛宣称全量结果。

large复核使用本地large-v3 snapshot，可从已提交的locale逐项source_order_index/asr_review.large_checked重新构造`--only-indices`，或直接对所有177轨`--all`（成本更高）。medium/large定向审校及WHISPER反转可通过`--reverse-whisper`和`--only-indices`复现；`--vad`仅供重现VAD漏检对照，最终完整筛查不使用它。

全部模型均`local_files_only=True`、HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE开启，CPU int8，无外部ASR服务，无音频上传。模型snapshot与model.bin SHA-256和`docs/MOVIE_AUDIO_AUDIT.md`相同。

## 验收分层

音频解码通过、ASR覆盖完成、中文cue时间范围校验通过，不代表native overlay已经在游戏里验收。实际音频播放/停止/循环、暂停、切场、字幕位置/宽度与可读性由`docs/AUDIO_SUBTITLES.md`及后续用户手动验收记录负责；本项没有启动游戏。


## 最终覆盖与自动校验

全量small无VAD筛查177/177完成；逐项检查识别假设并将86个出现非拟声词/精确No呼喊的候选全部交large，另外包含既有短语音和效果对照，总计91个原始声音资源完成large复核，无待补的大模型词候选。26首MUSIC全部经无VAD扫描，其中所有含词假设的来源也经large复核；未发现应新增的稳定歌词。

最终仍为7个明确对白/歌词资源、10个播放cue。其余分类计数：26音乐无稳定词、74环境/机械非对白效果、60敌人非词汇发声或效果、3笑声/处理笑声、3痛呼、1幽灵处理人声、1合唱元音、1钢琴音、1倒放WHISPER。分类为高置信推断，原始声轨保持不动；既不把133条非空ASR当真对白，也不把小模型空结果当语音不存在的绝对证明。

字面校验结果：

`AUDIO REVIEW PASS full=177 SFX=151 MUSIC=26 lexical-candidates=86 large-reviewed=91 missing-large=0 dialogue-resources=7 cues=10`

locale的coverage记录`full_no_vad_small_complete=true`和`novel_lexical_candidate_large_review_complete=true`；每个clip记录source_order_index、small无VAD覆盖、large是否复核及分类理由。所有86候选均满足large_checked，源FLAC SHA-256与解码清单逐项一致。测试不依赖build下原始音频/研究报告，干净源码可读取locale并验证身份、cue范围及完整覆盖标志。
