import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from art_delta import capture
from build_art import build_art,rebuild_mips,_validate_art
from engine_image import EngineImage,encode_frame
from texture import Texture


def fixture(mode='RGBA',prefix=b'ABCD',w=4,h=4,aw=6,ah=4,mips=3):
    fmt=0 if mode=='RGBA' else 1;bpp=4 if fmt==0 else 3
    count=sum(max(1,aw>>n)*max(1,ah>>n) for n in range(mips))
    pixels=bytes((i*17+5)%256 for i in range(count*bpp))
    head=struct.pack('<6H2I',fmt,mips,w,h,aw,ah,0x87654321,count)
    return prefix+head+struct.pack('<I',len(pixels))+encode_frame(encode_frame(pixels))


def original_image(resource):
    w,h,_=resource.levels[0]
    return Image.frombytes(resource.mode,(w,h),resource.level_pixels()).convert('RGBA')


class Archive:
    def __init__(self,raw):self.raw=raw
    def read(self,name):return self.raw


class BuildArtTests(unittest.TestCase):
    def test_source_preservation_contract_and_conflict(self):
        raw=b'preserved original';digest=hashlib.sha256(raw).hexdigest()
        entry=dict(scope='inner',resource='sample',source_sha256=digest,reason='unreadable')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'art-patches.json'
            config=dict(schema=1,patches=[],preserve_source=[entry])
            path.write_text(json.dumps(config),encoding='utf8')
            inner,outer,report=build_art(Archive(b''),Archive(raw),path)
            self.assertEqual((inner,outer),({},{}))
            self.assertEqual(report['preserved_sources'][0]['source_sha256'],digest)
            self.assertEqual(report['preserved_sources'][0]['disposition'],'original-resource-byte-identical')
            config['patches']=[dict(scope='inner',resource='sample',patch='art/sample.json')]
            path.write_text(json.dumps(config),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'conflicts'):build_art(Archive(b''),Archive(raw),path)
            config['patches']=[];entry['source_sha256']='0'*64
            path.write_text(json.dumps(config),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'source hash'):build_art(Archive(b''),Archive(raw),path)

    def test_locale_withdrawn_art_cannot_reenter_build(self):
        folder=Path(__file__).resolve().parents[1]/'locales/zh-CN'
        config=json.loads((folder/'art-patches.json').read_text(encoding='utf8'))
        protected={e['resource'] for e in config['preserve_source']}
        self.assertEqual(protected,{'3d/tex/notepad.tex','3d/tex/wboard02.tex'})
        self.assertFalse(protected & {e['resource'] for e in config['patches']})
        self.assertEqual(len(config['patches']),28)
        for name in ('notepad','wboard02'):
            self.assertFalse((folder/f'art/{name}.json').exists())

    def test_complete_mips_and_padding_alpha_metadata(self):
        raw=fixture();source=EngineImage(raw,4);edited=original_image(source)
        edited.putpixel((1,1),(255,32,18,edited.getpixel((1,1))[3]))
        encoded,report=rebuild_mips(source,edited);out=EngineImage(encoded,4)
        self.assertEqual(out.header,source.header);self.assertEqual(out.prefix,b'ABCD')
        self.assertTrue(report['all_mips_regenerated']);self.assertEqual(report['mip_levels'],3)
        self.assertEqual(out.level_pixels(),edited.tobytes())
        visible=set()
        for level,(w,h,offset) in enumerate(out.levels):
            expected=edited.resize((w,h),Image.Resampling.LANCZOS)
            old=Image.frombytes('RGBA',(w,h),source.level_pixels(level))
            expected.putalpha(old.getchannel('A'))
            self.assertEqual(out.level_pixels(level),expected.tobytes())
            self.assertEqual(Image.frombytes('RGBA',(w,h),out.level_pixels(level)).getchannel('A').tobytes(),old.getchannel('A').tobytes())
            stride=out.allocations[level][0]*out.bpp
            for y in range(h):visible.update(range(offset+y*stride,offset+y*stride+w*out.bpp))
        self.assertTrue(all(a==b for i,(a,b) in enumerate(zip(out.pixels,source.pixels)) if i not in visible))
        self.assertEqual(source.data,raw)

    def test_rgb_and_zero_prefix(self):
        source=EngineImage(fixture(mode='RGB',prefix=b''),0);edited=original_image(source)
        edited.putpixel((0,0),(255,255,255,255))
        result,report=rebuild_mips(source,edited);out=EngineImage(result,0)
        self.assertEqual(out.mode,'RGB');self.assertEqual(out.prefix,b'')
        self.assertEqual(out.level_pixels(),edited.convert('RGB').tobytes())
        self.assertTrue(report['all_mips_regenerated'])

    def test_noop_exact_binary(self):
        raw=fixture();source=EngineImage(raw,4)
        encoded,report=rebuild_mips(source,original_image(source))
        self.assertEqual(encoded,raw);self.assertTrue(report['noop_byte_identical'])

    def test_mipmap_wrong_alpha_mode_dimensions(self):
        source=EngineImage(fixture(),4);edited=original_image(source)
        bad=edited.copy();bad.putalpha(255)
        for value in [bad,edited.convert('RGB'),edited.resize((2,2))]:
            with self.assertRaises(ValueError):rebuild_mips(source,value)

    def _config(self,folder,raw,original,edited,scope='outer',prefix=0,regions=None):
        patch=capture(original,edited,resource='sample',prompt='synthetic fixture',regions=regions)
        path=Path(folder);(path/'art').mkdir(exist_ok=True)
        (path/'art/sample.json').write_text(json.dumps(patch),encoding='utf8')
        config=dict(schema=1,patches=[dict(scope=scope,resource='sample',source_sha256=hashlib.sha256(raw).hexdigest(),patch='art/sample.json',prefix_size=prefix)])
        (path/'art-patches.json').write_text(json.dumps(config),encoding='utf8')
        return path/'art-patches.json',config,patch

    def test_outer_build_and_native_verification(self):
        original=Image.new('RGBA',(6,4),(15,30,45,255));raw=Texture.encode(6,4,original.tobytes())
        edited=original.copy();edited.putpixel((1,1),(100,200,150,255))
        with tempfile.TemporaryDirectory() as folder:
            path,config,patch=self._config(folder,raw,original,edited,regions=[[1,1,2,2]])
            inner,outer,report=build_art(Archive(raw),Archive(b''),path)
            self.assertEqual(inner,{})
            self.assertEqual(Texture(outer['sample']).rgba,edited.tobytes())
            self.assertEqual(report['outer_count'],1)
            self.assertTrue(report['images'][0]['outside_reviewed_regions_unchanged'])
            self.assertEqual(build_art(Archive(raw),Archive(b''),path)[1],outer)

    def test_inner_build(self):
        raw=fixture();original=original_image(EngineImage(raw,4));edited=original.copy()
        edited.putpixel((0,0),(255,255,255,edited.getpixel((0,0))[3]))
        with tempfile.TemporaryDirectory() as folder:
            path,config,patch=self._config(folder,raw,original,edited,'inner',4)
            inner,outer,report=build_art(Archive(b''),Archive(raw),path)
            self.assertEqual(outer,{})
            self.assertEqual(EngineImage(inner['sample'],4).level_pixels(),edited.tobytes())
            self.assertTrue(report['images'][0]['all_mips_regenerated'])

    def test_reviewed_alpha_changes_only_projected_mip_rectangles(self):
        source=EngineImage(fixture(),4);edited=original_image(source)
        r,g,b,a=edited.getpixel((1,1));edited.putpixel((1,1),(r,g,b,a^255))
        encoded,report=rebuild_mips(source,edited,alpha_policy='reviewed-regions',regions=[[1,1,2,2]])
        out=EngineImage(encoded,4)
        self.assertEqual(out.level_pixels(),edited.tobytes())
        self.assertFalse(report['alpha_preserved'])
        for level,(w,h,offset) in enumerate(source.levels):
            old=Image.frombytes('RGBA',(w,h),source.level_pixels(level))
            new=Image.frombytes('RGBA',(w,h),out.level_pixels(level))
            boxes=report['mip_reviewed_regions'][level]
            for y in range(h):
                for x in range(w):
                    if not any(b[0]<=x<b[2] and b[1]<=y<b[3] for b in boxes):
                        self.assertEqual(new.getpixel((x,y)),old.getpixel((x,y)))

    def test_reviewed_alpha_outside_box_and_unknown_policy_rejected(self):
        source=EngineImage(fixture(),4);original=original_image(source);edited=original.copy()
        r,g,b,a=edited.getpixel((0,0));edited.putpixel((0,0),(r,g,b,a^255))
        with self.assertRaises(ValueError):rebuild_mips(source,edited,alpha_policy='reviewed-regions',regions=[[1,1,2,2]])
        with self.assertRaises(ValueError):rebuild_mips(source,edited,alpha_policy='preserve-source',regions=[[0,0,1,1]])
        with self.assertRaises(ValueError):_validate_art(original,original,dict(reviewed_regions=[[0,0,4,4]]),'unknown')

    def test_rgb_rejects_unrepresentable_transparency(self):
        source=EngineImage(fixture(mode='RGB',prefix=b''),0);edited=original_image(source)
        edited.putpixel((0,0),(12,34,56,0))
        with self.assertRaises(ValueError):rebuild_mips(source,edited,alpha_policy='reviewed-regions',regions=[[0,0,1,1]])

    def test_source_hash_and_resource_binding(self):
        original=Image.new('RGBA',(6,4),(15,30,45,255));raw=Texture.encode(6,4,original.tobytes());edited=original.copy()
        edited.putpixel((1,1),(100,200,150,255))
        with tempfile.TemporaryDirectory() as folder:
            path,config,patch=self._config(folder,raw,original,edited)
            config['patches'][0]['source_sha256']='0'*64
            path.write_text(json.dumps(config),encoding='utf8')
            with self.assertRaises(ValueError):build_art(Archive(raw),Archive(b''),path)
            config['patches'][0]['source_sha256']=hashlib.sha256(raw).hexdigest()
            path.write_text(json.dumps(config),encoding='utf8');patch['resource']='other'
            (Path(folder)/'art/sample.json').write_text(json.dumps(patch),encoding='utf8')
            with self.assertRaises(ValueError):build_art(Archive(raw),Archive(b''),path)

    def test_path_escape_duplicate_and_unknown_scope(self):
        original=Image.new('RGBA',(6,4),(15,30,45,255));raw=Texture.encode(6,4,original.tobytes())
        with tempfile.TemporaryDirectory() as folder:
            path,config,patch=self._config(folder,raw,original,original)
            for change in [dict(patch='../escape.json'),dict(scope='unknown'),dict(prefix_size=4)]:
                bad=copy.deepcopy(config);bad['patches'][0].update(change)
                path.write_text(json.dumps(bad),encoding='utf8')
                with self.assertRaises(ValueError):build_art(Archive(raw),Archive(b''),path)
            config['patches']*=2;path.write_text(json.dumps(config),encoding='utf8')
            with self.assertRaises(ValueError):build_art(Archive(raw),Archive(b''),path)

    def test_explicit_protected_artwork_pixels(self):
        original=Image.new('RGBA',(6,4),(15,30,45,255));edited=original.copy()
        edited.putpixel((1,1),(30,40,50,255))
        with self.assertRaises(ValueError):_validate_art(original,edited,dict(reviewed_regions=[[0,0,6,4]],protected_regions=[[1,1,2,2]]))
        self.assertEqual(_validate_art(original,edited,dict(reviewed_regions=[[0,0,6,4]],protected_regions=[[3,1,4,2]])),1)

    def test_review_regions_and_source_alpha(self):
        original=Image.new('RGBA',(6,4),(15,30,45,100));edited=original.copy()
        edited.putpixel((1,1),(30,40,50,100))
        for regions in [[[0,0,1,1]],[[-1,0,1,1]]]:
            with self.assertRaises(ValueError):_validate_art(original,edited,dict(reviewed_regions=regions))
        edited.putalpha(255)
        with self.assertRaises(ValueError):_validate_art(original,edited,dict(reviewed_regions=[[0,0,6,4]]))


if __name__=='__main__':unittest.main()
