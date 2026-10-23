import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DashStyleTests(unittest.TestCase):
 def test_no_em_dash_in_display_targets(self):
  def walk(o):
   if isinstance(o,dict):
    for k,v in o.items():
     if k=='target' and isinstance(v,str):self.assertNotIn('—',v)
     else:walk(v)
   elif isinstance(o,list):
    for v in o:walk(v)
  for p in (ROOT/'locales/zh-CN').glob('*.json'):walk(json.loads(p.read_text('utf8')))
class SignArtworkTests(unittest.TestCase):
 def test_all_floor_labels_are_localized_art(self):
  words=[]
  for n in ('sign06','sign07','sign09'):
   p=json.loads((ROOT/f'locales/zh-CN/art/{n}.json').read_text('utf8'))
   words += [m['wording'] for m in p['import']['crop_mappings']]
  self.assertTrue({f'{side}{i}楼' for side in ('西','东') for i in range(1,8)} <= set(words))
 def test_side_strip_words_use_rotated_horizontal_art(self):
  for n,word in (('sign06','屋顶'),('sign07','停尸房')):
   p=json.loads((ROOT/f'locales/zh-CN/art/{n}.json').read_text('utf8'))
   m=next(m for m in p['import']['crop_mappings'] if m['wording']==word)
   self.assertEqual(m.get('rotation_ccw'),90)
 def test_security_title_ends_above_authorization_uv(self):
  p=json.loads((ROOT/'locales/zh-CN/art/sign05.json').read_text('utf8'))
  m=next((m for m in p['import']['crop_mappings'] if m['wording']=='安保区'),None)
  self.assertIsNotNone(m)
  self.assertLessEqual(m['native_box'][3],19)
class UnreadableSourceTests(unittest.TestCase):
 def test_box_small_print_is_protected_from_generated_reconstruction(self):
  for n in ('boxes01','boxes01b','boxes02','boxes02b'):
   p=json.loads((ROOT/f'locales/zh-CN/art/{n}.json').read_text('utf8'))
   self.assertIn([0,0,64 if n.startswith('boxes01') else 128,32],p['protected_regions'])
if __name__=='__main__':unittest.main()
