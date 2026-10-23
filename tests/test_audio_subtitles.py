import json,pathlib,sys,unittest,copy
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from audio_subtitles import *
ROOT=pathlib.Path(__file__).resolve().parents[1]
def fixture():
 return dict(schema=1,clips=[dict(resource='SFX/VOICE.FLAC',sha256='a'*64,duration=3.,cues=[dict(id='v:0',start=0.,end=1.,target='你好',status='translated-asr-consensus'),dict(id='v:1',start=2.,end=3.,target='再见',status='translated-asr-consensus')])])
class AudioSubtitlesTests(unittest.TestCase):
 def test_resource(self):
  x=fixture();data=build_resource(x);self.assertEqual(data,build_resource(x));self.assertEqual(read_resource(data)['clips'][0]['cues'][0]['target'],'你好')
  with self.assertRaises(ValueError):read_resource(data[:-1])
 def test_channel_stop_and_scene(self):
  s=SubtitleState(fixture());self.assertTrue(s.play(1,'SFX/VOICE.FLAC','a'*64,10.))
  self.assertEqual(len(s.visible(10.5)),1);self.assertEqual(s.visible(11.5),[])
  s.play(2,'SFX/VOICE.FLAC','a'*64,12.);self.assertEqual(len(s.visible(12.5)),2)
  s.stop(1);self.assertEqual(len(s.visible(12.75)),1)
  s.clear_scene();self.assertEqual(s.visible(12.8),[])
  with self.assertRaises(ValueError):s.visible(11.)
 def test_guards(self):
  x=fixture();x['clips'][0]['cues'][0]['end']=9
  with self.assertRaises(ValueError):validate_catalog(x)
  s=SubtitleState(fixture())
  with self.assertRaises(ValueError):s.play(1,'SFX/VOICE.FLAC','b'*64,0)
 def test_actual_catalog(self):
  path=ROOT/'locales/zh-CN/audio-subtitles.json'
  if not path.exists():self.skipTest('catalog not present')
  c=json.loads(path.read_text(encoding='utf-8'));validate_catalog(c)
  data=read_resource(build_resource(c));self.assertGreaterEqual(len(data['clips']),6)
  self.assertGreaterEqual(sum(len(x['cues']) for x in data['clips']),7)

 def test_native_overlay_real_bytes_and_rollback(self):
  import struct,tempfile
  from types import SimpleNamespace
  from binfont import Glyph
  from runtime_patch import patch_bytes
  exe=pathlib.Path(r'C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward\Dementium.exe')
  if not exe.exists():self.skipTest('user-supplied executable absent')
  raw=bytearray(42);raw[:8]=b'fLaC'+bytes([128,0,0,34])
  raw[18:26]=((11025<<44)|(15<<36)|11025).to_bytes(8,'big');raw=bytes(raw)
  name='SFX/ENEMYBT/TALK01LO.FLAC';catalog=dict(schema=1,clips=[dict(resource=name,sha256=hashlib.sha256(raw).hexdigest(),duration=1.,cues=[dict(id='test:0',start=0.,end=0.5,target='新游戏',status='translated-asr-consensus')])])
  font=SimpleNamespace(glyphs={ord(c):Glyph(0,0,12,12,12,0,0) for c in '新游戏'})
  runtime,rr=patch_bytes(exe.read_bytes());out,patch=build_native_overlay(runtime,rr,catalog,{name:raw},font)
  self.assertEqual(rollback_overlay(out,patch),runtime)
  import pefile
  pe=pefile.PE(data=out)
  entries=[e for e in pe.DIRECTORY_ENTRY_EXCEPTION if e.struct.BeginAddress==patch['section_rva']]
  self.assertEqual(len(entries),1)
  self.assertEqual(entries[0].struct.EndAddress,patch['section_rva']+patch['code_size'])
  self.assertEqual(entries[0].struct.UnwindData,patch['unwind_rva'])
  self.assertEqual(pe.get_data(patch['unwind_rva'],4),bytes([1,19,10,0]))
  pe.close()
  dispatch=verify_native_dispatch(exe,catalog)
  self.assertEqual(dispatch['verified'][0]['resource'],name)
  replay=NativeOverlayReplay(exe,out,patch)
  event=dict(cue_id=AUDITED_CUE_IDS[name],sample_rate=11025,position=0.25)
  calls=replay.render([event]);self.assertEqual(calls[0]['text'],'新游戏');self.assertEqual((calls[0]['x'],calls[0]['y']),(214.,160.))
  self.assertEqual(replay.render([dict(event,position=0.75)]),[])
  self.assertEqual(replay.render([dict(event,paused=True)]),[])
  self.assertEqual(replay.render([dict(event,stopped=True)]),[])
  self.assertEqual(replay.render([dict(event,playing=False)]),[])
  self.assertEqual(replay.render([dict(event,cue_id=0)]),[])
  self.assertEqual(replay.render([dict(event,sample_rate=8000)]),[])
  self.assertEqual(replay.render([]),[])
  cases=[('duplicate', [event]*4, {}, 1),('first-eligible',[dict(event,volume=0.),event],{},1),('source-gap',[dict(event,position=0.75),event],{},1),('modal',[event],dict(modal=True),0),('modal-close',[event],dict(modal='closed'),1),
         ('muted',[event],dict(muted=True),0),('master-zero',[event],dict(master_gain=0.),0)]
  cases += [(key,[dict(event,**{key:0.0})],{},0) for key in ('volume','gain','envelope')]
  cases += [('both-panned-zero',[dict(event,left=0.,right=0.)],{},0),
            ('right-only',[dict(event,left=0.,right=1.)],{},1),
            ('unmixed-record',[dict(event,mixer_active=False)],{},0),
            ('scheduled-future',[dict(event,scheduled=2.)],{},0),
            ('scheduled-now',[dict(event,scheduled=1.)],{},1),
            ('scheduled-past',[dict(event,scheduled=0.5)],{},1)]
  for case_name,events,options,expected in cases:
   with self.subTest(regression=case_name):self.assertEqual(len(replay.render(events,**options)),expected)
  for key in ('volume','gain','envelope','left','right'):
   sample=dict(left=0.,right=0.) if key in ('left','right') else {key:0.}
   self.assertTrue(all(v==0. for v in replay.mixer_coefficients(sample)))
  self.assertTrue(all(v==0. for v in replay.mixer_coefficients({},muted=True)))
  self.assertTrue(all(v==0. for v in replay.mixer_coefficients({},master_gain=0.)))
  self.assertTrue(any(v>0. for v in replay.mixer_coefficients({})))
  from executable_text import build_executable,apply_executable_patch
  literal_catalog=json.loads((ROOT/'locales/zh-CN/executable-text.json').read_text(encoding='utf-8'))
  literal,lr=build_executable(runtime,literal_catalog)
  self.assertNotEqual(literal,runtime)
  combined,cp=build_native_overlay(literal,rr,catalog,{name:raw},font,literal_recipe=lr)
  self.assertEqual(apply_executable_patch(rollback_overlay(combined,cp),lr,True),runtime)
  with self.assertRaises(ValueError):build_native_overlay(literal,rr,catalog,{name:raw},font)
  drift=bytearray(literal);drift[-1]^=1
  with self.assertRaises(ValueError):build_native_overlay(bytes(drift),rr,catalog,{name:raw},font,literal_recipe=lr)
  shifted=NativeOverlayReplay(exe,out,patch,image_base=0x150000000)
  self.assertEqual(shifted.render([event])[0]['text'],'新游戏')
  self.assertEqual(len(shifted.render([event]*2)),1)
  self.assertEqual(shifted.render([event],modal=True),[])
  self.assertEqual(shifted.render([dict(event,gain=0.)]),[])
  self.assertTrue(shifted.unwind_verified)
  from test_binfont import fixture as font_fixture
  from binfont import BinFont
  glyphs={ord(c):Glyph(0,0,2,2,3,0,0) for c in ' 新游戏'}
  font_bytes=BinFont(font_fixture()).write(glyphs,bytes([255])*64,4,4)
  actual=NativeOverlayReplay(exe,out,patch,font_data=font_bytes)
  command_counts=[]
  for _ in range(20):
   result=actual.render([event])[0]
   self.assertEqual(result['text'],'新游戏')
   self.assertEqual(result['script_pointer'],0x3a83c0)
   command_counts.append(result['script_commands'])
  self.assertEqual(len(set(command_counts)),1)
  self.assertEqual(actual.r.compiler_calls,20)
  self.assertEqual(actual.r.heap_calls,0)

if __name__=='__main__':unittest.main()
