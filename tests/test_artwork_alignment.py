import copy
import json
from pathlib import Path
import sys
import unittest

from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from art_delta import capture,sha
from center_artwork import center_box,center_artwork,verify_alignment
from paired_artwork import lighting_variant

ROOT=Path(__file__).resolve().parents[1]


class ArtworkAlignmentTests(unittest.TestCase):
    def test_native_integer_centering_parities(self):
        for w in range(1,20):
            for h in range(1,12):
                box=center_box((w,h),[3,2,24,16])
                self.assertLessEqual(abs((box[0]+box[2]-27)/2),.5)
                self.assertLessEqual(abs((box[1]+box[3]-18)/2),.5)
        with self.assertRaises(ValueError):center_box((30,2),[0,0,20,10])

    def test_moves_painted_pixels_not_crop_padding(self):
        original=Image.new('RGBA',(24,16),(100,20,20,177))
        painted=original.copy()
        for x in range(5,10):
            for y in range(3,8):painted.putpixel((x,y),(220,210,180,177))
        base=capture(original,painted,resource='fixture',prompt='fixture',regions=[[2,2,22,14]])
        labels=[dict(text='fixture',clear=[2,2,22,14],search=[2,2,22,14],frame=[0,0,24,16],palette='ivory')]
        patch,edited=center_artwork(original,base,original,labels,'plate-sha')
        self.assertEqual(verify_alignment(edited,patch),1)
        self.assertEqual(edited.getchannel('A').tobytes(),original.getchannel('A').tobytes())
        self.assertEqual(patch['alignment']['labels'][0]['ink_box'],[9,5,14,10])
        bad=copy.deepcopy(patch);bad['alignment']['labels'][0]['ink_box'][0]+=2
        with self.assertRaisesRegex(ValueError,'not centered'):verify_alignment(edited,bad)
        edited.putpixel((12,8),(0,0,0,177))
        with self.assertRaisesRegex(ValueError,'pixels changed'):verify_alignment(edited,patch)

    def test_all_reviewed_framed_labels_have_center_evidence(self):
        labels=[]
        for p in (ROOT/'locales/zh-CN/art').glob('*.json'):
            labels+=json.loads(p.read_text('utf8')).get('alignment',{}).get('labels',[])
        self.assertEqual(len(labels),43)
        for row in labels:
            frame=row['frame_box'];ink=row['ink_box']
            self.assertLessEqual(abs((ink[0]+ink[2]-frame[0]-frame[2])/2),.5,row['text'])
            self.assertLessEqual(abs((ink[1]+ink[3]-frame[1]-frame[3])/2),.5,row['text'])

    def test_death_pair_is_one_artwork_and_lighting_only(self):
        a=json.loads((ROOT/'locales/zh-CN/art/death.json').read_text('utf8'))['pair']
        b=json.loads((ROOT/'locales/zh-CN/art/death2.json').read_text('utf8'))['pair']
        self.assertEqual(a['top_text'],'你已咽下')
        self.assertEqual(a['bottom_text'],'最后一口气')
        self.assertEqual(a['canonical_pixels_sha256'],b['canonical_pixels_sha256'])
        self.assertFalse(a['independent_redraw']);self.assertFalse(b['independent_redraw'])
        im=Image.new('RGBA',(8,6),(0,0,0,255));im.putpixel((3,2),(220,210,190,255))
        altered,mask=lighting_variant(im,[0,0,8,6],[.94,.77,.8])
        self.assertEqual(mask.getbbox(),(3,2,4,3))
        self.assertEqual(altered.getbbox(),im.getbbox())
        self.assertNotEqual(altered.getpixel((3,2)),im.getpixel((3,2)))
        self.assertEqual(altered.getpixel((2,2)),im.getpixel((2,2)))


if __name__=='__main__':unittest.main()
