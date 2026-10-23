import copy,hashlib,sys,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_movie_titles import rewrite_titles,_nonzero
FONT=ImageFont.load_default(size=12)

def fixture(brightness=200):
    im=Image.new('RGB',(100,60));im.putpixel((3,3),(brightness,brightness,brightness));im.putpixel((2,40),(120,3,4))
    r=dict(size=[100,60],font_sha256='x',frames=[dict(rgb_sha256=hashlib.sha256(im.tobytes()).hexdigest())],allowed_regions=[[2,2,90,30]],erase_runs=[[2,2,5,5]],protected_runs=[[2,40,3,41]],labels=[dict(source='SOURCE',target='TEST',box=[20,10,80,27],fade_samples=[[3,3]],fade_channel=0,reference_brightness=200,color=[255,40,40])])
    return im,r

class MovieTitles(unittest.TestCase):
    def run_recipe(self,im,r,index=0):
        with patch('build_movie_titles._font',return_value=(FONT,set(range(128)))):
            return rewrite_titles(im,r,'unused',index)
    def test_replacement_and_outside_preserved(self):
        im,r=fixture();e,rects=self.run_recipe(im,r)
        self.assertEqual(rects,r['allowed_regions']);self.assertNotEqual(e.tobytes(),im.tobytes());self.assertEqual(e.getpixel((3,3)),(0,0,0));self.assertEqual(e.getpixel((2,40)),im.getpixel((2,40)))
        for y in range(im.height):
            for x in range(im.width):
                if not 2<=x<90 or not 2<=y<30:self.assertEqual(e.getpixel((x,y)),im.getpixel((x,y)))
    def test_fade_is_source_brightness_not_index(self):
        full,r=fixture();half,q=fixture(100);a,_=self.run_recipe(full,r);b,_=self.run_recipe(half,q)
        self.assertGreater(a.getextrema()[0][1],250);self.assertAlmostEqual(b.getextrema()[0][1],a.getextrema()[0][1]/2,delta=1)
    def test_black_source_stays_black(self):
        im,r=fixture(0);im.putpixel((2,40),(0,0,0));r['frames'][0]['rgb_sha256']=hashlib.sha256(im.tobytes()).hexdigest();out,_=self.run_recipe(im,r);self.assertEqual(max(out.tobytes()),0)
    def test_unknown_frame_rejected(self):
        im,r=fixture();im.putpixel((99,59),(1,0,0))
        with self.assertRaisesRegex(ValueError,'identity'):self.run_recipe(im,r)
    def test_bad_dimensions_and_index(self):
        im,r=fixture()
        with self.assertRaises(ValueError):self.run_recipe(im.convert('RGBA'),r)
        with self.assertRaises(ValueError):self.run_recipe(im,r,1)
    def test_erasure_escape_rejected(self):
        im,r=fixture();r['erase_runs']=[[99,59,100,60]]
        with self.assertRaisesRegex(ValueError,'escapes'):self.run_recipe(im,r)
    def test_text_overflow_rejected(self):
        im,r=fixture();r['labels'][0]['target']='TEST'*20
        with self.assertRaisesRegex(ValueError,'exceed'):self.run_recipe(im,r)
    def test_unsupported_glyph_rejected(self):
        im,r=fixture();r['labels'][0]['target']='游戏'
        with self.assertRaisesRegex(ValueError,'coverage'):self.run_recipe(im,r)
    def test_protected_region_rejected(self):
        im,r=fixture();r['protected_runs']=[[2,2,5,5]]
        with self.assertRaisesRegex(ValueError,'decoration'):self.run_recipe(im,r)
    def test_single_bit_red_is_not_rounded_away(self):
        im=Image.new('RGB',(1,1),(1,0,0));self.assertEqual(_nonzero(im).getpixel((0,0)),255)
    def test_unchanged_mode_is_exact_copy_with_no_regions(self):
        im,r=fixture();r['frames'][0]['mode']='unchanged'
        # No glyph/font/rectangle interpretation is needed for passthrough.
        r['labels']=[];r['allowed_regions']=[]
        out,regions=self.run_recipe(im,r)
        self.assertIsNot(out,im);self.assertEqual(out.tobytes(),im.tobytes());self.assertEqual(regions,[])
    def test_unknown_mode_fails(self):
        im,r=fixture();r['frames'][0]['mode']='mystery'
        with self.assertRaisesRegex(ValueError,'mode'):self.run_recipe(im,r)
    def test_unchanged_mode_still_requires_original_identity(self):
        im,r=fixture();r['frames'][0]['mode']='unchanged';im.putpixel((99,59),(3,4,5))
        with self.assertRaisesRegex(ValueError,'identity'):self.run_recipe(im,r)
    def test_bad_rectangle_rejected(self):
        im,r=fixture();r['allowed_regions']=[[0,0,101,20]]
        with self.assertRaisesRegex(ValueError,'rectangle'):self.run_recipe(im,r)

if __name__=='__main__':unittest.main()
