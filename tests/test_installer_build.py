import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from installer_branding import build as branding
from build_installer import workspace


class InstallerBuildTests(unittest.TestCase):
    def test_original_png_is_embedded_without_redraw(self):
        with tempfile.TemporaryDirectory() as folder:
            d=Path(folder);(d/'branding').mkdir()
            Image.new('RGBA',(256,256),(100,20,40,255)).save(d/'branding/icon-source.png')
            Image.new('RGBA',(80,20),(250,0,0,128)).save(d/'branding/logo.png')
            source=(d/'branding/icon-source.png').read_bytes();logo=(d/'branding/logo.png').read_bytes()
            report=branding(d)
            self.assertEqual((d/'branding/app.ico').read_bytes()[22:],source)
            self.assertEqual((d/'branding/logo.png').read_bytes(),logo)
            self.assertEqual(report['logo_png_sha256'],hashlib.sha256(logo).hexdigest())
            self.assertFalse(report['image_generation'])

    def test_wrong_icon_size_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            d=Path(folder);(d/'branding').mkdir()
            Image.new('RGBA',(32,32)).save(d/'branding/icon-source.png')
            Image.new('RGBA',(32,32)).save(d/'branding/logo.png')
            with self.assertRaisesRegex(ValueError,'256px'):
                branding(d)

    def test_outputs_reject_outside_workspace_before_writing(self):
        with self.assertRaisesRegex(ValueError,'repository build'):
            workspace(Path('C:/unrelated-installer.exe'),'build')
        with self.assertRaisesRegex(ValueError,'repository dist'):
            workspace(ROOT/'build/not-a-release.exe','dist')

    def test_installer_versions_have_one_display_source(self):
        import re
        config=json.loads((ROOT/'locales/zh-CN/installer.json').read_text(encoding='utf8'))
        assembly=(ROOT/'installer/AssemblyInfo.cs').read_text(encoding='utf8')
        code=(ROOT/'installer/MaterialWindow.xaml.cs').read_text(encoding='utf8')
        self.assertIn('payload.Settings.version',code)
        self.assertNotIn(' · v1.0',code)
        actual=re.search(r'AssemblyInformationalVersion\("([^"\)]+)"\)',assembly).group(1)
        self.assertEqual(actual,config['version'])
        expected=(config['version']+'.0.0.0').split('.')[:4]
        for attribute in ('AssemblyVersion','AssemblyFileVersion'):
            found=re.search(attribute+r'\("([^"\)]+)"\)',assembly).group(1)
            self.assertEqual((found+'.0.0.0').split('.')[:4],expected)

    def test_material_ui_and_current_game_identity(self):
        xaml=(ROOT/'installer/MaterialWindow.xaml').read_text(encoding='utf-8')
        code=(ROOT/'installer/MaterialWindow.xaml.cs').read_text(encoding='utf-8')
        config=json.loads((ROOT/'locales/zh-CN/installer.json').read_text(encoding='utf-8'))
        self.assertIn('MaterialDesign3.Defaults.xaml',xaml)
        self.assertIn('3909960',xaml)
        self.assertIn('new Engine(payload,Append)',code)
        self.assertIn('Install.IsEnabled=Restore.IsEnabled=false',code)
        self.assertNotIn('ResourceEngine',code)
        self.assertEqual(config['executable_file'],'Dementium.exe')
        self.assertEqual(config['supported_builds'],'21501403')
        report=json.loads((ROOT/'installer/branding-inputs.json').read_text(encoding='utf-8'))
        for name,key in [('icon-source.png','icon_png_sha256'),('logo.png','logo_png_sha256')]:
            self.assertEqual(hashlib.sha256((ROOT/'installer/branding'/name).read_bytes()).hexdigest(),report[key])


if __name__=='__main__':
    unittest.main()
