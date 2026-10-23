import sys,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from movie_layers import sparse_runs,apply_runs,frame_at_timestamp,compile_movie
from movie import parse_ivf
import struct,subprocess


class MovieLayers(unittest.TestCase):
    def test_runs_are_horizontal_minimal_and_exact(self):
        a=Image.new('RGB',(4,2));b=a.copy()
        for xy,c in [((2,0),(1,0,0)),((3,0),(0,1,0)),((0,1),(0,0,1)),((2,1),(9,8,7))]:b.putpixel(xy,c)
        runs=sparse_runs(a,b)
        self.assertEqual(runs,[(2,b'\1\0\0\0\1\0'),(4,b'\0\0\1'),(6,b'\x09\x08\x07')])
        raw=bytearray(a.convert('RGBA').tobytes());raw[3::4]=bytes(range(8))
        applied=apply_runs(bytes(raw),a.size,runs)
        self.assertEqual(Image.frombytes('RGBA',a.size,applied).convert('RGB').tobytes(),b.tobytes())
        self.assertEqual(applied[3::4],bytes(range(8)))
    def test_forced_black_erasure_written_and_caption_alpha_mask(self):
        a=Image.new('RGB',(4,2));mask=Image.new('L',a.size)
        mask.putpixel((1,0),1);mask.putpixel((2,0),255)
        self.assertEqual(sparse_runs(a,a,mask),[(1,bytes(6))])
        with self.assertRaises(ValueError):sparse_runs(a,a,Image.new('L',(1,1)))
    def test_unchanged_has_no_runs(self):
        a=Image.new('RGB',(4,2));self.assertEqual(sparse_runs(a,a),[])
    def test_bad_image_rejected(self):
        a=Image.new('RGB',(4,2))
        for b in (Image.new('RGB',(3,2)),a.convert('RGBA')):
            with self.assertRaises(ValueError):sparse_runs(a,b)
    def test_invalid_runs_rejected(self):
        for runs in [[(-1,b'123')],[(7,b'123456')],[(3,b'123456')],[(0,b'12')],[(1,b'123'),(0,b'123')],[(0,b'')],[(True,b'123')]]:
            with self.assertRaises(ValueError):apply_runs(bytes(32),(4,2),runs)
    def test_nonopaque_alpha_stays_native(self):
        raw=bytes([3,4,5,17,6,7,8,0]);out=apply_runs(raw,(2,1),[(0,b'\x09\x08\x07')])
        self.assertEqual(out,bytes([9,8,7,17,6,7,8,0]))
    def test_exact_timestamp_not_wallclock_or_previous_frame(self):
        frames=[{'timestamp':0},{'timestamp':3},{'timestamp':9}]
        self.assertEqual(frame_at_timestamp(frames,3),1)
        self.assertIsNone(frame_at_timestamp(frames,4));self.assertIsNone(frame_at_timestamp(frames,-1))
    def test_native_geometry_rejected_before_decode(self):
        raw=struct.pack('<4sHH4sHHIIII',b'DKIF',0,32,b'VP90',20,10,30,1,1,0)+struct.pack('<IQ',1,0)+b'x'
        with self.assertRaisesRegex(ValueError,'geometry'):compile_movie(raw,'MOV',None,[],'unused')
    def test_caption_timing_uses_ivf_pts_and_deduplicates(self):
        raw=struct.pack('<4sHH4sHHIIII',b'DKIF',0,32,b'VP90',400,240,30,1,3,0)
        for t in (0,30,60):raw+=struct.pack('<IQ',1,t)+b'x'
        original=Image.new('RGB',(400,240));canvas=Image.new('RGBA',original.size);canvas.putpixel((5,5),(255,255,255,128))
        cue=dict(id='MOV:0',target='A',start=1,end=3)
        with patch('movie_layers.subprocess.run',return_value=subprocess.CompletedProcess([],0,original.tobytes()*3)),patch('movie_layers.render_caption',return_value=(canvas,{})):
            movie,report=compile_movie(raw,'MOV',None,[(cue,'bottom')],'unused')
        self.assertEqual(report['cues'][0]['frames'],2)
        self.assertEqual(movie['frames'][1]['layer_id'],movie['frames'][2]['layer_id'])
        self.assertEqual(movie['layers'][0],[])
        self.assertEqual(movie['layers'][1],[(2005,b'\x80\x80\x80')])
    def test_no_cue_frame_rejected(self):
        raw=struct.pack('<4sHH4sHHIIII',b'DKIF',0,32,b'VP90',400,240,30,1,1,0)+struct.pack('<IQ',1,0)+b'x'
        cue=dict(id='MOV:0',target='A',start=1,end=3)
        with patch('movie_layers.subprocess.run',return_value=subprocess.CompletedProcess([],0,bytes(400*240*3))),patch('movie_layers.render_caption',return_value=(Image.new('RGBA',(400,240)),{})):
            with self.assertRaisesRegex(ValueError,'no decoded frame'):compile_movie(raw,'MOV',None,[(cue,'bottom')],'unused')


if __name__=='__main__':unittest.main()
