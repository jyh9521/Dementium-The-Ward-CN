import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from review_audio_sources import select_candidates

class AudioCatalogReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'locales/zh-CN/audio-subtitles.json').read_text(encoding='utf-8'))

    def test_all_original_audio_identities_unique(self):
        clips=self.data['clips']
        self.assertEqual(len(clips),177)
        self.assertEqual(len({c['resource'] for c in clips}),177)
        for c in clips:
            self.assertRegex(c['sha256'],r'^[a-f0-9]{64}$')
            self.assertGreater(c['duration'],0)
        self.assertFalse(self.data['source_audio_modified'])
        self.assertFalse(self.data['game_launched'])

    def test_only_dialogue_has_timed_translated_cues(self):
        ids=[]
        for c in self.data['clips']:
            previous=0
            for cue in c['cues']:
                self.assertEqual(c['classification'],'intelligible-dialogue')
                self.assertGreaterEqual(cue['start'],previous)
                self.assertGreater(cue['end'],cue['start'])
                self.assertLessEqual(cue['end'],c['duration'])
                self.assertTrue(cue['source']);self.assertTrue(cue['target'])
                ids.append(cue['id']);previous=cue['end']
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(ids),10)

    def test_full_no_vad_and_lexical_candidate_coverage(self):
        coverage=self.data['coverage']
        self.assertTrue(coverage['full_no_vad_small_complete'])
        self.assertTrue(coverage['novel_lexical_candidate_large_review_complete'])
        self.assertEqual(coverage['full_no_vad_small_clips'],177)
        checked=sum(c['asr_review']['large_checked'] for c in self.data['clips'])
        required=sum(c['asr_review']['required_lexical_candidate'] for c in self.data['clips'])
        self.assertEqual(checked,coverage['large_checked_clips'])
        self.assertEqual(required,coverage['lexical_candidate_clips'])
        for c in self.data['clips']:
            self.assertTrue(c['asr_review']['small_no_vad_checked'])
            if c['asr_review']['required_lexical_candidate']:
                self.assertTrue(c['asr_review']['large_checked'])

    def test_mechanical_negative_control_never_becomes_dialogue(self):
        c=next(c for c in self.data['clips'] if c['resource']=='SFX/SE/BEEP2C_EDIT_11HZ_8BIT.FLAC')
        self.assertLess(c['duration'],0.1)
        self.assertEqual(c['cues'],[])
        self.assertTrue(c['asr_review']['large_checked'])

    def test_voice_selection_retains_short_and_processed_samples(self):
        inv=[dict(resource='SFX/ENEMYBT/TALK03LO.FLAC'),dict(resource='SFX/WHISPER/WHISPER.FLAC'),
             dict(resource='SFX/NOISE/HIT.FLAC'),dict(resource='MUSIC/theme.FLAC')]
        screen=[dict(resource='SFX/NOISE/HIT.FLAC',segments=[{'text':'BAM'}])]
        self.assertEqual([r['resource'] for r in select_candidates(inv,screen)],
                         [r['resource'] for r in inv[:3]])

if __name__=='__main__':unittest.main()
