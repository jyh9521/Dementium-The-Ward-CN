"""Sparse native RGB movie overlays, without movie encoding or media replacement.

The compiler decodes supported original VP9 IVF using FFmpeg's default rgb24
conversion (the same source-frame SHA256-bound conversion as title recipes).
Its RGB triples replace RGB channels immediately before the native RGBA upload;
alpha stays native. Timing selects the decoded IVF frame timestamp, not wall time.
Generated layer bytes contain only changed pixels and belong under ignored build/.
"""
from __future__ import annotations
import hashlib,json,re,shutil,struct,subprocess
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw
from build_movie_subtitles import render_caption,validate_cues
from build_movie_titles import rewrite_titles
from movie import parse_ivf,validate_pair
from zar import digest,filehash,write_json


def sparse_runs(original, edited, force_mask=None):
    """Return canonical horizontal (linear pixel offset, RGB bytes) runs."""
    if original.mode!='RGB' or edited.mode!='RGB' or original.size!=edited.size:
        raise ValueError('RGB layer geometry mismatch')
    channels=ImageChops.difference(original,edited).split()
    mask=ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2])
    if force_mask is not None:
        if force_mask.mode!='L' or force_mask.size!=original.size:raise ValueError('Sparse force-mask geometry mismatch')
        mask=ImageChops.lighter(mask,force_mask)
    box=mask.getbbox()
    if box is None:return []
    w,h=original.size;out=[]
    for y in range(box[1],box[3]):
        row=mask.crop((box[0],y,box[2],y+1)).tobytes()
        colors=edited.crop((box[0],y,box[2],y+1)).tobytes()
        x=0
        while x<len(row):
            if not row[x]:x+=1;continue
            start=x
            while x<len(row) and row[x]:x+=1
            out.append((y*w+box[0]+start,colors[start*3:x*3]))
    return out


def apply_runs(rgba, size, runs):
    """Independent upload oracle: reject invalid runs; never touch alpha."""
    w,h=size
    if len(rgba)!=w*h*4:raise ValueError('RGBA size mismatch')
    out=bytearray(rgba);previous=-1
    for offset,rgb in runs:
        if (type(offset) is not int or not isinstance(rgb,bytes) or not rgb or len(rgb)%3 or
            offset<0 or offset+len(rgb)//3>w*h or offset<previous or
            offset//w!=(offset+len(rgb)//3-1)//w):
            raise ValueError('Invalid sparse RGB run')
        previous=offset+len(rgb)//3
        for i in range(len(rgb)//3):out[(offset+i)*4:(offset+i)*4+3]=rgb[i*3:i*3+3]
    return bytes(out)


def frame_at_timestamp(frames,timestamp):
    """Exact decoded-frame lookup. A stale/unknown timestamp never paints."""
    import bisect
    times=[f['timestamp'] for f in frames]
    index=bisect.bisect_left(times,timestamp)
    return index if index<len(times) and times[index]==timestamp else None


def compile_movie(raw_ivf, movie, title, cues, fontpath, ffmpeg='ffmpeg', preview=None):
    if not isinstance(movie,str) or not re.fullmatch(r'[A-Z0-9_]+',movie):raise ValueError('Unsafe movie key')
    meta=parse_ivf(raw_ivf);size=(meta['width'],meta['height'])
    if size!=(400,240):raise ValueError('Unsupported native movie upload geometry')
    if title and (digest(raw_ivf)!=title['source_sha256'] or list(size)!=title['size'] or
                  meta['count']!=title['frame_count'] or len(title['frames'])!=meta['count']):
        raise ValueError('Movie title source identity mismatch')
    command=[str(ffmpeg),'-v','error','-xerror','-threads','1','-f','ivf','-i','pipe:0','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    decoded=subprocess.run(command,input=raw_ivf,capture_output=True,check=True).stdout
    stride=size[0]*size[1]*3
    if len(decoded)!=stride*meta['count']:raise ValueError('Decoded native movie frame count mismatch')
    captions=[]
    for cue,anchor in cues:
        canvas,layout=render_caption(cue['target'],fontpath,size,anchor)
        captions.append((cue,canvas,layout))
    layers=[];layer_ids={};frames=[];active_counts={c['id']:0 for c,_ in cues};changed=0;output_hash=hashlib.sha256()
    test_alpha=bytes(i%251 for i in range(size[0]*size[1]))
    for index,frame in enumerate(meta['frames']):
        source=Image.frombytes('RGB',size,decoded[index*stride:(index+1)*stride])
        edited,regions=rewrite_titles(source,title,fontpath,index) if title else (source.copy(),[])
        force_mask=Image.new('L',size)
        if title and title['frames'][index].get('mode','title')=='title':
            draw=ImageDraw.Draw(force_mask)
            for x0,y0,x1,y1 in title['erase_runs']:draw.rectangle((x0,y0,x1-1,y1-1),fill=255)
        t=frame['timestamp']*meta['scale']/meta['rate'];active=[]
        for cue,canvas,layout in captions:
            if cue['start']<=t<cue['end']:
                edited=Image.alpha_composite(edited.convert('RGBA'),canvas).convert('RGB')
                force_mask=ImageChops.lighter(force_mask,canvas.getchannel('A'))
                active_counts[cue['id']]+=1;active.append(cue['id'])
        runs=sparse_runs(source,edited,force_mask)
        key=b''.join(struct.pack('<II',offset,len(rgb))+rgb for offset,rgb in runs)
        if key not in layer_ids:layer_ids[key]=len(layers);layers.append(runs)
        layer_id=layer_ids[key];frames.append(dict(timestamp=frame['timestamp'],layer_id=layer_id))
        changed+=bool(runs);output_hash.update(edited.tobytes())
        # Vary alpha per pixel; exact RGB reconstruction AND alpha preservation.
        rgba=bytearray(source.convert('RGBA').tobytes());rgba[3::4]=test_alpha
        applied=apply_runs(bytes(rgba),size,runs)
        check=Image.frombytes('RGBA',size,applied)
        if check.convert('RGB').tobytes()!=edited.tobytes() or applied[3::4]!=rgba[3::4]:
            raise ValueError('Sparse upload pixel or alpha roundtrip mismatch')
        if preview and (index in (0,5,10,45,75,meta['count']-1) or
                        any(active_counts[c]==1 for c in active)):
            edited.save(Path(preview)/(movie+f'-{index:05d}.png'))
            source.save(Path(preview)/(movie+f'-{index:05d}-source.png'))
    if any(not count for count in active_counts.values()):raise ValueError('Caption cue has no decoded frame')
    return dict(resource='MOVIES/'+movie+'.IVF',source_sha256=digest(raw_ivf),width=size[0],height=size[1],
                rate=meta['rate'],scale=meta['scale'],frames=frames,layers=layers),dict(
        movie=movie,frames=meta['count'],changed_frames=changed,unique_layers=len(layers),
        changed_pixels=sum(len(rgb)//3 for runs in layers for _,rgb in runs),
        cues=[dict(id=cue['id'],anchor=anchor,frames=active_counts[cue['id']]) for cue,anchor in cues],
        title=bool(title),passthrough_frames=meta['count']-changed,
        mask_policy='RGB difference union complete active title erase_runs union nonzero caption alpha; native alpha retained',output_rgb_sha256=output_hash.hexdigest(),
        decode_command=command,decode_exit=0,rgba_roundtrip='exact RGB; arbitrary alpha preserved')


def compile_layers(zar,config_path,fontpath,output,ffmpeg=None):
    """Compile identity-guarded catalogs; return (movie structures, report)."""
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    config_path=Path(config_path);raw=config_path.read_bytes();config=json.loads(raw)
    if config.get('schema')!=1 or config.get('time_unit')!='seconds':raise ValueError('Unsupported subtitle config')
    annotation_path=config_path.with_name('movie-onscreen-text.json');title_path=config_path.with_name('movie-titles.json')
    annotation_raw=annotation_path.read_bytes();title_raw=title_path.read_bytes()
    annotation_config=json.loads(annotation_raw);title_config=json.loads(title_raw)
    if annotation_config.get('schema')!=1 or title_config.get('schema')!=1:raise ValueError('Unsupported movie auxiliary catalog')
    def unique(rows,key):
        out={}
        for row in rows:
            if row[key] in out:raise ValueError('Duplicate movie catalog resource')
            out[row[key]]=row
        return out
    annotations=unique(annotation_config['movies'],'movie');titles=unique(title_config['titles'],'resource')
    unique(config['movies'],'movie');unique(config['movies'],'resource')
    if filehash(Path(fontpath))!=title_config['font']['sha256']:raise ValueError('Movie overlay font identity mismatch')
    ffmpeg=ffmpeg or shutil.which('ffmpeg')
    if not ffmpeg:raise ValueError('ffmpeg required for native movie layer compilation')
    movies=[];reports=[];seen_titles=set();seen_annotations=set();sources=[]
    for row in config['movies']:
        name=row['resource']
        if name!='MOVIES/'+row['movie']+'.AVI.REFORMATTED.AVI.OGG':raise ValueError('Movie catalog resource/key mismatch')
        base=name[:-4];ivf=zar.read(base+'.IVF');dat=zar.read(base+'.DAT');ogg=zar.read(name)
        if digest(ivf)!=row['ivf_sha256'] or digest(dat)!=row['dat_sha256'] or digest(ogg)!=row['sha256']:
            raise ValueError('Movie source identity mismatch')
        validate_pair(dat,ivf)
        sources.append(dict(movie=row['movie'],ivf_sha256=digest(ivf),dat_sha256=digest(dat),ogg_sha256=digest(ogg)))
        annotation=annotations.get(row['movie']);title=titles.get(base+'.IVF')
        extra=[]
        if annotation:
            seen_annotations.add(row['movie']);extra=annotation['cues']
            if annotation['ivf_sha256']!=row['ivf_sha256']:raise ValueError('Onscreen video identity mismatch')
        if title:seen_titles.add(base+'.IVF')
        validate_cues(row['segments'],row['duration']);validate_cues(extra,row['duration'])
        cues=[(c,'bottom') for c in row['segments']]+[(c,'top') for c in extra]
        if len({c['id'] for c,_ in cues})!=len(cues):raise ValueError('Duplicate caption ID')
        if not title and not cues:continue
        compiled,report=compile_movie(ivf,row['movie'],title,cues,fontpath,ffmpeg,output)
        compiled['resource']=base+'.IVF'
        movies.append(compiled);reports.append(report)
        print('LAYER MOVIE '+row['movie']+' frames='+str(report['frames']),flush=True)
    if set(titles)!=seen_titles or set(annotations)!=seen_annotations:raise ValueError('Orphan movie title/annotation catalog')
    report=dict(schema=1,catalog_sha256={config_path.name:digest(raw),annotation_path.name:digest(annotation_raw),title_path.name:digest(title_raw)},
        font_sha256=filehash(Path(fontpath)),ffmpeg_sha256=filehash(Path(ffmpeg)),sources=sources,movies=reports,
        movie_count=len(movies),dialogue_cue_count=sum(len(r['segments']) for r in config['movies']),
        onscreen_cue_count=sum(len(r['cues']) for r in annotations.values()),title_movie_count=len(titles),
        frames=sum(len(m['frames']) for m in movies),
        decoded_source_frames=sum(len(m['frames']) for m in movies),
        mask_policy='complete title erasure even original black; all caption nonzero alpha; no title passthrough mask',
        original_media_preserved=True,video_reencoded=False,game_launched=False)
    write_json(output/'layers-report.json',report)
    frames=[dict(stem=m['resource'].split('/')[-1][:-4]+'.DAT',width=m['width'],height=m['height'],
                 start=(f['timestamp']-.5)*m['scale']/m['rate'],
                 end=(f['timestamp']+.5)*m['scale']/m['rate'],
                 timestamp=f['timestamp'],frame_index=i,rate=m['rate'],scale=m['scale'],
                 runs=[(offset*4,rgb) for offset,rgb in m['layers'][f['layer_id']]])
            for m in movies for i,f in enumerate(m['frames']) if m['layers'][f['layer_id']]]
    return frames,report
