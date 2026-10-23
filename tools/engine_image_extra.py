"""Read-only adapters for native Image format 5 (LA8) and 8 (L=A8).

No serializer or game execution is provided. Uninterpreted trailing bytes remain
in .tail; their presence does not establish an extra mip level.
"""
import hashlib,json,struct
from pathlib import Path
from engine_image import decode_frame

class ExtraImage:
    def __init__(self,data):
        self.data=bytes(data)
        if len(data)<36:raise ValueError('Truncated image')
        self.fields=struct.unpack_from('<6H2I',data)
        fmt,mips,w,h,aw,ah,opaque,count=self.fields
        if fmt not in (5,8) or not(1<=mips<=16 and 1<=w<=aw<=8192 and 1<=h<=ah<=8192):
            raise ValueError('Unsupported image layout')
        self.bpp={5:2,8:1}[fmt];self.width=w;self.height=h
        size=struct.unpack_from('<I',data,20)[0]
        self.raw=decode_frame(decode_frame(data[24:]))
        if len(self.raw)!=size or size<aw*ah*self.bpp:raise ValueError('Pixel payload bounds mismatch')
        if aw!=w or ah!=h:raise ValueError('Allocated dimensions require separate native audit')
        self.base=self.raw[:w*h*self.bpp];self.tail=self.raw[len(self.base):]
        self.rgba=b''.join(bytes((self.base[i],)*3+(self.base[i+1] if fmt==5 else self.base[i],))
                           for i in range(0,len(self.base),self.bpp))
    def rebuild(self):return self.data


def verify_native_conversion(exe,image):
    """Execute shipped F9340 conversion-loop bytes, not the game process/GPU."""
    import pefile
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_64
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_EAX,UC_X86_REG_RDX,UC_X86_REG_RBX,UC_X86_REG_RBP
    original=Path(exe).read_bytes()
    if hashlib.sha256(original).hexdigest()!='26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e':
        raise ValueError('Unsupported executable')
    p=pefile.PE(data=original);base=p.OPTIONAL_HEADER.ImageBase
    start,end=(0xf9768,0xf97bd) if image.fields[0]==5 else (0xf9635,0xf9679)
    code=p.get_data(start,end-start);p.close()
    u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(base+0xf9000,0x1000)
    u.mem_write(base+start,code)
    u.mem_map(0x30000000,0x200000);src=0x30000000;dst=0x30080000;frame=0x30180000
    if len(image.base)>0x80000 or len(image.rgba)>0x100000:raise ValueError('Replay image too large')
    u.mem_write(src,image.base);u.mem_write(frame+0x1f,struct.pack('<I',image.width*4))
    for reg,value in [(UC_X86_REG_ECX,image.height),(UC_X86_REG_EAX,image.width),(UC_X86_REG_RDX,dst),
                      (UC_X86_REG_RBX,src),(UC_X86_REG_RBP,frame)]:u.reg_write(reg,value)
    u.emu_start(base+start,base+end,count=2000000)
    actual=bytes(u.mem_read(dst,len(image.rgba)))
    if actual!=image.rgba:raise ValueError('Native conversion output differs')
    return dict(native_rva_start=hex(start),native_rva_end=hex(end),pixels=image.width*image.height,
                rgba_sha256=hashlib.sha256(actual).hexdigest(),match=True,game_launched=False,gpu_boundary_doubled=True)


def audit(game,out):
    from zar import Zar
    from content import Content
    from PIL import Image,ImageDraw
    game=Path(game).resolve();out=Path(out).resolve()
    root=Path(__file__).resolve().parents[1]
    if root/'build' not in out.parents or game in out.parents:raise ValueError('Output must remain in project build')
    out.mkdir(parents=True,exist_ok=True)
    from workspace_io import validate_output_tree
    validate_output_tree(out)
    z=Zar((game/'rom.zar').read_bytes());c=Content(z.read('CONTENT.TAR'));rows=[]
    for name in c.entries:
        if not name.endswith('.art'):continue
        data=c.read(name)
        if struct.unpack_from('<H',data)[0] not in (5,8):continue
        image=ExtraImage(data);index=len(rows);im=Image.frombytes('RGBA',(image.width,image.height),image.rgba)
        im.save(out/f'{index:02d}.png')
        sheet=Image.new('RGB',(800,280),(90,90,90));draw=ImageDraw.Draw(sheet)
        for j,bg in enumerate((0,90,220)):
            composite=Image.new('RGBA',im.size,(bg,bg,bg,255));composite.alpha_composite(im)
            composite=composite.convert('RGB');composite.thumbnail((250,230))
            factor=max(1,min(250//composite.width,230//composite.height))
            composite=composite.resize((composite.width*factor,composite.height*factor),Image.Resampling.NEAREST)
            sheet.paste(composite,(j*265,25));draw.text((j*265,5),name+' / '+str(bg),fill='white')
        sheet.save(out/f'{index:02d}-review.png')
        rows.append(dict(resource=name,sha256=hashlib.sha256(data).hexdigest(),fields=image.fields,
                         raw_size=len(image.raw),base_size=len(image.base),tail_size=len(image.tail),
                         noop_byte_identical=image.rebuild()==data,native=verify_native_conversion(game/'Dementium.exe',image)))
    (out/'report.json').write_text(json.dumps(dict(resources=rows),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(images=len(rows),native_match=all(r['native']['match'] for r in rows))))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--game',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();audit(a.game,a.out)
