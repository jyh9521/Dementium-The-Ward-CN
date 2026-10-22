"""Build appended binfont glyphs from hash-verified installed font input.

Encoding/slot allocation is caller policy; no game paths or locale strings here.
"""
from __future__ import annotations
from dataclasses import asdict

from binfont import BinFont, Glyph
from font_source import resolve_fonts, font_metadata


def build_font(original_binfont: bytes, mapping: dict[int, int], profile: dict):
    """Append mapped glyph cells, preserving all original metrics and RGBA pixels.

    mapping maps source Unicode scalar values to unused runtime BMP slots.
    The atlas width is fixed; its height grows to the next sufficient power of
    two, bounded by 1024 because binary glyph x/y fields each use ten bits.
    """
    from PIL import Image, ImageDraw, ImageFont
    from fontTools.ttLib import TTFont

    original = BinFont(original_binfont)
    if not mapping:
        raise ValueError('Empty character mapping')
    if any(type(cp) is not int or not 0 <= cp <= 0x10FFFF or 0xD800 <= cp <= 0xDFFF
           for cp in mapping):
        raise ValueError('Invalid source Unicode scalar')
    slots = list(mapping.values())
    if any(type(slot) is not int or not 0 <= slot <= 0xFFFF or 0xD800 <= slot <= 0xDFFF
           for slot in slots):
        raise ValueError('Invalid runtime glyph slot')
    if len(set(slots)) != len(slots):
        raise ValueError('Duplicate runtime glyph slot')
    if set(slots) & set(original.glyphs):
        raise ValueError('Runtime glyph slot overwrites original glyph')
    spec = profile['fonts']['body']
    pixel_size = spec['pixel_size']
    cell_width = spec.get('cell_width', pixel_size)
    cell_height = spec.get('cell_height', pixel_size + 3)
    advance = spec.get('advance', cell_width)
    if (any(type(n) is not int for n in (pixel_size, cell_width, cell_height, advance)) or
            not 1 <= pixel_size <= 255 or not 1 <= cell_width <= 255 or
            not 1 <= cell_height <= 1024 or not 1 <= advance <= 255):
        raise ValueError('Invalid font cell or advance')
    if original.width > 1024 or original.height > 1024:
        raise ValueError('Original atlas exceeds metric address bound')
    columns = original.width // cell_width
    if not columns:
        raise ValueError('Cell wider than atlas')
    required_height = original.height + ((len(mapping) + columns - 1) // columns) * cell_height
    new_height = 1 << (required_height - 1).bit_length()
    if new_height > 1024:
        raise ValueError('Expanded atlas exceeds 1024 metric address bound')

    path = resolve_fonts(profile)['body']
    metadata = font_metadata(path)
    with TTFont(path) as font:
        cmap = font.getBestCmap()
    missing = sorted(cp for cp in mapping if cp not in cmap)
    if missing:
        raise ValueError('Required font glyph missing: ' + ','.join(hex(cp) for cp in missing))
    font = ImageFont.truetype(str(path), pixel_size)
    image = Image.new('RGBA', (original.width, new_height), (0, 0, 0, 0))
    image.paste(Image.frombytes('RGBA', (original.width, original.height), original.rgba), (0, 0))
    glyphs = dict(original.glyphs)
    added = []
    for index, (cp, slot) in enumerate(sorted(mapping.items())):
        box = font.getbbox(chr(cp))
        if box is None or box[0] < 0 or box[1] < 0 or box[2] > cell_width or box[3] > cell_height:
            raise ValueError('Source glyph extends outside configured cell: ' + hex(cp))
        cell = Image.new('RGBA', (cell_width, cell_height), (0, 0, 0, 0))
        ImageDraw.Draw(cell).text((0, 0), chr(cp), font=font, fill=(255, 255, 255, 255))
        ink = cell.getchannel('A').getbbox()
        if ink is None:
            raise ValueError('Required font glyph raster is empty: ' + hex(cp))
        x = (index % columns) * cell_width
        y = original.height + (index // columns) * cell_height
        image.paste(cell, (x, y))
        metric = Glyph(x, y, cell_height, cell_width, advance, 0, 0)
        glyphs[slot] = metric
        added.append({'unicode': cp, 'slot': slot, 'metric': asdict(metric),
                      'ink_box': list(ink), 'ink_pixels': sum(a > 0 for a in cell.getchannel('A').tobytes())})
    rgba = image.tobytes()
    result = original.write(glyphs, rgba, original.width, new_height)
    parsed = BinFont(result)
    if (parsed.rgba[:len(original.rgba)] != original.rgba or parsed.base_height != original.base_height or
            any(parsed.glyphs[cp] != glyph for cp, glyph in original.glyphs.items()) or
            any(parsed.glyph_rgba(cp) != original.glyph_rgba(cp) for cp in original.glyphs)):
        raise ValueError('Original font preservation verification failed')
    report = {'font_sha256': metadata['sha256'], 'font_metadata': metadata,
              'mapping': {str(cp): slot for cp, slot in sorted(mapping.items())},
              'added_glyphs': added, 'atlas_before': [original.width, original.height],
              'atlas_after': [parsed.width, parsed.height], 'serialized_base_height': parsed.base_height,
              'base_height_unchanged': True, 'original_glyphs_preserved': len(original.glyphs),
              'original_atlas_rgba_preserved': True}
    return result, report
