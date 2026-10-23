"""Author source-dependent artwork deltas from hash-bound, reviewed fragments.

This is an optional art-import tool, not a release-build dependency. Complete
source/generated images stay local; normal builds consume the resulting delta.
Crop/resize/quarter-turn operations pack authored artwork into native UV slots.
"""
import argparse
import json
from pathlib import Path

from PIL import Image

from art_delta import apply, capture, sha
from build_image_text import checked_box


def import_fragments(original, base, recipe, fragments):
    if recipe['resource'] != base['resource']:
        raise ValueError('Fragment resource mismatch')
    edited = apply(original, base)
    regions = list(base['reviewed_regions'])
    mappings = list(recipe.get('preserved_mappings', []))
    for part in recipe['fragments']:
        name = part['file']
        if Path(name).name != name:
            raise ValueError('Fragment filename must be local basename')
        raw = (Path(fragments) / name).read_bytes()
        if sha(raw) != part['sha256']:
            raise ValueError('Fragment source identity mismatch')
        with Image.open(Path(fragments) / name) as source:
            source_box = checked_box(part['generated_box'], source.size)
            fragment = source.convert('RGBA').crop(source_box)
        target = checked_box(part['native_box'], original.size)
        rotation = part.get('rotation_ccw', 0)
        if rotation not in (0, 90, 180, 270):
            raise ValueError('Fragment rotation must be a quarter-turn')
        if rotation:
            fragment = fragment.transpose({90: Image.Transpose.ROTATE_90,
                                           180: Image.Transpose.ROTATE_180,
                                           270: Image.Transpose.ROTATE_270}[rotation])
        fragment = fragment.resize((target[2]-target[0], target[3]-target[1]),
                                   Image.Resampling.LANCZOS)
        edited.paste(fragment, target[:2])
        regions.append(list(target))
        mappings.append(dict(part))
    edited.putalpha(original.getchannel('A'))
    patch = capture(original, edited, resource=base['resource'],
                    prompt=recipe['prompt'], regions=regions)
    patch['import'] = dict(resize='LANCZOS per reviewed fragment; exact quarter-turn atlas packing',
                           crop_mappings=mappings, alpha='source',
                           protected='all pixels outside reviewed interiors; original borders, arrows and geometry',
                           authoring='imagegen local repaint matching original weathered painted artwork; no solid fills or runtime font overlay')
    return patch, edited


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--base-delta', type=Path, required=True)
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--fragments', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.resolve() in (a.original.resolve(), a.base_delta.resolve()):
        raise ValueError('Import must write a new delta, not overwrite input')
    with Image.open(a.original) as image:
        original = image.convert('RGBA')
    base = json.loads(a.base_delta.read_text(encoding='utf8'))
    recipe = json.loads(a.recipe.read_text(encoding='utf8'))
    patch, edited = import_fragments(original, base, recipe, a.fragments)
    a.output.write_text(json.dumps(patch, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    saved = json.loads(a.output.read_text(encoding='utf8'))
    if apply(original, saved).tobytes() != edited.tobytes():
        raise ValueError('Imported artwork delta roundtrip mismatch')
    print('ART IMPORT PASS resource='+base['resource']+' fragments='+str(len(recipe['fragments'])))


if __name__ == '__main__':
    main()
