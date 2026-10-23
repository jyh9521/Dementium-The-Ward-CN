"""Y-axis legend layout and exact-pixel icon relocation regressions."""
import json
from pathlib import Path
import sys
import unittest
from PIL import Image,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_image_text import render_recipe,raster_label
from font_source import resolve_fonts

class IconRelocationTests(unittest.TestCase):
    def fixture(self):
        image=Image.new('RGBA',(48,32))
        image.paste((20,50,90,255),(2,2,8,8))
        recipe=dict(resource='fixture',size=[48,32],allowed_regions=[[0,0,48,32]],
                    labels=[dict(source='label',target='A',box=[25,5,45,25])],
                    relocations=[dict(source_box=[2,2,8,8],destination_box=[2,3,8,9])])
        return image,recipe
    def test_exact_icon_pixels_relocated(self):
        image,recipe=self.fixture()
        result,report=render_recipe(image,recipe,lambda size:ImageFont.load_default())
        self.assertEqual(result.crop((2,3,8,9)).tobytes(),image.crop((2,2,8,8)).tobytes())
        self.assertEqual(result.getpixel((2,2)),(0,0,0,0))
        self.assertTrue(report['relocations'][0]['pixels_preserved'])
    def test_relocation_rejects_protected_or_outside_or_resize(self):
        for change in [dict(protected_regions=[[2,2,8,9]]),dict(allowed_regions=[[25,0,48,32]])]:
            image,recipe=self.fixture();recipe.update(change)
            with self.assertRaises(ValueError):render_recipe(image,recipe,lambda size:ImageFont.load_default())
        image,recipe=self.fixture();recipe['relocations'][0]['destination_box']=[2,3,9,9]
        with self.assertRaises(ValueError):render_recipe(image,recipe,lambda size:ImageFont.load_default())
    def test_label_cannot_cover_relocated_icon(self):
        image,recipe=self.fixture();recipe['relocations'][0]['destination_box']=[29,12,35,18]
        with self.assertRaisesRegex(ValueError,'relocated'):
            render_recipe(image,recipe,lambda size:ImageFont.load_default())

class YAxisLayoutTests(unittest.TestCase):
    def test_all_devices_colon_gap_and_shared_ink_center(self):
        config=json.loads((ROOT/'locales/zh-CN/image-text.json').read_text(encoding='utf-8'))
        recipes=[r for r in config['images'] if r['resource'].endswith('_YAXIS.PNG')]
        self.assertEqual(len(recipes),4)
        path=resolve_fonts({'fonts':{'body':config['font']}})['body']
        font=ImageFont.truetype(str(path),12)
        for recipe in recipes:
            with self.subTest(resource=recipe['resource']):
                label=recipe['labels'][0]
                self.assertEqual(label['target'],'纵轴：')
                move=recipe['relocations'][0];dest=move['destination_box']
                ink=raster_label(label,font);x0,y0,x1,y1=label['box']
                top=y0+(y1-y0-ink.height)//2
                # Original C2C7F..C2C9D gives state origin (125,220).
                # Appended binfont ink begins +3 and ends +14; texture x origin -68.
                self.assertEqual((top,top+ink.height),(223,234))
                self.assertEqual(dest[1]+dest[3],223+234)
                self.assertGreaterEqual(x0-dest[2],6)
                self.assertGreaterEqual(193-(x0+ink.width),4)
if __name__=='__main__':unittest.main()
