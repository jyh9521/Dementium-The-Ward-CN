"""Local-only ASR review of previously extracted audio candidates; no game launch."""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def select_candidates(inventory,screen):
    """Include every nonempty screening result plus named short/processed voices."""
    candidates={r['resource'] for r in screen if r['segments']}
    candidates.update(r['resource'] for r in inventory if '/ENEMYBT/TALK' in r['resource'] or
                      any('/'+token+'/' in r['resource'] for token in ['WHISPER','SINGING','GHOSTLYREVERB']))
    return [r for r in inventory if r['resource'] in candidates]


def main():
    p=argparse.ArgumentParser();p.add_argument('--inventory',type=Path,required=True);p.add_argument('--screen',type=Path)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--exclude-indices',default='');p.add_argument('--reverse-whisper',action='store_true');p.add_argument('--all',action='store_true');p.add_argument('--threads',type=int,default=4);p.add_argument('--single-temperature',action='store_true');p.add_argument('--only-indices',default='');p.add_argument('--vad',action='store_true')
    a=p.parse_args();root=Path(__file__).resolve().parents[1];out=a.out.resolve()
    if root/'build' not in out.parents:raise ValueError('Output must remain under project build/')
    inv=json.loads(a.inventory.read_text(encoding='utf-8'))['flac']
    if not a.all and not a.screen:raise ValueError('Candidate mode requires --screen; --all needs only the original audio inventory')
    screen=json.loads(a.screen.read_text(encoding='utf-8'))['flac'] if a.screen else []
    rows=inv if a.all else select_candidates(inv,screen);excluded=set(a.exclude_indices.split(','))
    rows=[r for r in rows if str(int(Path(r['local_wav']).stem)) not in excluded]
    if a.only_indices:
        selected=set(a.only_indices.split(','));rows=[r for r in rows if str(int(Path(r['local_wav']).stem)) in selected]
    out.mkdir(parents=True,exist_ok=True)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from faster_whisper import WhisperModel
    model=WhisperModel(str(a.model),device='cpu',compute_type='int8',cpu_threads=a.threads,local_files_only=True)
    with (a.model/'model.bin').open('rb') as f:modelsha=hashlib.file_digest(f,'sha256').hexdigest()
    report=dict(model_snapshot=a.model.name,model_sha256=modelsha,local_files_only=True,device='cpu',compute_type='int8',
                vad_filter=a.vad,language='en',initial_prompt=None,full_inventory=a.all,single_temperature=a.single_temperature,max_new_tokens=256 if a.single_temperature else None,rows=[])
    for r in rows:
        path=Path(r['local_wav']);index=int(path.stem)
        jobs=[('original',path)]
        if a.reverse_whisper and '/WHISPER/' in r['resource']:
            rev=out/f'{index:03d}-reverse.wav'
            subprocess.run([shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y','-i',str(path),'-af','areverse',str(rev)],check=True)
            jobs.append(('reverse',rev))
        for variant,wav in jobs:
            options=dict(temperature=0.0,max_new_tokens=256) if a.single_temperature else {}
            segments,info=model.transcribe(str(wav),language='en',beam_size=5,condition_on_previous_text=False,vad_filter=a.vad,word_timestamps=True,**options)
            ss=[dict(start=s.start,end=s.end,text=s.text.strip(),avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,
                     words=[dict(word=w.word,start=w.start,end=w.end,probability=w.probability) for w in s.words or []]) for s in segments]
            row=dict(resource=r['resource'],sha256=r['sha256'],index=index,variant=variant,wav=str(wav),
                     wav_sha256=hashlib.sha256(wav.read_bytes()).hexdigest(),duration=r['duration'],segments=ss)
            report['rows'].append(row)
            (out/'asr.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(index,variant,[(s['start'],s['end'],s['text']) for s in ss],flush=True)
    print('AUDIO SOURCE REVIEW rows=%d' % len(report['rows']),flush=True)

if __name__=='__main__':main()
