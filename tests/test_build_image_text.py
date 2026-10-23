import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageFont

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_image_text import checked_box, raster_label, render_recipe, build_images
from texture import Texture


FONT=ImageFont.load_default()


def recipe():
    return dict(resource='UI/LABEL',size=[48,24],allowed_regions=[[20,0,48,24]],
                clear_regions=[dict(box=[20,0,48,24],color=[0,0,0,0])],
                labels=[dict(source='Old',target='New',box=[20,0,48,24])],
                protected_regions=[[0,0,20,24]])


class Face:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def getBestCmap(self):return {n:'glyph' for n in range(32,127)}


class ImagesTests(unittest.TestCase):
    def test_native_dimensions_and_outside_pixels(self):
        original=Image.new('RGBA',(48,24),(10,20,30,180))
        r=recipe();result,report=render_recipe(original,r,lambda size:FONT)
        self.assertEqual(result.size,original.size)
        self.assertEqual(result.crop((0,0,20,24)).tobytes(),original.crop((0,0,20,24)).tobytes())
        self.assertTrue(report['outside_regions_unchanged'])
        self.assertTrue(report['protected_regions_unchanged'])
        self.assertGreater(report['changed_pixels'],0)
        self.assertEqual(original.getpixel((24,1)),(10,20,30,180))

    def test_deterministic_raster(self):
        original=Image.new('RGBA',(48,24),(10,20,30,180))
        self.assertEqual(render_recipe(original,recipe(),lambda size:FONT)[0].tobytes(),
                         render_recipe(original,recipe(),lambda size:FONT)[0].tobytes())

    def test_reject_clear_outside_allowed(self):
        r=recipe();r['clear_regions'][0]['box']=[0,0,48,24]
        with self.assertRaises(ValueError):render_recipe(Image.new('RGBA',(48,24)),r,lambda size:FONT)

    def test_reject_label_outside_allowed(self):
        r=recipe();r['labels'][0]['box']=[0,0,48,24]
        with self.assertRaises(ValueError):render_recipe(Image.new('RGBA',(48,24)),r,lambda size:FONT)

    def test_reject_clipped_ink(self):
        r=recipe();r['labels'][0]['target']='OVERFLOWING LABEL'
        with self.assertRaises(ValueError):render_recipe(Image.new('RGBA',(48,24)),r,lambda size:FONT)

    def test_reject_protected_input_overlap(self):
        r=recipe();r['protected_regions']=[[0,0,48,24]]
        with self.assertRaises(ValueError):render_recipe(Image.new('RGBA',(48,24)),r,lambda size:FONT)

    def test_reject_label_overlap(self):
        r=recipe();r['labels']*=2
        with self.assertRaises(ValueError):render_recipe(Image.new('RGBA',(48,24)),r,lambda size:FONT)

    def test_neutral_erase_preserves_red_ornament(self):
        r=recipe();r['clear_regions'][0]['ink']='neutral'
        original=Image.new('RGBA',(48,24),(70,70,70,255));original.putpixel((21,1),(255,0,0,255))
        result,report=render_recipe(original,r,lambda size:FONT)
        self.assertEqual(result.getpixel((21,1)),original.getpixel((21,1)))
        self.assertEqual(result.getpixel((22,1)),(0,0,0,0))

    def test_bad_boxes_and_sizes(self):
        for box in [[-1,0,2,2],[0,0,49,2],[0,0,0,1],[0,0,1],[0,0,1.0,2]]:
            with self.assertRaises(ValueError):checked_box(box,(48,24))
        with self.assertRaises(ValueError):render_recipe(Image.new('RGBA',(47,24)),recipe(),lambda size:FONT)
        for text in ['', 'A\n\nB']:
            with self.assertRaises(ValueError):raster_label(dict(target=text),FONT)

    def test_encoded_build_and_font_hash(self):
        raw=Texture.encode(48,24,Image.new('RGBA',(48,24),(10,20,30,180)).tobytes())
        class Archive:
            def read(self,name):return raw
        r=recipe();r.update(source_sha256=hashlib.sha256(raw).hexdigest(),header_words=[122,32])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'font.ttf';path.write_bytes(b'font input fixture')
            config=dict(schema=1,font=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest()),images=[r])
            with patch('build_image_text.TTFont',return_value=Face()),patch('build_image_text.ImageFont.truetype',return_value=FONT):
                result,report=build_images(Archive(),config,path)
                modified=Texture(result['UI/LABEL'])
                self.assertEqual((modified.width,modified.height),(48,24))
                self.assertEqual(modified.rgba[:20*4],Texture(raw).rgba[:20*4])
                self.assertEqual(report['image_count'],1)
                config['font']['sha256']='0'*64
                with self.assertRaises(ValueError):build_images(Archive(),config,path)

    def test_source_hash_binding_and_missing_glyph(self):
        raw=Texture.encode(48,24,Image.new('RGBA',(48,24),(10,20,30,180)).tobytes())
        class Archive:
            def read(self,name):return raw
        r=recipe();r.update(source_sha256='0'*64,header_words=[122,32])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'font.ttf';path.write_bytes(b'fixture')
            config=dict(schema=1,font=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest()),images=[r])
            with patch('build_image_text.TTFont',return_value=Face()),patch('build_image_text.ImageFont.truetype',return_value=FONT):
                with self.assertRaises(ValueError):build_images(Archive(),config,path)
                r['labels'][0]['target']='缺字'
                with self.assertRaises(ValueError):build_images(Archive(),config,path)

    def test_project_recipe_scope(self):
        config=json.loads((Path(__file__).resolve().parents[1]/'locales/zh-CN/image-text.json').read_text(encoding='utf8'))
        names=[r['resource'] for r in config['images']]
        self.assertEqual(len(names),49)
        self.assertEqual(len(set(names)),49)
        self.assertEqual(len(config['deferred_images']),3)
        self.assertFalse(any('/HUD/' in n or n=='TEXTURES/MAP/BG.PNG' for n in names))
        for r in config['images']:
            self.assertEqual(len(r['source_sha256']),64)
            for box in r['allowed_regions']+r['protected_regions']:
                checked_box(box,r['size'])
            if '/CONTROLS_' in r['resource']:
                self.assertFalse(any(l['source'] in ('Jump','Crouch') for l in r['labels']))


if __name__=='__main__':unittest.main()
