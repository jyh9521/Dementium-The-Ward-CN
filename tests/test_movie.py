import unittest,struct,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from movie import parse_ivf,parse_dat,validate_pair,rebuild_dat,KEYFRAME

def fixture(sizes=(3,4,5),timestamps=(0,1,2)):
    ivf=struct.pack('<4sHH4sHHIIII',b'DKIF',0,32,b'VP90',400,240,30,1,len(sizes),0)
    rows=[]
    for i,(size,stamp) in enumerate(zip(sizes,timestamps)):
        rows.append((round(stamp/30,6),len(ivf)|(KEYFRAME if i==0 else 0),size))
        ivf+=struct.pack('<IQ',size,stamp)+bytes([i+1])*size
    dat=struct.pack('<IIQd',1,len(rows),max(sizes),30.)+b''.join(struct.pack('<dQQ',*r) for r in rows)
    return dat,ivf

class MovieTests(unittest.TestCase):
    def test_parse_and_noop(self):
        d,v=fixture();r=validate_pair(d,v)
        self.assertEqual(r['frames'],3);self.assertEqual(r['keyframes'],1)
        self.assertEqual(rebuild_dat(d,v,v,[True,False,False]),d)
    def test_growth_reindexes_and_retimes_rejected(self):
        d,v=fixture();_,new=fixture((10,1,17))
        out=rebuild_dat(d,v,new,[True,False,True]);t=parse_dat(out)
        self.assertEqual(t['max_frame_size'],17)
        self.assertEqual([r['offset'] for r in t['frames']],[32,54,67])
        self.assertEqual([r['time'] for r in t['frames']],[r['time'] for r in parse_dat(d)['frames']])
        _,bad=fixture((10,1,17),(0,1,3))
        with self.assertRaises(ValueError):rebuild_dat(d,v,bad,[True,False,True])
        with self.assertRaises(ValueError):rebuild_dat(d,v,new,[True,False])
        with self.assertRaises(ValueError):rebuild_dat(d,v,new,[False]*3)
    def test_corruption(self):
        d,v=fixture()
        for bad in [d[:-1],b'\x02'+d[1:],d[:8]+struct.pack('<Q',1)+d[16:]]:
            with self.assertRaises(ValueError):parse_dat(bad)
        for bad in [v[:-1],b'FAIL'+v[4:],v[:24]+struct.pack('<I',4)+v[28:]]:
            with self.assertRaises(ValueError):parse_ivf(bad)
        broken=bytearray(d);struct.pack_into('<Q',broken,32,KEYFRAME|33)
        with self.assertRaises(ValueError):validate_pair(bytes(broken),v)

if __name__=='__main__':unittest.main()
