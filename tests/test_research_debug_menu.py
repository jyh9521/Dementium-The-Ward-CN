import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from research_debug_menu import Investigation, main
from runtime_patch import ORIGINAL_SIZE


class DebugInvestigationTests(unittest.TestCase):
    def test_truncated_input_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            Investigation(b'MZ')

    def test_same_size_unknown_build_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            Investigation(bytes(ORIGINAL_SIZE))

    def test_output_outside_build_rejected_before_reading_target(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            args = ['research_debug_menu', '--exe', 'not-a-game.exe', '--output', str(output)]
            with patch.object(sys, 'argv', args), patch('research_debug_menu.investigate') as run:
                with self.assertRaisesRegex(ValueError, 'repository build'):
                    main()
                run.assert_not_called()
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
