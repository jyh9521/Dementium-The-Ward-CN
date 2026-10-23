"""Extract identity-bound original movie frames for offline visual-text review.

Samples first/middle/last decoded frames of every original IVF group; output
contains copyrighted original frames and must remain under ignored build/.
Successful frame decoding is not a claim about every unsampled movie frame.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

from movie import parse_ivf
from workspace_io import validate_output_tree


def sha(raw):return hashlib.sha256(raw).hexdigest()


def audit(archive,manifest,out,ffmpeg):
    root=Path(__file__).resolve().parents[1]
    archive=Path(archive).resolve();out=Path(out).resolve()
    if root/'build' not in out.parents or archive==out or archive in out.parents:
        raise ValueError('Original frame output must stay inside ignored project build/')
    out.mkdir(parents=True,exist_ok=True);validate_output_tree(out)
    selected=[r for r in manifest if r['name'].startswith('MOVIES/') and r['name'].endswith('.IVF')]
    if not selected:raise ValueError('No original movie groups')
    selected.sort(key=lambda row:row['name'])
    def one(pair):
        index,row=pair
        with archive.open('rb') as stream:
            stream.seek(row['offset']);raw=stream.read(row['size'])
        if len(raw)!=row['size'] or sha(raw)!=row['sha256']:
            raise ValueError('Original movie source identity mismatch')
        parsed=parse_ivf(raw);count=parsed['count']
        ids=sorted(set([0,count//2,count-1]))
        expression='+'.join('eq(n\\,'+str(n)+')' for n in ids)
        command=[str(ffmpeg),'-hide_banner','-loglevel','error','-xerror','-threads','1',
                 '-f','ivf','-i','pipe:0','-vf','select='+expression,
                 '-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
        process=subprocess.run(command,input=raw,capture_output=True)
        if process.returncode:raise ValueError('Original movie frame decode failed: '+row['name']+' '+process.stderr.decode(errors='replace'))
        stride=parsed['width']*parsed['height']*3
        if len(process.stdout)!=len(ids)*stride:
            raise ValueError('Selected frame output count/dimensions mismatch')
        frames=[]
        for pos,frame in enumerate(ids):
            pixels=process.stdout[pos*stride:(pos+1)*stride]
            path=out/f'{index:02d}-{frame:05d}.png'
            image=Image.frombytes('RGB',(parsed['width'],parsed['height']),pixels);image.save(path)
            frames.append(dict(frame=frame,timestamp=parsed['frames'][frame]['timestamp'],
                               seconds=parsed['frames'][frame]['timestamp']*parsed['scale']/parsed['rate'],
                               rgb_sha256=sha(pixels),local_png=str(path.relative_to(root))))
        return dict(index=index,resource=row['name'],source_sha256=row['sha256'],
                    original_frame_count=count,width=parsed['width'],height=parsed['height'],
                    selection='first/middle/last decoded frame indices',samples=frames,
                    decode_exit_status=process.returncode,decode_command=command)
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,enumerate(selected)))
    contacts=[]
    for start in range(0,len(rows),6):
        page=rows[start:start+6];sheet=Image.new('RGB',(1200,len(page)*267),(35,35,35));draw=ImageDraw.Draw(sheet)
        for n,row in enumerate(page):
            for j,frame in enumerate(row['samples']):
                image=Image.open(root/frame['local_png']).convert('RGB')
                if image.size!=(400,240):raise ValueError('Contact layout requires observed 400x240 movie frames')
                sheet.paste(image,(j*400,n*267))
                draw.text((j*400+2,n*267+241),f"{row['index']:02d} {row['resource'].split('/')[-1][:32]} f{frame['frame']} {frame['seconds']:.2f}s",fill='white')
        path=out/f'contact-{start//6:02d}.png';sheet.save(path);contacts.append(str(path.relative_to(root)))
    report=dict(schema=1,movie_groups=len(rows),selected_frames=sum(len(r['samples']) for r in rows),
                scope='original IVF first/middle/last visual samples; no re-encoding and no game execution',
                coverage_limit='does not exclude transient lettering in unsampled frames',movies=rows,contact_sheets=contacts)
    (out/'frames.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f"MOVIE FRAMES PASS groups={len(rows)} samples={report['selected_frames']} decode=0 dimensions=400x240 source=unchanged")
    return report


def audit_dense_resource(archive, manifest, name, output, ffmpeg, step_seconds=1.0):
    """Supplement a flagged movie with reproducible integer-second native frames."""
    root=Path(__file__).resolve().parents[1];output=Path(output).resolve()
    if root/'build' not in output.parents:raise ValueError('Dense frames must stay under build/')
    matches=[r for r in manifest if r['name']==name]
    if len(matches)!=1 or not name.endswith('.IVF'):raise ValueError('Dense resource identity absent or duplicate')
    row=matches[0]
    with Path(archive).open('rb') as stream:stream.seek(row['offset']);raw=stream.read(row['size'])
    if sha(raw)!=row['sha256']:raise ValueError('Dense movie source identity mismatch')
    parsed=parse_ivf(raw);step=round(step_seconds*parsed['rate']/parsed['scale'])
    if step<1:raise ValueError('Dense frame interval must be at least one frame')
    indices=list(range(0,parsed['count'],step))
    expression='+'.join('eq(n\\,'+str(n)+')' for n in indices)
    command=[str(ffmpeg),'-hide_banner','-loglevel','error','-xerror','-threads','1','-f','ivf','-i','pipe:0',
             '-vf','select='+expression,'-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    decoded=subprocess.run(command,input=raw,capture_output=True)
    if decoded.returncode:raise ValueError('Dense original frame decode failed')
    stride=parsed['width']*parsed['height']*3
    if len(decoded.stdout)!=stride*len(indices):raise ValueError('Dense frame count mismatch')
    output.mkdir(parents=True,exist_ok=True);validate_output_tree(output)
    samples=[]
    for i,index in enumerate(indices):
        pixels=decoded.stdout[i*stride:(i+1)*stride];path=output/f'{index:05d}.png'
        Image.frombytes('RGB',(parsed['width'],parsed['height']),pixels).save(path)
        samples.append(dict(frame=index,seconds=parsed['frames'][index]['timestamp']*parsed['scale']/parsed['rate'],
                            rgb_sha256=sha(pixels),local_png=str(path.relative_to(root))))
    contacts=[]
    for start in range(0,len(samples),12):
        batch=samples[start:start+12];sheet=Image.new('RGB',(1200,((len(batch)+2)//3)*260));draw=ImageDraw.Draw(sheet)
        for i,record in enumerate(batch):
            x=i%3*400;y=i//3*260
            sheet.paste(Image.open(root/record['local_png']).convert('RGB'),(x,y))
            draw.text((x+2,y+242),f"f{record['frame']} {record['seconds']:.2f}s",fill='white')
        path=output/f'contact-{start//12:02d}.png';sheet.save(path);contacts.append(str(path.relative_to(root)))
    report=dict(resource=name,source_sha256=row['sha256'],step_seconds=step_seconds,samples=samples,
                decode_exit_status=decoded.returncode,decode_command=command,contact_sheets=contacts)
    (output/'dense-frames.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('DENSE MOVIE FRAMES PASS samples='+str(len(samples))+' source='+name)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--manifest',default='assets/inspection/archive-manifest.json',type=Path)
    parser.add_argument('--out',default='build/full-research/movie-frames',type=Path)
    parser.add_argument('--ffmpeg',default='ffmpeg')
    parser.add_argument('--dense-resource',action='append',default=[])
    parser.add_argument('--dense-seconds',default=1.0,type=float)
    args=parser.parse_args();manifest=json.loads(args.manifest.read_text(encoding='utf8'))
    audit(args.archive,manifest,args.out,args.ffmpeg)
    for i,name in enumerate(args.dense_resource):
        audit_dense_resource(args.archive,manifest,name,args.out/('dense-'+str(i)),args.ffmpeg,args.dense_seconds)


if __name__=='__main__':main()
