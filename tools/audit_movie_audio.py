"""Offline audio extraction and local-only ASR research; never launches game."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import wave
from zar import Zar,digest


def main():
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--only',default='')
    a=p.parse_args();root=Path(__file__).resolve().parents[1];out=a.out.resolve();game=a.game.resolve()
    if root/'build' not in out.parents or game in out.parents:raise ValueError('Output must remain under project build/')
    if not (a.model/'model.bin').is_file():raise ValueError('Complete local model snapshot required')
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise ValueError('ffmpeg/ffprobe required')
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    from faster_whisper import WhisperModel
    model=WhisperModel(str(a.model.resolve()),device='cpu',compute_type='int8',local_files_only=True,cpu_threads=8)
    z=Zar((game/'rom.zar').read_bytes());out.mkdir(parents=True,exist_ok=True)
    model_sha=hashlib.file_digest((a.model/'model.bin').open('rb'),'sha256').hexdigest()
    rows=[];cache={};pcm_cache={}
    for n in z.entries:
        if not n.endswith('.OGG') or (a.only and not any(token in n for token in a.only.split(','))):continue
        data=z.read(n);sha=digest(data);base=n[:-4]
        row=dict(resource=n,sha256=sha,size=len(data),ivf_sha256=digest(z.read(base+'.IVF')),dat_sha256=digest(z.read(base+'.DAT')))
        if sha in cache:
            row.update(duplicate_of=cache[sha]['resource'],duration=cache[sha]['duration'],segments=cache[sha]['segments'])
        else:
            ogg=out/f'{len(rows):02d}.ogg';wav=out/f'{len(rows):02d}.wav';ogg.write_bytes(data)
            subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(ogg),'-ac','1','-ar','16000',str(wav)],check=True)
            duration=float(subprocess.check_output([ffprobe,'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(wav)],text=True).strip())
            with wave.open(str(wav),'rb') as pcm:
                pcm_hash=digest(pcm.readframes(pcm.getnframes()))
            if pcm_hash in pcm_cache:
                row.update(duration=duration,pcm_sha256=pcm_hash,pcm_duplicate_of=pcm_cache[pcm_hash]['resource'],segments=pcm_cache[pcm_hash]['segments'],local_wav=wav.relative_to(root).as_posix())
                rows.append(row)
                print(n,'duration',duration,'PCM duplicate',row['pcm_duplicate_of'],flush=True)
                continue
            segments,info=model.transcribe(str(wav),language='en',beam_size=5,condition_on_previous_text=False,vad_filter=True,word_timestamps=True)
            result=[dict(start=s.start,end=s.end,text=s.text.strip(),avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,compression_ratio=s.compression_ratio,
                         words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in (s.words or [])]) for s in segments]
            row.update(duration=duration,pcm_sha256=pcm_hash,segments=result,local_wav=wav.relative_to(root).as_posix(),duration_after_vad=info.duration_after_vad)
            cache[sha]=row;pcm_cache[pcm_hash]=row
        rows.append(row)
        report=dict(schema=1,asr=dict(model_directory=str(a.model.resolve()),model_sha256=model_sha,device='cpu',compute_type='int8',local_files_only=True,language='en',beam_size=5,condition_on_previous_text=False,vad_filter=True,word_timestamps=True),movies=rows)
        (out/'asr.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(n,'duration',row['duration'],'segments',len(row['segments']),'duplicate',row.get('duplicate_of',''),flush=True)
    if not rows:raise ValueError('No matching movie audio resources')
    report['movies']=rows
    (out/'asr.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('MOVIE AUDIO AUDIT movies=%d unique-pcm=%d' % (len(rows),len(pcm_cache)),flush=True)

if __name__=='__main__':main()
