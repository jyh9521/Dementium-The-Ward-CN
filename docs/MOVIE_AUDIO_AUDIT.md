# 电影音轨与字幕离线审计

## 范围和交付

只读审计34组原版MOVIES OGG/IVF/DAT配对，对全部34个OGG运行已缓存的small与medium模型；对5组有语音候选的音轨再运行large-v3。未联网、未下载模型、未上传音频、未运行游戏、未修改Steam安装目录。中间OGG、mono16k WAV、原始ASR输出仅在忽略目录`build/full-research/movie-audio-{small,medium,large}/`。

结构化结果和中文翻译在`locales/zh-CN/movie-subtitles.json`，包括34条电影身份、OGG/IVF/DAT SHA-256、时长、PCM哈希、英文时间码、中文target、ASR来源及待确认状态。本项不烧录字幕、不修改音画；电影构建由单独工具处理。

## 已验证结果

- 34个OGG均经ffmpeg成功解码。small和medium扫描范围一致。
- 原始OGG容器SHA-256有34种，解码为单声道16k s16 PCM后只有19种。CHAPTER01至CHAPTER16的PCM逐字节相同，不能把容器哈希差异当作不同章节对白。
- 4组有三模型相互支持的可懂对白：BT_SIGHTING、FINAL、GENERATOR、NEWSCAST，整理18条中文字幕cue；其中GENERATOR:001经追加变体实验转为`translated-high-confidence-deduction`，与原音三模型一致的`translated-asr-consensus`区分，不当作已人工验证转写。
- FLASHBACK正放产生互不相容结果；追加逆转实验由两模型在四类逆转变体一致得到“I am whispering now”，现高置信归类反向处理人声效果，不当作前向可懂剧情对白，不强加字幕。
- 其余29组分类`no-intelligible-speech-detected`；这是两个模型未检出可懂对白，而不是证明绝无呼吸、尖叫、音效、歌唱或低清人声，也不是人工听校。

## 关键字幕与疑点

|电影|结果|状态|
|---|---|---|
|BT_SIGHTING|Mr. Redmoor, we meet at last. / It will all be over soon.|姓氏采large-v3 Redmoor，与《病房2》雷德穆尔一致；small/medium误写Redmore，音频不证明Latin拼写|
|FINAL|凌晨3:33，病人经历第一阶段手术存活；准备第二阶段|三个模型语义一致；large-v3将首词Let错配到0.08秒，其余词在20.94秒后，使用small/medium约20.52秒起始，需手动校时|
|GENERATOR|挑衅靠近、发现不是怪物同伙、被打断的结尾|中间3.32–4.72秒原音三模型错识近音词；large-v3在tempo1.2无候选词提示时准确给出“Freak, that’s right”，两模型慢放又支持freak，现标`translated-high-confidence-deduction`，不是已人工听校|
|NEWSCAST|30岁女子遭枪杀、武装嫌犯受伤、8岁女儿未受伤并可能目睹凶案、广告后继续|三模型语义一致；记者名Karina/Carina只影响Latin拼写，中文统一卡里娜·菲利普斯；新闻机构统一雷德穆尔新闻|
|FLASHBACK|small反复Here I see one there；medium I’m here, I’ve seen one；large Erepsilum|不能把正放互斥ASR当真实台词；逆转实验已高置信解释为反向人声样本，保留原音轨，不将反向恢复句强加为剧情字幕|

GENERATOR结尾只保留“Oh man, we’re gonna—”及中文“天哪，我们要——”，不采用small单独出现的fall来虚构“掉下去”等后文。

字幕用秒为时间单位，各电影cue按升序、不重叠、非空中文target且不超音轨时长。新闻长句按语义插入中文换行，未把ASR词时间机械等同最终画面排版。所有cue仍待人工听校与电影画面同步验收；不能将三模型一致描述成已人工验证。

## 没有新增原版字幕表的结论边界

OGG用于音频解码，18条字幕为本项目离线转写/翻译数据，不是提取出的官方原版字幕表。DAT虽有规则结构和无可打印正文，但本项未证明其每一字段含义；IVF画面烧录文字与独立章节标题由电影/图片审计合并判断。另外177个FLAC随后已完成全量无VAD筛查及全部新增词候选large复核，7个对白/歌词资源10cue详见`docs/AUDIO_SUBTITLE_AUDIT.md`；电影与非电影声音分开统计。

## 模型身份和离线约束

CPU int8、8 threads、language=en、beam_size=5、condition_on_previous_text=False、vad_filter=True、word_timestamps=True、local_files_only=True。工具显式设置HF_HUB_OFFLINE和TRANSFORMERS_OFFLINE。使用本地snapshot而不是在线模型别名。

|模型|snapshot|model.bin SHA-256|
|---|---|---|
|small|536b0662742c02347bc0e980a01041f333bce120|3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671|
|medium|08e178d48790749d25932bbc082711ddcfdfbc4f|9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae|
|large-v3|edaa852ec7e145841d8ffdb056a99866b5f0a478|69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1|

faster_whisper1.2.1；torch2.14.0+cpu（CUDA不可用）；ffmpeg9.0.2-full_build。模型是用户本地现有缓存，不随项目分发。

## 复现命令

```powershell
python -X utf8 tools/audit_movie_audio.py --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --out build/full-research/movie-audio-small --model "C:\Users\noway\.cache\huggingface\hub\models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120"
python -X utf8 tools/audit_movie_audio.py --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --out build/full-research/movie-audio-medium --model "C:\Users\noway\.cache\huggingface\hub\models--Systran--faster-whisper-medium\snapshots\08e178d48790749d25932bbc082711ddcfdfbc4f"
python -X utf8 tools/audit_movie_audio.py --game "C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward" --out build/full-research/movie-audio-large --model "C:\Users\noway\.cache\huggingface\hub\models--Systran--faster-whisper-large-v3\snapshots\edaa852ec7e145841d8ffdb056a99866b5f0a478" --only BT_SIGHTING,FINAL,FLASHBACK,GENERATOR,NEWSCAST
```

结果：small34/34、medium34/34、large5/5完成；small最初版本按OGG哈希去重报告unique-audio34，medium新版本按PCM去重为19；已在提交的locale清单明确记录19种PCM及章节复用，不混淆两类身份。ASR原始输出不是确定台词真值；离线整理与时间码边界选择记录在locale的notes。

## 待办门禁

1. GENERATOR:001按已记录的高置信推断保留，并在后续人工听校中复核；FLASHBACK作反向处理音效，不因恢复出录音句就添加剧情字幕。
2. 核对全部18cue的时间与画面，尤其FINAL首词ASR错配。
3. 已合并177个FLAC完整审计及7资源10cue，原始音轨保持不变，native overlay验收另记。
4. 电影构建保持帧率、帧数、音轨身份与DAT配对，再做离线格式/字幕可读性检查；这仍不替代游戏内验收。


## 追加：两处疑点的非破坏性变体实验

`tools/research_movie_voice.py`仅从build中的原始WAV读取，在`build/full-research/movie-voice-variants/`生成19个研究变体。FLASHBACK使用整段；GENERATOR使用原音2..7秒。方法包含原音、areverse、atempo0.8/1.2、保持时长的pitch±3半音、afftdn降噪及组合；FLASHBACK额外加入逆转+慢放、逆转±3半音。研究音频不进入游戏构建。

medium和large-v3均使用本地snapshot、CPU int8、英文、beam5、无VAD、condition_on_previous_text=False。FLASHBACK从不提供initial_prompt；GENERATOR只提供已知上下文“You want me? Come on over and get me. A little closer. Wait, you’re not one of them.”，没有向模型输入freak/that’s right等待确认词。

- **已验证的实验输出**：FLASHBACK逆转、逆转+0.8速、逆转±3半音在两个模型下均包含“I am whispering now”；正向处理持续产生互斥的近音乱码。因此“反向处理人声效果”是高置信推断，而非据原音识别出的剧情台词。恢复句及中文解释只存metadata，不作播放字幕。
- **已验证的实验输出**：GENERATOR的large-v3 tempo1.2给出“Come on over and get me. Freak, that’s right. A little closer.”；medium和large tempo0.8都含freak但后面误作I tried。结合原音free cat’s ride/three cats right等近音，采用“freak! That’s right.”为高置信推断，中文“怪物！对，就是这样。”，未冒充人工听校。
- **失败与偏差保留**：FLASHBACK正放会幻觉数字计数、One year of silver mania、I’m here等互斥句；GENERATOR逆转对照会回显提示里的not one of them，显示语境prompt可能造成幻觉。没有把这些失败输出删掉或用作确认依据；完整结果保留在本地voice-variants.json。
- **波形关联**：电影FLASHBACK与单独WHISPER176的单声道16k PCM做归一化FFT互相关，三个峰为lag0.0s/4.5045s/9.009s，对应cosine0.720757/0.422039/0.208264。支持同一处理人声在电影里重复混入的推断；不等于字节相同或证明全部混音来源。算法输出在whisper-correlation.json。

复现：

```powershell
python -X utf8 tools/research_movie_voice.py --out build/full-research/movie-voice-variants --medium "C:\Users\noway\.cache\huggingface\hub\models--Systran--faster-whisper-medium\snapshots\08e178d48790749d25932bbc082711ddcfdfbc4f" --large "C:\Users\noway\.cache\huggingface\hub\models--Systran--faster-whisper-large-v3\snapshots\edaa852ec7e145841d8ffdb056a99866b5f0a478"
```

这些是可复现的离线实验与推断分级，不是用户实机语音/画面验收。
