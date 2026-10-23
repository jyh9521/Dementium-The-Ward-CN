"""Admission guards for the size-only, non-release experiment."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MoviePayloadResearchTests(unittest.TestCase):
    def reject(self, output, source, candidate, expected):
        p = subprocess.run([sys.executable, '-X', 'utf8',
                            str(ROOT/'tools/research_movie_payload.py'), 'modified',
                            '--output', str(output), '--source', str(source),
                            '--candidate', str(candidate)], cwd=ROOT,
                           capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(expected, p.stderr)
        self.assertFalse((output/'MODIFIED_FILE.zar').exists())

    def test_output_outside_build_rejected_before_input_read(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            self.reject(p/'output', p/'source', p/'candidate',
                        'Research output must stay under repository build/')

    def test_output_containing_candidate_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as t:
            p = Path(t)
            self.reject(p, ROOT/'missing-source', p/'candidate.zar',
                        'Research output contains an input')


if __name__ == '__main__':
    unittest.main()
