import copy
import hashlib
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from movie_overlay import pack_frames,build_movie_overlay,rollback_movie_overlay,MovieOverlayReplay,verify_movie_overlay,BASE


def frame(stem='TEST.DAT',start=0.,end=1.,runs=None):
    return dict(stem=stem,width=400,height=240,start=start,end=end,runs=runs if runs is not None else [(0,b'\xff\x01\x02'),(1596,b'\x03\x04\x05'),(383996,b'\x06\x07\x08')])


class MovieTableGuards(unittest.TestCase):
    def test_canonical_and_layer_dedup(self):
        rows=[frame(start=0,end=1),frame(start=1,end=2)]
        a,stats=pack_frames(rows);b,_=pack_frames(list(reversed(rows)))
        self.assertEqual(a,b);self.assertEqual(stats,[dict(stem='TEST.DAT',frames=2)])
        self.assertLess(len(a),400)

    def test_bad_names_dimensions_and_times(self):
        for field,value in [('stem','../TEST.DAT'),('stem','test.dat'),('stem','NODAT'),('stem','A'*96+'.DAT'),('width',401),('height',239),('start',float('nan')),('end',float('inf')),('start',2)]:
            row=frame();row[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):pack_frames([row])

    def test_bad_runs_and_overlap(self):
        for runs in [[(1,b'abc')],[(0,b'a')],[(383996,b'abcdef')],[(1596,b'abcdef')],[(4,b'abc'),(0,b'abc')],[(0,b'')]]:
            with self.subTest(runs=runs),self.assertRaises(ValueError):pack_frames([frame(runs=runs)])
        with self.assertRaises(ValueError):pack_frames([frame(),frame(start=.5,end=2)])
        with self.assertRaises(ValueError):pack_frames([frame(),frame()])
        with self.assertRaises(ValueError):pack_frames([frame(runs=[])])

    def test_unknown_identity_and_rollback_rejected(self):
        with self.assertRaises(ValueError):build_movie_overlay(b'MZ',b'MZ',[frame()],expected_input_sha256='0'*64)
        with self.assertRaises(ValueError):rollback_movie_overlay(b'MZ',{'format':'unknown'})


ORIGINAL=ROOT/'build/full/rollback-sample/Dementium.exe'
ARCHIVED_LAYERED=ROOT/'build/movie-overlay-release/baseline/MODIFIED_EXECUTABLE.exe'
LAYERED=ARCHIVED_LAYERED if ARCHIVED_LAYERED.exists() else ROOT/'build/release-candidate/MODIFIED_EXECUTABLE.exe'
@unittest.skipUnless(ORIGINAL.exists() and LAYERED.exists(),'offline user-supplied executable fixtures absent')
class NativeMovieTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes();cls.before=LAYERED.read_bytes()
        # The active release candidate may already include this layer after a
        # rebuild; tests must compose the pre-movie chain, never patch twice.
        import pefile,json
        check=pefile.PE(data=cls.before)
        has_movie=any(s.Name.rstrip(b'\0')==b'.locmov' for s in check.sections);check.close()
        if has_movie:
            recipe=json.loads((LAYERED.parent/'DIFF_FILE.json').read_text(encoding='utf-8'))['movie_overlay']
            cls.before=rollback_movie_overlay(cls.before,recipe)
        cls.frames=[frame(),frame(start=1,end=2,runs=[(1600,b'\x08\x09\x0a')])]
        cls.after,cls.recipe=build_movie_overlay(cls.before,cls.original,cls.frames,expected_input_sha256=hashlib.sha256(cls.before).hexdigest())

    def test_exact_layered_roundtrip_and_drift(self):
        self.assertEqual(rollback_movie_overlay(self.after,self.recipe),self.before)
        for bad in [self.after[:-1],b'X'+self.after[1:],self.before]:
            with self.assertRaises(ValueError):rollback_movie_overlay(bad,self.recipe)
        changed=copy.deepcopy(self.recipe);changed['hook_before']='00'*5
        with self.assertRaises(ValueError):rollback_movie_overlay(self.after,changed)
        with self.assertRaises(ValueError):build_movie_overlay(self.after,self.original,self.frames,expected_input_sha256=hashlib.sha256(self.after).hexdigest())
        with self.assertRaises(ValueError):build_movie_overlay(self.before,self.original,self.frames,expected_input_sha256='0'*64)

    def test_pe_permissions_header_shift_debug_and_pdata(self):
        import pefile,struct
        a=pefile.PE(data=self.before);b=pefile.PE(data=self.after);shift=self.recipe['header_shift']
        self.assertGreater(shift,0)
        self.assertEqual(b.OPTIONAL_HEADER.SizeOfHeaders,a.OPTIONAL_HEADER.SizeOfHeaders+shift)
        for old,new in zip(a.sections,b.sections):
            self.assertEqual(old.VirtualAddress,new.VirtualAddress)
            if old.SizeOfRawData:self.assertEqual(old.PointerToRawData+shift,new.PointerToRawData)
        self.assertEqual(b.sections[-2].Characteristics,0x60000020)
        self.assertEqual(b.sections[-1].Characteristics,0xc0000080)
        self.assertEqual(b.sections[-1].SizeOfRawData,0)
        for old,new in zip(a.DIRECTORY_ENTRY_DEBUG,b.DIRECTORY_ENTRY_DEBUG):
            self.assertEqual(old.struct.PointerToRawData+shift if old.struct.PointerToRawData else 0,new.struct.PointerToRawData)
            self.assertEqual(old.struct.AddressOfRawData,new.struct.AddressOfRawData)
        directory=b.OPTIONAL_HEADER.DATA_DIRECTORY[3]
        table=b.get_data(directory.VirtualAddress,directory.Size)
        self.assertEqual(struct.unpack('<III',table[-12:]),(self.recipe['section_rva'],self.recipe['section_rva']+self.recipe['code_size'],self.recipe['unwind_rva']))
        self.assertEqual(b.get_data(self.recipe['unwind_rva'],20).hex(),self.recipe['unwind'])
        a.close();b.close()

    def test_all_pixels_aslr_alpha_registers_and_unwind(self):
        report=verify_movie_overlay(ORIGINAL,self.after,self.recipe,self.frames)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual([r['native_frames'] for r in report['results']],[2,2])
        self.assertFalse(report['game_launched']);self.assertFalse(report['steam_directory_modified'])

    def test_ss0_boundary_frame_replay_and_stale_clear(self):
        original=bytes(range(256))*1500
        for base in (BASE,0x180000000):
            r=MovieOverlayReplay(self.after,self.recipe,base)
            out=r.run(original,'TEST.DAT',0.,longname=False,ownership=1)
            self.assertEqual(out['pixels'][:4],b'\x02\x01\xff\x03')
            self.assertEqual(out['pixels'][1596:1600],b'\x05\x04\x03\x3f')
            self.assertEqual(out['pixels'][383996:384000],b'\x08\x07\x06\xff')
            second=r.run(original,'TEST.DAT',1.,longname=False)
            self.assertEqual(second['pixels'][:4],original[:4])
            self.assertEqual(second['pixels'][1600:1604],b'\x0a\x09\x08\x43')
            ended=r.run(original,'TEST.DAT',2.,longname=False)
            self.assertEqual(ended['pixels'],original)
            self.assertEqual(ended['pointer'],r.heap+0x40000)

if __name__=='__main__':unittest.main()
