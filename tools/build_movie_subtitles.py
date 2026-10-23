"""Guarded same-timeline VP9 caption rebuild, with independently regenerated DAT."""
from __future__ import annotations
import hashlib,json,math,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops
from fontTools.ttLib import TTFont
from movie import parse_ivf,rebuild_dat,probe_ivf_keyframes,validate_pair
from zar import digest,filehash,write_json


def caption_lines(text,font,width):
    result=[]
    for paragraph in text.split('\n'):
        if not paragraph:raise ValueError('Empty caption line')
        current=''
        for char in paragraph:
            if font.getlength(char)>width:raise ValueError('Caption glyph exceeds width')
            if current and font.getlength(current+char)>width:
                result.append(current);current=''
            current+=char
        result.append(current)
    if len(result)>3:raise ValueError('Caption exceeds three lines')
    return result


def render_caption(text,fontpath,size,anchor='bottom'):
    if not isinstance(text,str) or not text.strip() or '\0' in text:raise ValueError('Invalid caption')
    with TTFont(fontpath) as face:supported=set(face.getBestCmap())
    if {ord(c) for c in text if not c.isspace()}-supported:raise ValueError('Caption font coverage failure')
    font=ImageFont.truetype(str(fontpath),12)
    lines=caption_lines(text,font,size[0]-24)
    canvas=Image.new('RGBA',size)
    draw=ImageDraw.Draw(canvas);height=15*len(lines)
    if anchor not in ('top','bottom'):raise ValueError('Unsupported caption anchor')
    y=8 if anchor=='top' else size[1]-height-8
    for line in lines:
        box=draw.textbbox((0,0),line,font=font,stroke_width=1)
        x=(size[0]-(box[2]-box[0]))//2-box[0]
        draw.text((x,y-box[1]),line,font=font,fill='white',stroke_width=1,stroke_fill='black')
        y+=15
    box=canvas.getbbox()
    if box is None or box[0]<2 or box[2]>size[0]-2 or box[1]<2 or box[3]>size[1]-2:
        raise ValueError('Caption clips native video surface')
    return canvas,dict(lines=lines,ink_box=list(box),font_size=12)


def validate_cues(cues,duration):
    previous=0
    for cue in cues:
        if (not all(isinstance(cue[k],(int,float)) and math.isfinite(cue[k]) for k in ('start','end')) or
                not previous<=cue['start']<cue['end']<=duration or not cue['target']):
            raise ValueError('Invalid caption interval/text')
        if cue['status'] not in ('translated-asr-consensus','translated-high-confidence-deduction','translated-visual-reviewed'):
            raise ValueError('Unreviewed subtitle cue: '+cue['id'])
        previous=cue['end']


def decode_yuv(path,ffmpeg):
    return subprocess.run([ffmpeg,'-v','error','-xerror','-i',str(path),'-f','rawvideo','-pix_fmt','yuv420p','pipe:1'],
                          check=True,capture_output=True).stdout


def verify_caption_pixels(original,modified,video,cues,boxes,frame_regions=None):
    """Lossless YUV evidence: no-caption frames and pixels outside caption box stay exact."""
    w,h=video['width'],video['height']
    if w%2 or h%2:raise ValueError('Audited video requires even planar dimensions')
    frame_size=w*h*3//2
    if len(original)!=frame_size*video['count'] or len(modified)!=len(original):raise ValueError('Decoded video size mismatch')
    if frame_regions is not None and len(frame_regions)!=video['count']:raise ValueError('Title region timeline length mismatch')
    untouched=0;changed_frames=0
    for index,frame in enumerate(video['frames']):
        start=index*frame_size;a=original[start:start+frame_size];b=modified[start:start+frame_size]
        t=frame['timestamp']*video['scale']/video['rate']
        active=[box for cue,box in zip(cues,boxes) if cue['start']<=t<cue['end']]
        has_caption=bool(active)
        if frame_regions is not None:active+=frame_regions[index]
        if not active:
            if a!=b:raise ValueError('Frame without active caption changed')
            untouched+=1;continue
        # Chroma subsampling may touch the adjacent 2x2 sample; keep a bounded two-pixel guard.
        mask=bytearray(frame_size)
        for x0,y0,x1,y1 in active:
            x0=max(0,x0-2);x1=min(w,x1+2);y0=max(0,y0-2);y1=min(h,y1+2)
            for yy in range(y0,y1):mask[yy*w+x0:yy*w+x1]=b'\1'*(x1-x0)
            for plane in (w*h,w*h+w*h//4):
                for yy in range(y0//2,(y1+1)//2):
                    at=plane+yy*(w//2)+x0//2;n=(x1+1)//2-x0//2;mask[at:at+n]=b'\1'*n
        if any(x!=y and not allowed for x,y,allowed in zip(a,b,mask)):
            raise ValueError('Video pixels outside caption regions changed')
        if a==b and has_caption:raise ValueError('Active caption made no pixel change')
        if a!=b:changed_frames+=1
    return dict(no_caption_frames_byte_identical=untouched,caption_frames=changed_frames,
                outside_caption_yuv_preserved=True)


def build_movies(zar,config_path,fontpath,output):
    """Return outer IVF/DAT changes and report; OGG bytes are never rewritten."""
    config=json.loads(Path(config_path).read_text(encoding='utf-8'))
    if config.get('schema')!=1 or config.get('time_unit')!='seconds':raise ValueError('Unsupported subtitle config')
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise ValueError('ffmpeg and ffprobe required')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    annotations={}
    annotation_path=Path(config_path).parent/'movie-onscreen-text.json'
    if annotation_path.exists():
        annotations={r['movie']:r for r in json.loads(annotation_path.read_text(encoding='utf-8'))['movies']}
    titles={}
    title_path=Path(config_path).parent/'movie-titles.json'
    if title_path.exists():
        titles={r['resource']:r for r in json.loads(title_path.read_text(encoding='utf-8'))['titles']}
    changes={};reports=[]
    for row in config['movies']:
        name=row['resource'];base=name[:-4]
        raw_ogg=zar.read(name);raw_ivf=zar.read(base+'.IVF');raw_dat=zar.read(base+'.DAT')
        if digest(raw_ogg)!=row['sha256'] or digest(raw_ivf)!=row['ivf_sha256'] or digest(raw_dat)!=row['dat_sha256']:
            raise ValueError('Movie source identity mismatch')
        validate_pair(raw_dat,raw_ivf)
        onscreen=annotations.get(row['movie'],{})
        if onscreen and onscreen['ivf_sha256']!=row['ivf_sha256']:raise ValueError('Onscreen text video identity mismatch')
        dialogue=row['segments'];extra=onscreen.get('cues',[])
        validate_cues(dialogue,row['duration']);validate_cues(extra,row['duration'])
        cues=dialogue+extra
        title=titles.get(base+'.IVF')
        if not cues and title is None:continue
        video=parse_ivf(raw_ivf);work=output/row['movie'];work.mkdir(exist_ok=True)
        source=work/'original.ivf';source.write_bytes(raw_ivf)
        font=Path(fontpath);layouts=[];paths=[]
        for index,cue in enumerate(cues):
            caption,layout=render_caption(cue['target'],font,(video['width'],video['height']),
                                          'top' if index>=len(dialogue) else 'bottom')
            path=work/f'caption-{index:03d}.png';caption.save(path);paths.append(path)
            layouts.append(dict(id=cue['id'],start=cue['start'],end=cue['end'],**layout))
        frame_regions=None;title_frames=None
        if title:
            from build_movie_titles import rewrite_titles
            if digest(raw_ivf)!=title['source_sha256'] or video['count']!=title['frame_count']:
                raise ValueError('Movie title source identity mismatch')
            decoded=subprocess.run([ffmpeg,'-v','error','-xerror','-i',str(source),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],
                                   check=True,capture_output=True).stdout
            step=video['width']*video['height']*3
            if len(decoded)!=step*video['count']:raise ValueError('Movie title decoded frame length mismatch')
            title_frames=work/'title-%05d.png';frame_regions=[]
            for index in range(video['count']):
                original=Image.frombytes('RGB',(video['width'],video['height']),decoded[index*step:(index+1)*step])
                edited,regions=rewrite_titles(original,title,font,index)
                channels=ImageChops.difference(original,edited).split()
                mask=ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2]).point(lambda x:255 if x else 0)
                layer=edited.convert('RGBA');layer.putalpha(mask);layer.save(work/f'title-{index:05d}.png')
                frame_regions.append(regions)
                if index==video['count']//2:edited.save(work/'title-preview.png')
        filters=[];prior='0:v'
        for index,cue in enumerate(cues):
            label=f'v{index}'
            filters.append(f"[{prior}][{index+1}:v]overlay=0:0:format=yuv420:enable='gte(t,{cue['start']:.6f})*lt(t,{cue['end']:.6f})'[{label}]")
            prior=label
        if title_frames is not None:
            filters.append(f'[{prior}][{len(cues)+1}:v]overlay=0:0:format=yuv420[title]')
            prior='title'
        destination=work/'subtitled.ivf'
        command=[ffmpeg,'-hide_banner','-loglevel','error','-xerror','-y','-i',str(source)]
        for path in paths:command+=['-loop','1','-framerate',str(video['rate']/video['scale']),'-i',str(path)]
        if title_frames is not None:command+=['-framerate',str(video['rate']/video['scale']),'-i',str(title_frames)]
        command+=['-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map',f'[{prior}]',
            '-an','-frames:v',str(video['count']),'-c:v','libvpx-vp9','-lossless','1','-pix_fmt','yuv420p',
            '-threads','1','-row-mt','0','-tile-columns','0','-frame-parallel','0','-lag-in-frames','0','-auto-alt-ref','0',
            '-deadline','good','-cpu-used','4','-fps_mode','passthrough','-enc_time_base',f'{video["scale"]}:{video["rate"]}',
            '-fflags','+bitexact','-flags:v','+bitexact','-f','ivf',str(destination)]
        subprocess.run(command,capture_output=True,check=True)
        new_ivf=destination.read_bytes()
        flags=probe_ivf_keyframes(new_ivf,ffprobe)
        new_dat=rebuild_dat(raw_dat,raw_ivf,new_ivf,flags)
        pixels=verify_caption_pixels(decode_yuv(source,ffmpeg),decode_yuv(destination,ffmpeg),video,cues,[r['ink_box'] for r in layouts],frame_regions)
        changes[base+'.IVF']=new_ivf;changes[base+'.DAT']=new_dat
        for index,cue in enumerate(cues):
            # Native-resolution offline QA frame at midpoint; not an in-game screenshot.
            subprocess.run([ffmpeg,'-v','error','-y','-ss',str((cue['start']+cue['end'])/2),'-i',str(destination),
                '-frames:v','1',str(work/f'preview-{index:03d}.png')],capture_output=True,check=True)
        reports.append(dict(movie=row['movie'],frames=video['count'],source_ivf_sha256=digest(raw_ivf),
            modified_ivf_sha256=digest(new_ivf),modified_dat_sha256=digest(new_dat),ogg_unchanged=True,
            captions=layouts,dialogue_cue_count=len(dialogue),onscreen_cue_count=len(extra),
            localized_title=bool(title),command=command,exit_status=0,**pixels))
    return changes,dict(schema=1,movies=reports,movie_count=len(reports),cue_count=sum(len(r['captions']) for r in reports),
        title_movie_count=sum(r['localized_title'] for r in reports),
        dialogue_cue_count=sum(r['dialogue_cue_count'] for r in reports),
        onscreen_cue_count=sum(r['onscreen_cue_count'] for r in reports),
        ffmpeg_sha256=filehash(Path(ffmpeg)),ffprobe_sha256=filehash(Path(ffprobe)),font_sha256=filehash(Path(fontpath)),
        game_launched=False,verification='offline VP9 decode, same-timeline DAT and bounded caption YUV comparison')
