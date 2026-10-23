import pathlib,sys,unittest
from PIL import ImageFont
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from build_movie_subtitles import caption_lines,validate_cues,verify_caption_pixels

class CaptionTests(unittest.TestCase):
    def test_caption_wrapping_is_lossless(self):
        f=ImageFont.load_default()
        s='A long caption for testing'
        lines=caption_lines(s,f,70)
        self.assertEqual(''.join(lines),s)
        self.assertTrue(all(f.getlength(line)<=70 for line in lines))
        with self.assertRaises(ValueError):caption_lines('A\nB\nC\nD',f,70)
    def test_interval_and_status_guards(self):
        row=dict(id='fixture',start=1,end=2,target='测试',status='translated-asr-consensus')
        validate_cues([row],3)
        for changed in [dict(start=-1),dict(end=4),dict(end=float('nan')),dict(target=''),dict(status='unverified')]:
            with self.assertRaises(ValueError):validate_cues([dict(row,**changed)],3)
        with self.assertRaises(ValueError):validate_cues([row,row],3)
    def test_pixel_proof_rejects_noncaption_changes(self):
        video=dict(width=8,height=8,count=2,scale=1,rate=1,frames=[dict(timestamp=0),dict(timestamp=1)])
        original=bytes(96*2);modified=bytearray(original);modified[96+4*8+4]=255
        cues=[dict(start=1,end=2)]
        r=verify_caption_pixels(original,bytes(modified),video,cues,[[3,3,6,6]])
        self.assertEqual(r['no_caption_frames_byte_identical'],1)
        modified[0]=1
        with self.assertRaisesRegex(ValueError,'without active'):verify_caption_pixels(original,bytes(modified),video,cues,[[3,3,6,6]])
    def test_embedded_title_regions_preserve_non_title_frames(self):
        video=dict(width=8,height=8,count=2,scale=1,rate=1,frames=[dict(timestamp=0),dict(timestamp=1)])
        original=bytes(192);modified=bytearray(original);modified[96+4*8+4]=255
        r=verify_caption_pixels(original,bytes(modified),video,[],[],[[],[[3,3,6,6]]])
        self.assertEqual(r['caption_frames'],1)
        self.assertEqual(r['no_caption_frames_byte_identical'],1)
        with self.assertRaisesRegex(ValueError,'timeline length'):
            verify_caption_pixels(original,bytes(modified),video,[],[],[[]])

if __name__=='__main__':unittest.main()
