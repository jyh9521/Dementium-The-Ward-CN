"""Local-only voice processing experiment. Processed audio never enters a game build."""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--medium',type=Path,required=True);p.add_argument('--large',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1];out=a.out.resolve()
    if root/'build' not in out.parents:raise ValueError('Output must remain under project build/')
    out.mkdir(parents=True,exist_ok=True)
    sources={'FLASHBACK':root/'build/full-research/movie-audio-medium/25.wav','GENERATOR':root/'build/full-research/movie-audio-medium/26.wav'}
    filters={'original':'anull','reverse':'areverse','tempo08':'atempo=0.8','tempo12':'atempo=1.2',
        'pitchminus3':'asetrate=13454.342644,aresample=16000,atempo=1.189207115',
        'pitchplus3':'asetrate=19027.31384,aresample=16000,atempo=0.840896415',
        'denoise':'afftdn=nf=-25','denoise_tempo08':'afftdn=nf=-25,atempo=0.8'}
    variants=[]
    for name,source in sources.items():
        for variant,af in filters.items():
            # Whole flashback; generator crop includes the requested 2..7 second span.
            crop='atrim=start=2:end=7,asetpts=PTS-STARTPTS,' if name=='GENERATOR' else ''
            path=out/(name+'-'+variant+'.wav')
            cmd=[shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y','-i',str(source),'-af',crop+af,'-ar','16000','-ac','1',str(path)]
            subprocess.run(cmd,check=True)
            variants.append(dict(movie=name,variant=variant,source=str(source.relative_to(root)),source_sha256=sha(source),
                crop_seconds=[2,7] if name=='GENERATOR' else None,filter=crop+af,wav=str(path.relative_to(root)),wav_sha256=sha(path),results={}))
        if name=='FLASHBACK':
            for variant,af in {'reverse_tempo08':'areverse,atempo=0.8','reverse_pitchminus3':'areverse,asetrate=13454.342644,aresample=16000,atempo=1.189207115',
                               'reverse_pitchplus3':'areverse,asetrate=19027.31384,aresample=16000,atempo=0.840896415'}.items():
                path=out/(name+'-'+variant+'.wav')
                subprocess.run([shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y','-i',str(source),'-af',af,'-ar','16000','-ac','1',str(path)],check=True)
                variants.append(dict(movie=name,variant=variant,source=str(source.relative_to(root)),source_sha256=sha(source),crop_seconds=None,filter=af,wav=str(path.relative_to(root)),wav_sha256=sha(path),results={}))
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from faster_whisper import WhisperModel
    report=dict(schema=1,experiment='non-destructive offline voice transformations; no processed audio in game output',
        context_policy='Only previously established surrounding dialogue, never the disputed candidate words.',models={},variants=variants)
    for modelname,modelpath in [('medium',a.medium),('large-v3',a.large)]:
        report['models'][modelname]=dict(snapshot=modelpath.name,model_sha256=sha(modelpath/'model.bin'),device='cpu',compute_type='int8',local_files_only=True)
        model=WhisperModel(str(modelpath),device='cpu',compute_type='int8',local_files_only=True,cpu_threads=8)
        for row in variants:
            prompt="You want me? Come on over and get me. A little closer. Wait, you're not one of them." if row['movie']=='GENERATOR' else None
            segments,info=model.transcribe(str(root/row['wav']),language='en',beam_size=5,condition_on_previous_text=False,vad_filter=False,initial_prompt=prompt,word_timestamps=True)
            result=[dict(start=s.start,end=s.end,text=s.text.strip(),avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,
                         words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in s.words or []]) for s in segments]
            row['results'][modelname]=dict(initial_prompt=prompt,language='en',vad_filter=False,segments=result)
            (out/'voice-variants.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(modelname,row['movie'],row['variant'],[(s['start'],s['end'],s['text']) for s in result],flush=True)
        del model;gc.collect()
    print('VOICE VARIANTS completed',len(variants),'models=2',flush=True)

if __name__=='__main__':main()
