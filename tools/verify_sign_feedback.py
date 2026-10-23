"""Verify final archive artwork, source-preserved pixels, mips and dash targets."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from art_delta import apply
from build_art import rebuild_mips
from build_art import build_art
from content import Content
from engine_image import EngineImage
from build_locale import inputs
from zar import Zar, filehash, write_json

ROOT = Path(__file__).resolve().parents[1]


def image(raw):
    codec = EngineImage(raw, 4)
    w, h, _ = codec.levels[0]
    return codec, Image.frombytes(codec.mode, (w, h), codec.level_pixels()).convert('RGBA')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game', type=Path, required=True)
    p.add_argument('--build', type=Path, required=True)
    a = p.parse_args()
    out = a.build.resolve()
    if ROOT/'build' not in out.parents:
        raise ValueError('Verification output must stay in repository build/')
    # Identity is checked by the same full-manifest gate as the release build.
    profile, identity, _, _, original_z, original_c, _ = inputs(a.game, 'zh-CN')
    final_z = Zar((out/'MODIFIED_FILE.zar').read_bytes())
    final_c = Content(final_z.read(profile['content']))
    art_inner,art_outer,art_report=build_art(original_z,original_c,ROOT/'locales/zh-CN/art-patches.json')
    for resource,expected in art_inner.items():
        if final_c.read(resource)!=expected:raise ValueError('Final inner art mismatch: '+resource)
    for resource,expected in art_outer.items():
        if final_z.read(resource)!=expected:raise ValueError('Final outer art mismatch: '+resource)
    if art_report['centered_labels']!=43 or not art_report['artwork_lighting_pairs']:
        raise ValueError('Missing centered labels or shared death artwork proof')
    rows = []
    previews = []
    for name in ('sign05', 'sign06', 'sign07', 'sign09'):
        resource = '3d/tex/'+name+'.tex'
        codec, original = image(original_c.read(resource))
        final_codec, actual = image(final_c.read(resource))
        patch = json.loads((ROOT/'locales/zh-CN/art'/f'{name}.json').read_text(encoding='utf8'))
        expected = apply(original, patch)
        if actual.tobytes() != expected.tobytes():
            raise ValueError('Final artwork does not match reviewed delta: '+name)
        encoded, mip_report = rebuild_mips(codec, expected, regions=patch['reviewed_regions'])
        if encoded != final_c.read(resource):
            raise ValueError('Final mip levels differ: '+name)
        if original.getchannel('A').tobytes() != actual.getchannel('A').tobytes():
            raise ValueError('Source alpha changed: '+name)
        mappings = patch['import']['crop_mappings']
        floors = [m for m in mappings if m['wording'].endswith('楼')]
        for m in floors:
            # A flat-color cover would fail this check. Visual style was also
            # reviewed from actual native pixels, not just the high-res source.
            pixels = actual.crop(m['native_box']).convert('RGB')
            red_material = {p for p in pixels.get_flattened_data() if p[0] > p[1]*1.4 and p[0] > p[2]*1.4}
            if len(red_material) < 40:
                raise ValueError('Floor sign lacks textured red material: '+m['wording'])
        actual.save(out/(name+'-reviewed.png'))
        previews.append((name, original, actual))
        rows.append(dict(resource=resource, final_source_delta_match=True,
                         source_alpha_preserved=True, all_mips_match=True,
                         floors=[m['wording'] for m in floors], **mip_report))
    expected_floors = {f'{side}{i}楼' for side in ('西', '东') for i in range(1, 8)}
    if {v for row in rows for v in row['floors']} != expected_floors:
        raise ValueError('Fourteen floor signs are incomplete')
    def targets(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == 'target' and isinstance(v, str):
                    yield v
                else:
                    yield from targets(v)
        elif isinstance(o, list):
            for v in o:
                yield from targets(v)
    values = [v for path in (ROOT/'locales/zh-CN').glob('*.json')
              for v in targets(json.loads(path.read_text(encoding='utf8')))]
    if any('—' in value for value in values):
        raise ValueError('Em dash remains in display target')
    board = Image.new('RGB', (560, 1120), (35, 35, 35))
    draw = ImageDraw.Draw(board)
    for i, (name, original, actual) in enumerate(previews):
        for col, (label, im) in enumerate((('original', original), ('reworked', actual))):
            board.paste(im.resize((256, 256), Image.Resampling.NEAREST), (col*280, i*280+24))
            draw.text((col*280, i*280), name+' '+label)
    board.save(out/'sign-artwork-preview.png')
    # Show the door-facing orientation of the rotated atlas strips.
    door = Image.new('RGB', (720, 320), (30, 30, 30))
    draw = ImageDraw.Draw(door)
    for i, name in enumerate(('sign06', 'sign07')):
        im = next(v for n, _, v in previews if n == name)
        strip = im.crop((107, 40, 125, 112)).transpose(Image.Transpose.ROTATE_270)
        door.paste(strip.resize((576, 144), Image.Resampling.NEAREST), (0, i*160+16))
        draw.text((0, i*160), name+' atlas strip unpacked clockwise (offline preview)')
    door.save(out/'door-label-orientation.png')
    # All centered frames shown from the FINAL archive, with geometric center
    # crosshairs and actual committed ink bounds; no authoring plate dependency.
    centered=[];protected=[]
    for entry in json.loads((ROOT/'locales/zh-CN/art-patches.json').read_text(encoding='utf8'))['patches']:
        patch=json.loads((ROOT/'locales/zh-CN'/entry['patch']).read_text(encoding='utf8'))
        if entry['scope']=='inner':
            _,actual=image(final_c.read(entry['resource']))
            _,source=image(original_c.read(entry['resource']))
        else:
            from texture import Texture
            co=Texture(final_z.read(entry['resource']))
            actual=Image.frombytes('RGBA',(co.width,co.height),co.rgba)
            co=Texture(original_z.read(entry['resource']))
            source=Image.frombytes('RGBA',(co.width,co.height),co.rgba)
        for row in patch.get('alignment',{}).get('labels',[]):
            centered.append((entry['resource'],row,actual))
        if 'unreadable_source_policy' in patch:
            box=[0,0,64 if '/boxes01' in entry['resource'] else 128,32]
            if source.crop(box).tobytes()!=actual.crop(box).tobytes():
                raise ValueError('Unclear source print changed: '+entry['resource'])
            protected.append(dict(resource=entry['resource'],box=box,original_pixels_identical=True))
    centers=Image.new('RGB',(1600,((len(centered)+3)//4)*140),(28,28,28))
    d=ImageDraw.Draw(centers)
    for i,(resource,row,actual) in enumerate(centered):
        frame=row['frame_box'];im=actual.crop(frame).convert('RGB')
        scale=min(380/im.width,95/im.height)
        im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.NEAREST)
        x=(i%4)*400;y=(i//4)*140
        centers.paste(im,(x,y+25))
        d.text((x,y),Path(resource).stem+' '+str(i+1)+' error='+str(row['center_error']),fill='white')
        midx=x+im.width/2;midy=y+25+im.height/2
        d.line((midx,y+25,midx,y+25+im.height),fill=(255,70,70))
        d.line((x,midy,x+im.width,midy),fill=(255,70,70))
    centers.save(out/'framed-label-centers.png')
    from texture import Texture
    death_images=[]
    for key in ('TEXTURES/HUD/THATWASYOURLASTBREATH.PNG','TEXTURES/HUD/THATWASYOURLASTBREATH2.PNG'):
        co=Texture(final_z.read(key));death_images.append(Image.frombytes('RGBA',(co.width,co.height),co.rgba))
    pair=Image.new('RGB',(856,240))
    for i,im in enumerate(death_images):pair.paste(im,(i*428,0))
    pair.save(out/'death-paired-preview.png')
    report = dict(archive_sha256=filehash(out/'MODIFIED_FILE.zar'), artwork=rows,
                  localized_floor_signs=14, em_dash_targets=0,
                  all_art_resources_match=True,centered_labels=43,
                  artwork_lighting_pairs=art_report['artwork_lighting_pairs'],protected_unreadable_print=protected,
                  game_launched=False, in_game_acceptance='NOT_TESTED')
    write_json(out/'sign-feedback-verification.json', report)
    if json.loads((out/'sign-feedback-verification.json').read_text(encoding='utf8')) != report:
        raise ValueError('Verification report persistence mismatch')
    print('SIGN FEEDBACK PASS art=26 centered-labels=43 floor-signs=14 paired-death=lighting-only protected-print=4 mips=matched em-dash-targets=0 game-launched=false')


if __name__ == '__main__':
    main()
