import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class MovieSubtitleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'locales/zh-CN/movie-subtitles.json').read_text(encoding='utf-8'))

    def test_all_movie_triplets_have_identity(self):
        movies=self.data['movies']
        self.assertEqual(len(movies),34)
        self.assertEqual(len({m['resource'] for m in movies}),34)
        for m in movies:
            for name in ['sha256','ivf_sha256','dat_sha256','pcm_sha256']:
                self.assertRegex(m[name],r'^[a-f0-9]{64}$')

    def test_cues_are_timed_translated_and_nonoverlapping(self):
        ids=[]
        for m in self.data['movies']:
            previous=0
            for s in m['segments']:
                ids.append(s['id'])
                self.assertGreaterEqual(s['start'],previous)
                self.assertGreater(s['end'],s['start'])
                self.assertLessEqual(s['end'],m['duration'])
                self.assertTrue(s['source']);self.assertTrue(s['target'])
                if '[unclear' in s['source']:
                    self.assertEqual(s['status'],'needs-manual-audio-review')
                previous=s['end']
        self.assertEqual(len(ids),len(set(ids)))

    def test_chapter_reuse_is_verified_by_pcm(self):
        chapters=[m for m in self.data['movies'] if m['movie'].startswith('CHAPTER')]
        self.assertEqual(len(chapters),16)
        self.assertEqual(len({m['pcm_sha256'] for m in chapters}),1)
        self.assertEqual(len({m['pcm_sha256'] for m in self.data['movies']}),19)

    def test_models_are_local_and_identified(self):
        for m in self.data['models'].values():
            self.assertTrue(m['local_files_only'])
            self.assertRegex(m['model_sha256'],r'^[a-f0-9]{64}$')
            self.assertEqual(m['device'],'cpu')
            self.assertEqual(m['compute_type'],'int8')

if __name__=='__main__':unittest.main()
