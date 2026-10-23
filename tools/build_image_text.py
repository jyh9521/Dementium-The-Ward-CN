"""Hash-locked, rectangle-bounded native texture label recipes.

Ported from Dementium-II-CN tools/image_text.py (MIT, jyh9521): glyph
coverage, visible-ink centering, hard-edged Fusion raster, physical-input
protection and outside-region pixel comparison. Container I/O is adapted to
the independently verified double-LZ4 Texture codec. No original pixels ship
in the configuration; input hashes bind each recipe to its surveyed asset.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from font_source import resolve_fonts
from texture import Texture
from zar import Zar, filehash, write_json


def checked_box(box, size):
    if (not isinstance(box, list) or len(box) != 4 or
            any(type(v) is not int for v in box)):
        raise ValueError('Rectangle must contain four integers')
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
        raise ValueError('Rectangle outside texture')
    return tuple(box)


def raster_label(label, font):
    """Upstream visible-ink centering: no rescaling or negative tracking."""
    target = label['target']
    if not isinstance(target, str) or not target.strip():
        raise ValueError('Empty image label')
    size = label.get('font_size', 12)
    stroke = label.get('stroke', 0)
    if type(size) is not int or not 1 <= size <= 96 or type(stroke) is not int or not 0 <= stroke <= 2:
        raise ValueError('Invalid raster font size or stroke')
    lines = target.split('\n')
    if len(lines) > 8 or any(not line for line in lines):
        raise ValueError('Invalid image label lines')
    boxes = [font.getbbox(line) for line in lines]
    width = max(b[2] - b[0] for b in boxes)
    scratch = Image.new('L', (width + 16, len(lines) * size + 16))
    draw = ImageDraw.Draw(scratch)
    for i, (line, box) in enumerate(zip(lines, boxes)):
        draw.text((8 - box[0], 8 + i * size - box[1]), line, font=font,
                  fill=255, stroke_width=stroke, stroke_fill=128 if stroke else 255)
    bounds = scratch.getbbox()
    if bounds is None:
        raise ValueError('Empty image label ink')
    return scratch.crop(bounds)


def render_recipe(original, recipe, font_loader):
    """Edit only configured regions; reject clipped ink or changed physical keys."""
    if original.mode != 'RGBA' or list(original.size) != recipe['size']:
        raise ValueError('Unexpected source image dimensions or mode')
    allowed = Image.new('L', original.size)
    for box in recipe['allowed_regions']:
        x0, y0, x1, y1 = checked_box(box, original.size)
        ImageDraw.Draw(allowed).rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    protected = Image.new('L', original.size)
    for box in recipe.get('protected_regions', []):
        x0, y0, x1, y1 = checked_box(box, original.size)
        ImageDraw.Draw(protected).rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    result = original.copy()
    for region in recipe.get('clear_regions', []):
        box = checked_box(region['box'], original.size)
        if allowed.crop(box).getextrema() != (255, 255):
            raise ValueError('Clear rectangle outside allowed regions')
        color = region.get('color', [0, 0, 0, 0])
        if len(color) != 4 or any(type(c) is not int or not 0 <= c <= 255 for c in color):
            raise ValueError('Invalid replacement background color')
        if region.get('ink') == 'neutral':
            # Black chapter backgrounds: erase only gray/white subtitle ink,
            # not adjacent red ornaments. Exact source identity is mandatory.
            for yy in range(box[1],box[3]):
                for xx in range(box[0],box[2]):
                    r,g,b,a = result.getpixel((xx,yy))
                    if r == g == b: result.putpixel((xx,yy),tuple(color))
        elif region.get('ink') is not None:
            raise ValueError('Unknown ink selection')
        else:
            result.paste(tuple(color), box)
    ink_areas = Image.new('L', original.size)
    layouts = []
    for label in recipe['labels']:
        x0, y0, x1, y1 = checked_box(label['box'], original.size)
        if allowed.crop((x0,y0,x1,y1)).getextrema() != (255,255):
            raise ValueError('Label rectangle outside allowed regions')
        ink = raster_label(label, font_loader(label.get('font_size', 12)))
        if ink.width > x1 - x0 or ink.height > y1 - y0:
            raise ValueError('Image label overflow: ' + recipe['resource'] + ': ' + label['target'])
        left = x0 if label.get('ink_align') == 'left' else x0 + (x1 - x0 - ink.width) // 2
        top = y0 + (y1 - y0 - ink.height) // 2
        area = (left, top, left + ink.width, top + ink.height)
        # Physical input symbols must never be hidden under translated ink.
        covered = protected.crop(area)
        if any(a and b for a,b in zip(covered.get_flattened_data(), ink.get_flattened_data())):
            raise ValueError('Translated label overlaps protected input symbol')
        if any(a and b for a,b in zip(ink_areas.crop(area).get_flattened_data(), ink.get_flattened_data())):
            raise ValueError('Translated labels overlap')
        color = tuple(label.get('color', [255,255,255,255]))
        outline = tuple(label.get('outline', [0,0,0,255]))
        for y in range(ink.height):
            for x in range(ink.width):
                value = ink.getpixel((x,y))
                if value >= 192:
                    result.putpixel((left+x,top+y),color)
                    ink_areas.putpixel((left+x,top+y),255)
                elif value >= 64:
                    result.putpixel((left+x,top+y),outline)
                    ink_areas.putpixel((left+x,top+y),255)
        layouts.append(dict(source=label['source'],target=label['target'],ink_box=list(area),
                            font_size=label.get('font_size',12)))
    # Upstream preservation rule: restore protected region source pixels, but
    # only after explicitly rejecting any overlap by new text above.
    for box in recipe.get('protected_regions', []):
        result.paste(original.crop(box), (box[0],box[1]))
    before = original.get_flattened_data()
    after = result.get_flattened_data()
    changed = 0
    for a,b,ok,locked in zip(before,after,allowed.get_flattened_data(),protected.get_flattened_data()):
        if a != b:
            if not ok or locked:
                raise ValueError('Pixels outside allowed regions or inside protected regions changed')
            changed += 1
    if not changed:
        raise ValueError('Image recipe made no change')
    return result,dict(changed_pixels=changed,outside_regions_unchanged=True,
                       protected_regions_unchanged=True,dimensions_unchanged=True,labels=layouts)


def build_images(zar, config, fontpath):
    if isinstance(config, (str, Path)):
        config = json.loads(Path(config).read_text(encoding='utf-8'))
    if config.get('schema') != 1 or not config.get('images'):
        raise ValueError('Unsupported image text configuration')
    if filehash(Path(fontpath)) != config['font']['sha256']:
        raise ValueError('Image font source identity mismatch')
    with TTFont(str(fontpath)) as face:
        supported = set(face.getBestCmap())
    required = {ord(c) for r in config['images'] for l in r['labels'] for c in l['target'] if not c.isspace()}
    missing = required - supported
    if missing:
        raise ValueError('Image font missing glyphs: ' + ', '.join(f'U+{cp:04X}' for cp in sorted(missing)))
    replacements = {}; records = []; fonts = {}
    def get_font(size):
        if size not in fonts: fonts[size] = ImageFont.truetype(str(fontpath),size)
        return fonts[size]
    for recipe in config['images']:
        name = recipe['resource']
        if name in replacements:
            raise ValueError('Duplicate image text recipe')
        raw = zar.read(name)
        texture = Texture(raw,expected_sha256=recipe['source_sha256'],expected_header=recipe['header_words'])
        original = Image.frombytes('RGBA',(texture.width,texture.height),texture.rgba)
        result, row = render_recipe(original,recipe,get_font)
        encoded = texture.rebuild(result.tobytes(),expected_sha256=recipe['source_sha256'])
        check = Texture(encoded)
        if check.rgba != result.tobytes() or check.header_words != texture.header_words:
            raise ValueError('Encoded image text verification failed')
        replacements[name] = encoded
        row.update(resource=name,source_sha256=texture.sha256,output_sha256=hashlib.sha256(encoded).hexdigest(),
                   rgba_sha256=hashlib.sha256(check.rgba).hexdigest(),font_sha256=config['font']['sha256'])
        records.append(row)
    return replacements,dict(schema=1,images=records,image_count=len(records),
                             verification='offline raster and container checks; no game execution')


def write_previews(replacements, output):
    """Deterministic review contact sheets; native asset output stays unscaled."""
    output = Path(output)
    rows = sorted(replacements.items())
    paths = []
    for page, start in enumerate(range(0,len(rows),12)):
        selected = rows[start:start+12]
        sheet = Image.new('RGB',(1284,((len(selected)+2)//3)*265),(45,45,45))
        draw = ImageDraw.Draw(sheet)
        for i,(name,data) in enumerate(selected):
            t = Texture(data)
            original = Image.frombytes('RGBA',(t.width,t.height),t.rgba)
            # Tiny legends get an integer nearest-neighbor QA enlargement only.
            scale = min(3,428//t.width,240//t.height)
            preview = original.resize((t.width*scale,t.height*scale),Image.Resampling.NEAREST) if scale>1 else original
            background = Image.new('RGBA',preview.size,(45,45,45,255))
            background.alpha_composite(preview)
            x,y = i%3*428,i//3*265
            sheet.paste(background.convert('RGB'),(x,y))
            draw.text((x+2,y+244),name.replace('TEXTURES/',''),fill=(230,230,230))
        path = output / f'contact-ui-{page:02d}.png'
        sheet.save(path)
        paths.append(str(path.resolve()))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',required=True,type=Path)
    parser.add_argument('--config',default='locales/zh-CN/image-text.json',type=Path)
    parser.add_argument('--out',default='build/full-research/ui-edits',type=Path)
    args = parser.parse_args()
    from investigate import ensure_output
    from workspace_io import validate_output_tree
    ensure_output(args.game,args.out)
    validate_output_tree(args.out)
    config = json.loads(args.config.read_text(encoding='utf-8'))
    path = resolve_fonts({'fonts':{'body':config['font']}})['body']
    profile = json.loads((Path(__file__).resolve().parents[1]/'assets/game-profile.json').read_text(encoding='utf-8'))
    archive = Zar((args.game/profile['archive']).read_bytes())
    replacements, report = build_images(archive,config,path)
    for name, data in replacements.items():
        t = Texture(data)
        Image.frombytes('RGBA',(t.width,t.height),t.rgba).save(args.out/(name.replace('/','__')+'.png'))
    report['contact_sheets'] = write_previews(replacements,args.out)
    write_json(args.out/'report.json',report)
    print('IMAGE TEXT PASS images='+str(len(replacements))+' outside-regions=unchanged protected-inputs=unchanged dimensions=native')


if __name__ == '__main__':
    main()
