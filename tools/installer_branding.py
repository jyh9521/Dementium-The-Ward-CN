"""Verify user-provided branding and wrap the original PNG in an ICO container.

No artwork generation, resampling, font replacement or image rewriting occurs.
"""
import hashlib
import json
from pathlib import Path
import struct
from PIL import Image


def build(directory):
    directory = Path(directory)
    png = (directory / 'branding/icon-source.png').read_bytes()
    logo = (directory / 'branding/logo.png').read_bytes()
    with Image.open(directory / 'branding/icon-source.png') as image:
        if image.size != (256, 256) or image.format != 'PNG':
            raise ValueError('Expected the supplied 256px PNG icon')
    ico = struct.pack('<HHH', 0, 1, 1)
    ico += struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(png), 22) + png
    (directory / 'branding/app.ico').write_bytes(ico)
    report = dict(schema=1, source='Two user-provided attachments, 2026-10-23',
                  image_generation=False, icon_png_embedded_unchanged=True,
                  icon_png_sha256=hashlib.sha256(png).hexdigest(),
                  logo_png_sha256=hashlib.sha256(logo).hexdigest())
    (directory / 'branding-inputs.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    if (directory / 'branding/app.ico').read_bytes()[22:] != png:
        raise ValueError('Reopened icon does not contain the original image')
    return report


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[1] / 'installer')
    print('BRANDING PASS icon=original-PNG-in-ICO logo=byte-identical')
