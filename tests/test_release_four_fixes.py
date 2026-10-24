import unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReleaseFourFixTests(unittest.TestCase):
 def test_chapter15_exact_wording_only(self):
  c=json.loads((ROOT/'locales/zh-CN/movie-titles.json').read_text('utf8'))
  row=next(r for r in c['titles'] if r['resource']=='MOVIES/CHAPTER15.AVI.REFORMATTED.AVI.IVF')
  self.assertEqual([r['target'] for r in row['labels']],['第十五章','初次相遇'])
 def test_art_targets_and_alpha(self):
  for name,target,policy in [('exit01a','出口','preserve-source'),('code03','有胆你就来！','reviewed-regions'),('soda01','汽水 / 泡泡 (front and side)','preserve-source')]:
   p=json.loads((ROOT/f'locales/zh-CN/art/{name}.json').read_text('utf8'))
   self.assertEqual(p['import_recipe']['target'],target)
   self.assertEqual(p['alpha_policy'],policy)
 def test_release_version_stays_1_0(self):
  self.assertEqual(json.loads((ROOT/'locales/zh-CN/installer.json').read_text('utf8'))['version'],'1.0')
if __name__=='__main__':unittest.main()
