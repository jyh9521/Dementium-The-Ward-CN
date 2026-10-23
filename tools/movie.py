"""Audited IVF/DAT pairing and offline media inventory; never runs the game."""
from __future__ import annotations
import argparse,hashlib,json,math,struct,subprocess,wave
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

KEYFRAME=1<<63
OFFSET_MASK=KEYFRAME-1

def sha(data):return hashlib.sha256(data).hexdigest()

def parse_ivf(data):
    if len(data)<32:raise ValueError('Truncated IVF header')
    magic,version,header,codec,width,height,rate,scale,count,reserved=struct.unpack_from('<4sHH4sHHIIII',data)
    if magic!=b'DKIF' or version!=0 or header!=32 or codec!=b'VP90' or not width or not height or not rate or not scale or reserved:
        raise ValueError('Unsupported audited IVF variant')
    frames=[];offset=32;previous=-1
    while offset<len(data):
        if offset+12>len(data):raise ValueError('Truncated IVF frame header')
        size,timestamp=struct.unpack_from('<IQ',data,offset)
        if not 0<size<=0x10000000 or offset+12+size>len(data) or timestamp<=previous:
            raise ValueError('Invalid IVF frame bounds/timestamps')
        frames.append(dict(offset=offset,size=size,timestamp=timestamp))
        previous=timestamp;offset+=12+size
    if len(frames)!=count or not frames:raise ValueError('IVF frame count mismatch')
    return dict(codec=codec.decode(),width=width,height=height,rate=rate,scale=scale,count=count,frames=frames)


def parse_dat(data):
    if len(data)<24:raise ValueError('Truncated DAT header')
    version,count,maximum,fps=struct.unpack_from('<IIQd',data)
    if version!=1 or not count or len(data)!=24+24*count or not math.isfinite(fps) or fps<=0:
        raise ValueError('Unsupported DAT header/frame count')
    frames=[];previous=-1.0
    for i in range(count):
        time,flagged,size=struct.unpack_from('<dQQ',data,24+i*24)
        if not math.isfinite(time) or time<0 or time<=previous or not size or size>0x10000000:
            raise ValueError('Invalid DAT frame record')
        frames.append(dict(time=time,offset=flagged&OFFSET_MASK,keyframe=bool(flagged&KEYFRAME),size=size))
        previous=time
    if maximum!=max(f['size'] for f in frames) or not frames[0]['keyframe']:
        raise ValueError('DAT maximum/keyframe guard mismatch')
    return dict(version=version,count=count,max_frame_size=maximum,fps=fps,frames=frames)


def validate_pair(dat,ivf):
    table=parse_dat(dat);video=parse_ivf(ivf)
    if table['count']!=video['count'] or table['fps']!=video['rate']/video['scale']:
        raise ValueError('DAT/IVF count or frame rate mismatch')
    for a,b in zip(table['frames'],video['frames']):
        if a['offset']!=b['offset'] or a['size']!=b['size'] or abs(a['time']-b['timestamp']*video['scale']/video['rate'])>0.00000051:
            raise ValueError('DAT/IVF frame offset/size/time mismatch')
    return dict(frames=video['count'],codec=video['codec'],width=video['width'],height=video['height'],
        rate=video['rate'],scale=video['scale'],max_frame_size=table['max_frame_size'],
        keyframes=sum(f['keyframe'] for f in table['frames']),dat_sha256=sha(dat),ivf_sha256=sha(ivf))


def rebuild_dat(original_dat,original_ivf,new_ivf,keyframes):
    """Synchronize an independently encoded same-timeline IVF. No encoding/burn-in.

    keyframes must come from an independent VP9 decoder/probe for the new file;
    GOP flags are not copied from the original after re-encoding.
    """
    validate_pair(original_dat,original_ivf)
    old=parse_ivf(original_ivf);new=parse_ivf(new_ivf);flags=list(keyframes)
    if any(old[k]!=new[k] for k in ('codec','width','height','rate','scale','count')):
        raise ValueError('Re-encoding changed codec, dimensions or timeline')
    if [f['timestamp'] for f in old['frames']]!=[f['timestamp'] for f in new['frames']]:
        raise ValueError('Re-encoding changed frame timestamps')
    if len(flags)!=new['count'] or any(type(x) is not bool for x in flags) or not flags[0]:
        raise ValueError('Independent keyframe flags required')
    out=bytearray(original_dat)
    struct.pack_into('<Q',out,8,max(f['size'] for f in new['frames']))
    for i,(frame,key) in enumerate(zip(new['frames'],flags)):
        struct.pack_into('<QQ',out,24+i*24+8,frame['offset']|(KEYFRAME if key else 0),frame['size'])
    validate_pair(bytes(out),new_ivf)
    return bytes(out)



def probe_ivf_keyframes(ivf,ffprobe):
    """Use the independent codec parser, checking packet count/size/PTS alignment."""
    parsed=parse_ivf(ivf)
    p=subprocess.run([str(ffprobe),'-v','error','-f','ivf','-show_packets',
        '-show_entries','packet=pts,size,flags','-of','json','pipe:0'],input=ivf,capture_output=True)
    if p.returncode:raise ValueError('IVF codec probe failed: '+p.stderr.decode(errors='replace'))
    packets=json.loads(p.stdout)['packets']
    if len(packets)!=parsed['count']:raise ValueError('IVF codec packet count differs')
    flags=[]
    for packet,frame in zip(packets,parsed['frames']):
        if int(packet['size'])!=frame['size'] or int(packet['pts'])!=frame['timestamp']:
            raise ValueError('IVF codec parser packet alignment differs')
        flags.append('K' in packet['flags'])
    return flags


def audit_movies(archive,manifest):
    members={r['name']:r for r in manifest};result=[]
    with Path(archive).open('rb') as f:
        for name,r in members.items():
            if not name.endswith('.DAT') or not name.startswith('MOVIES/'):continue
            companion=members[name[:-4]+'.IVF'];f.seek(r['offset']);dat=f.read(r['size'])
            f.seek(companion['offset']);ivf=f.read(companion['size'])
            if sha(dat)!=r['sha256'] or sha(ivf)!=companion['sha256']:raise ValueError('Archive member identity mismatch')
            report=validate_pair(dat,ivf)
            if rebuild_dat(dat,ivf,ivf,[x['keyframe'] for x in parse_dat(dat)['frames']])!=dat:
                raise ValueError('DAT no-op roundtrip mismatch')
            result.append(dict(resource=name,**report,noop_identical=True))
    return result


def audit_flac(archive,manifest,out,ffmpeg,ffprobe):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    selected=[r for r in manifest if r['name'].endswith('.FLAC')]
    def one(pair):
        index,row=pair
        with Path(archive).open('rb') as f:f.seek(row['offset']);data=f.read(row['size'])
        if sha(data)!=row['sha256'] or not data.startswith(b'fLaC'):raise ValueError('FLAC source guard mismatch')
        source=out/f'{index:03d}.flac';wav=out/f'{index:03d}.wav';source.write_bytes(data)
        p=subprocess.run([str(ffprobe),'-v','error','-show_streams','-show_format','-of','json',str(source)],capture_output=True,text=True,check=True)
        info=json.loads(p.stdout);streams=info['streams']
        if len(streams)!=1 or streams[0]['codec_name']!='flac':raise ValueError('Unexpected FLAC stream')
        decoded=subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-xerror','-threads','1','-y','-i',str(source),'-ac','1','-ar','16000',str(wav)],capture_output=True,text=True)
        if decoded.returncode:raise ValueError('FLAC decode failed: '+row['name']+' '+decoded.stderr)
        with wave.open(str(wav),'rb') as pcm:
            frames=pcm.getnframes();raw=pcm.readframes(frames)
        return dict(resource=row['name'],sha256=row['sha256'],size=row['size'],
            duration=float(info['format']['duration']),sample_rate=int(streams[0]['sample_rate']),
            channels=streams[0]['channels'],decode_exit_status=decoded.returncode,
            canonical_pcm_sha256=sha(raw),canonical_samples=frames,local_wav=str(wav.resolve()),
            speech_status='unreviewed; successful decode does not establish speech absence')
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,enumerate(selected)))
    return dict(schema=1,flac=rows,files=len(rows),decode_all_passed=True,game_launched=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--ffmpeg',type=Path);p.add_argument('--ffprobe',type=Path)
    a=p.parse_args();root=Path(__file__).resolve().parents[1];out=a.out.resolve()
    if root/'build' not in out.parents:raise ValueError('Audit output must be inside project build/')
    manifest=json.loads(a.manifest.read_text(encoding='utf-8'));out.mkdir(parents=True,exist_ok=True)
    movies=audit_movies(a.archive,manifest);(out/'movies.json').write_text(json.dumps(movies,indent=2),encoding='utf-8')
    print('MOVIES PASS',len(movies),'paired DAT/IVF byte-identical no-op')
    if a.ffmpeg and a.ffprobe:
        report=audit_flac(a.archive,manifest,out/'flac',a.ffmpeg,a.ffprobe)
        (out/'flac.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('FLAC PASS',report['files'],'decoded')

if __name__=='__main__':main()
