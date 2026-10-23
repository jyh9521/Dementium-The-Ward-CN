"""Bounded codec for observed engine Image resources; no locale or game launch."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import zlib

MAX_RAW = 128 * 1024 * 1024


def decode_frame(data, maximum=MAX_RAW):
    if len(data)<12:raise ValueError('Truncated frame')
    usize,csize,aligned=struct.unpack_from('<3I',data)
    if usize>maximum or csize>MAX_RAW or aligned!=len(data) or aligned!=(12+csize+3)//4*4:
        raise ValueError('Frame bounds/alignment mismatch')
    stream=zlib.decompressobj()
    decoded=stream.decompress(data[12:12+csize],usize+1)
    if len(decoded)!=usize or not stream.eof or stream.unused_data or stream.unconsumed_tail:
        raise ValueError('Compressed stream boundary/size mismatch')
    if any(data[12+csize:]):raise ValueError('Nonzero alignment padding')
    return decoded


def encode_frame(data):
    if len(data)>MAX_RAW:raise ValueError('Frame too large')
    packed=zlib.compress(data,9)
    aligned=(12+len(packed)+3)//4*4
    return struct.pack('<3I',len(data),len(packed),aligned)+packed+b'\0'*(aligned-12-len(packed))


class EngineImage:
    def __init__(self,data,prefix_size=0):
        self.data=bytes(data)
        if prefix_size not in (0,4):raise ValueError('Unsupported prefix size')
        self.prefix_size=prefix_size
        if len(data)<prefix_size+36:raise ValueError('Truncated Image resource')
        self.prefix=data[:prefix_size]
        self.header=data[prefix_size:prefix_size+20]
        self.fields=struct.unpack('<6H2I',self.header)
        fmt,mips,w,h,aw,ah,opaque,count=self.fields
        if fmt not in (0,1):raise ValueError(f'Unknown pixel format {fmt}')
        if not (1<=mips<=16 and 1<=w<=8192 and 1<=h<=8192 and aw>=w and ah>=h):
            raise ValueError('Invalid dimensions/mipmap count')
        self.bpp={0:4,1:3}[fmt];self.mode={0:'RGBA',1:'RGB'}[fmt]
        self.levels=[];self.allocations=[];total=0
        for level in range(mips):
            lw,lh=max(1,w>>level),max(1,h>>level)
            allocw,alloch=max(1,aw>>level),max(1,ah>>level)
            self.levels.append((lw,lh,total*self.bpp))
            self.allocations.append((allocw,alloch))
            total+=allocw*alloch
        raw_size=struct.unpack_from('<I',data,prefix_size+20)[0]
        if count!=total or raw_size!=total*self.bpp or raw_size>MAX_RAW:
            raise ValueError('Pixel/mipmap payload length mismatch')
        self.raw_size=raw_size
        inner=decode_frame(data[prefix_size+24:])
        self.pixels=decode_frame(inner)
        if len(self.pixels)!=raw_size:raise ValueError('Raw size mismatch')

    def level_pixels(self,level=0):
        w,h,offset=self.levels[level]
        stride=self.allocations[level][0]*self.bpp
        return b''.join(self.pixels[offset+y*stride:offset+y*stride+w*self.bpp] for y in range(h))

    def rebuild(self):
        return self.data

    def write(self,pixels):
        """Replace all mip levels at unchanged dimensions; preserve every metadata byte."""
        pixels=bytes(pixels)
        if len(pixels)!=self.raw_size:raise ValueError('All original mipmap bytes required')
        if pixels==self.pixels:return self.data
        result=self.prefix+self.header+struct.pack('<I',len(pixels))+encode_frame(encode_frame(pixels))
        parsed=EngineImage(result,self.prefix_size)
        if parsed.fields!=self.fields or parsed.prefix!=self.prefix or parsed.pixels!=pixels:
            raise ValueError('Image serialization verification failed')
        return result


def audit(game,out,inventory):
    from collections import Counter
    from PIL import Image,ImageDraw
    from content import Content
    from zar import Zar,digest
    root=Path(__file__).resolve().parents[1]
    out=out.resolve();inventory=inventory.resolve()
    if root not in inventory.parents or game.resolve() in inventory.parents:
        raise ValueError('Inventory must remain under project workspace outside game input')
    prior={}
    if inventory.exists():
        previous=json.loads(inventory.read_text(encoding='utf-8'))
        prior={r['resource']:r for r in previous.get('resources',[])}
    if root/'build' not in out.parents or game.resolve() in out.parents:
        raise ValueError('Output must remain under project build/')
    profile=json.loads((root/'assets/game-profile.json').read_text(encoding='utf-8'))
    z=Zar((game/profile['archive']).read_bytes());c=Content(z.read(profile['content']))
    out.mkdir(parents=True,exist_ok=True)
    rows=[];previews=[]
    for name,e in c.entries.items():
        if not name.endswith(('.tex','.art')):continue
        data=c.read(name);index=len(rows)
        row=dict(index=index,resource=name,size=len(data),sha256=digest(data),status='unclassified',
                 prefix_size=4 if name.endswith('.tex') else 0,
                 header_fields=list(struct.unpack_from('<6H2I',data,4 if name.endswith('.tex') else 0)))
        try:
            image=EngineImage(data,4 if name.endswith('.tex') else 0)
            row.update(status='decoded',prefix_hex=image.prefix.hex(),fields=list(image.fields),
                       mip_levels=[list(x) for x in image.levels],mip_allocations=[list(x) for x in image.allocations],raw_size=image.raw_size,
                       noop_byte_identical=image.rebuild()==data)
            w,h,_=image.levels[0]
            preview=Image.frombytes(image.mode,(w,h),image.level_pixels()).convert('RGBA')
            path=out/f'{index:03d}.png';preview.save(path)
            row['preview_local']=path.relative_to(root).as_posix()
            previews.append((index,name,preview))
        except ValueError as err:row.update(status='unsupported',reason=str(err))
        old=prior.get(name,{})
        if old.get('sha256')==row['sha256']:
            for key in ['visual_review','text_segments','recommendation','notes','extra_native_base']:
                if key in old:row[key]=old[key]
        rows.append(row)
    for start in range(0,len(previews),36):
        sheet=Image.new('RGB',(1200,1200),(35,35,35));draw=ImageDraw.Draw(sheet)
        for pos,(index,name,im) in enumerate(previews[start:start+36]):
            x=(pos%6)*200;y=(pos//6)*200
            bg=Image.new('RGBA',im.size,(100,100,100,255));bg.alpha_composite(im)
            bg=bg.convert('RGB');bg.thumbnail((194,170))
            sheet.paste(bg,(x+(194-bg.width)//2,y))
            draw.text((x+2,y+172),str(index)+' '+Path(name).name[:24],fill='white')
        sheet.save(out/f'contact-{start//36:02d}.jpg',quality=90)
    inventory.parent.mkdir(parents=True,exist_ok=True)
    inventory.write_text(json.dumps(dict(schema=1,scope='CONTENT.TAR .tex/.art',resources=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('INNER IMAGES',dict(Counter(r['status'] for r in rows)),'total',len(rows),'contact-sheets',(len(previews)+35)//36)


def main():
    p=argparse.ArgumentParser();p.add_argument('--game',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--inventory',required=True,type=Path)
    a=p.parse_args();audit(a.game,a.out,a.inventory)

if __name__=='__main__':main()
