"""Native movie-title raster replacement; English-derived fade and pixel guards.

No movie encoding or timeline alteration occurs here. Recipes bind every decoded
RGB frame plus the input font. Only reviewed title masks can change; red scroll
ornaments and all other source pixels are copied verbatim.
"""
from __future__ import annotations
import hashlib
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont
from fontTools.ttLib import TTFont


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _rect(box, size):
    if (not isinstance(box,(list,tuple)) or len(box)!=4 or
        any(type(x) is not int for x in box) or
        not (0<=box[0]<box[2]<=size[0] and 0<=box[1]<box[3]<=size[1])):
        raise ValueError('Invalid native movie-title rectangle')
    return tuple(box)


@lru_cache(maxsize=8)
def _font(path, expected_hash):
    raw=Path(path).read_bytes()
    if sha(raw)!=expected_hash:raise ValueError('Movie-title font identity mismatch')
    with TTFont(path) as face:coverage=frozenset(face.getBestCmap())
    return ImageFont.truetype(path,12),coverage


def _mask(size, rects):
    result=Image.new('L',size)
    for box in rects:
        x0,y0,x1,y1=_rect(box,size)
        ImageDraw.Draw(result).rectangle((x0,y0,x1-1,y1-1),fill=255)
    return result


def _nonzero(image):
    r,g,b=image.split()
    return ImageChops.lighter(ImageChops.lighter(r,g),b).point(lambda x:255 if x else 0)


def rewrite_titles(original, recipe, fontpath, frame_index):
    """Return (edited RGB, allowed rectangles), preserving source-derived fade.

    Each source frame is hash locked. Erasure masks were identified from actual
    native decoded title pixels, not a 428px texture or guessed screen geometry.
    Original brightness is sampled at reviewed source English ink pixels before
    removal; separately sampled heading/subtitle fade controls Chinese ink.
    """
    if original.mode!='RGB' or list(original.size)!=recipe['size']:
        raise ValueError('Movie-title native frame format mismatch')
    if type(frame_index) is not int or not 0<=frame_index<len(recipe['frames']):
        raise ValueError('Movie-title frame index out of range')
    frame=recipe['frames'][frame_index]
    if sha(original.tobytes())!=frame['rgb_sha256']:
        raise ValueError('Movie-title source frame identity mismatch')
    mode=frame.get('mode','title')
    if mode=='unchanged':return original.copy(),[]
    if mode!='title':raise ValueError('Unsupported movie-title frame mode')
    font,coverage=_font(str(Path(fontpath).resolve()),recipe['font_sha256'])
    allowed=[list(_rect(b,original.size)) for b in recipe['allowed_regions']]
    allowed_mask=_mask(original.size,allowed)
    erasure=_mask(original.size,recipe['erase_runs'])
    if any(e and not a for e,a in zip(erasure.tobytes(),allowed_mask.tobytes())):
        raise ValueError('Movie-title erasure escapes reviewed regions')
    out=original.copy();out.paste((0,0,0),(0,0,*original.size),erasure)
    draw=ImageDraw.Draw(out)
    for label in recipe['labels']:
        text=label['target']
        if not text or {ord(c) for c in text}-coverage:
            raise ValueError('Movie-title font coverage failure')
        box=_rect(label['box'],original.size)
        ink=font.getbbox(text);w=ink[2]-ink[0];h=ink[3]-ink[1]
        if w>box[2]-box[0] or h>box[3]-box[1]:
            raise ValueError('Movie-title glyphs exceed native rectangle')
        samples=label['fade_samples']
        if not samples:raise ValueError('Movie-title fade samples absent')
        values=[]
        for x,y in samples:
            if not 0<=x<original.width or not 0<=y<original.height:
                raise ValueError('Invalid movie-title fade sample')
            values.append(original.getpixel((x,y))[label['fade_channel']])
        if (not isinstance(label['reference_brightness'],(int,float)) or not 0<label['reference_brightness']<=255):
            raise ValueError('Invalid movie-title reference brightness')
        brightness=sum(values)/len(values)
        strength=min(1.,brightness/label['reference_brightness'])
        color=tuple(round(c*strength) for c in label['color'])
        layer=Image.new('RGB',original.size)
        ld=ImageDraw.Draw(layer)
        position=((box[0]+box[2]-w)//2-ink[0],(box[1]+box[3]-h)//2-ink[1])
        ld.text(position,text,font=font,fill=color)
        actual=layer.getbbox()
        if actual:
            if not box[0]<=actual[0]<actual[2]<=box[2] or not box[1]<=actual[1]<actual[3]<=box[3]:
                raise ValueError('Movie-title output escapes reviewed region')
            glyph_mask=_nonzero(layer)
            if ImageChops.subtract(glyph_mask,allowed_mask).getbbox():
                raise ValueError('Movie-title output escapes reviewed region')
            out.paste(layer,(0,0),glyph_mask)
    changed=_nonzero(ImageChops.difference(original,out))
    if ImageChops.subtract(changed,allowed_mask).getbbox():
        raise ValueError('Movie-title outside-region pixels changed')
    # Decoration mask can intersect the review box near long English subtitles.
    for run in recipe.get('protected_runs',[]):
        box=_rect(run,original.size)
        if original.crop(box).tobytes()!=out.crop(box).tobytes():
            raise ValueError('Movie-title red decoration changed')
    return out,allowed


def verify_movies(zar, config, fontpath, output, ffmpeg='ffmpeg'):
    """Decode every original title frame and validate replacement offline."""
    import json,subprocess
    from movie import parse_ivf
    if config.get('schema')!=1:raise ValueError('Unsupported movie-title configuration')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    records=[];seen=set()
    for recipe in config['titles']:
        name=recipe['resource']
        if name in seen:raise ValueError('Duplicate movie-title resource')
        seen.add(name);raw=zar.read(name)
        if sha(raw)!=recipe['source_sha256']:raise ValueError('Movie-title IVF identity mismatch')
        meta=parse_ivf(raw)
        if [meta['width'],meta['height']]!=recipe['size'] or meta['count']!=recipe['frame_count'] or meta['count']!=len(recipe['frames']):
            raise ValueError('Movie-title IVF native geometry/timeline mismatch')
        command=[ffmpeg,'-v','error','-xerror','-threads','1','-f','ivf','-i','pipe:0','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
        decoded=subprocess.run(command,input=raw,check=True,capture_output=True).stdout
        stride=meta['width']*meta['height']*3
        if len(decoded)!=stride*meta['count']:raise ValueError('Movie-title decoded frame count mismatch')
        digest=hashlib.sha256();black=[];passthrough=0
        for i in range(meta['count']):
            source=Image.frombytes('RGB',tuple(recipe['size']),decoded[i*stride:(i+1)*stride])
            edited,regions=rewrite_titles(source,recipe,fontpath,i);digest.update(edited.tobytes())
            if recipe['frames'][i].get('mode','title')=='unchanged':
                if edited.tobytes()!=source.tobytes() or regions:raise ValueError('Movie-title passthrough changed')
                passthrough+=1
            if i in (0,meta['count']-1):black.append(max(edited.tobytes())==0)
            if i in (0,5,10,15,45,75,85,meta['count']-1):
                edited.save(output/(Path(name).name.split('.')[0]+f'-{i:02d}.png'))
        if recipe.get('require_first_last_black',True) and not all(black):raise ValueError('Movie-title black ending/start changed')
        records.append(dict(resource=name,frames=meta['count'],input_sha256=sha(raw),output_rgb_stream_sha256=digest.hexdigest(),outside_regions_unchanged=True,red_decorations_unchanged=True,first_last_black=all(black),passthrough_frames_byte_identical=passthrough,decode_exit=0,decode_command=command))
    report=dict(schema=1,movies=len(records),chapters=sum('/CHAPTER' in x['resource'] for x in records),frames=sum(x['frames'] for x in records),records=records,verification='offline RGB-frame validation; not in-game acceptance')
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report


if __name__=='__main__':
    import argparse,json
    from zar import Zar
    from font_source import resolve_fonts
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=Path('locales/zh-CN/movie-titles.json'))
    parser.add_argument('--output',type=Path,default=Path('build/full-research/movie-titles-verified'))
    args=parser.parse_args();config=json.loads(args.config.read_text(encoding='utf8'))
    font=resolve_fonts({'fonts':{'body':config['font']}})['body']
    report=verify_movies(Zar(args.archive.read_bytes()),config,font,args.output)
    print(f"MOVIE TITLES PASS movies={report['movies']} standalone-chapters={report['chapters']} frames={report['frames']} source=unchanged ornaments=unchanged outside-regions=unchanged")
