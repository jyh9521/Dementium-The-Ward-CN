"""Apply reviewed source-dependent artwork deltas to verified image resources.

The XOR delta primitive is an exact MIT source copy of Dementium-II-CN
c0ea10f93450972841e510ff82913920339bd058 tools/art_delta.py (jyh9521).
This adapter independently binds container hashes and rebuilds all mip levels.
No source or generated whole image is required in the repository.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from art_delta import apply
from engine_image import EngineImage
from texture import Texture
from center_artwork import verify_alignment
from paired_artwork import lighting_variant


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _validate_art(original, edited, patch, alpha_policy='preserve-source'):
    if original.size != edited.size or original.mode != 'RGBA' or edited.mode != 'RGBA':
        raise ValueError('Artwork dimensions/mode mismatch')
    if alpha_policy not in ('preserve-source','reviewed-regions'):
        raise ValueError('Unknown artwork alpha policy')
    if alpha_policy=='preserve-source' and original.getchannel('A').tobytes() != edited.getchannel('A').tobytes():
        raise ValueError('Reviewed artwork changed source alpha')
    mask = Image.new('L',original.size)
    boxes = patch.get('reviewed_regions')
    if not boxes:
        raise ValueError('Artwork lacks reviewed regions')
    for box in boxes:
        if (not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box) or
                not 0<=box[0]<box[2]<=original.width or not 0<=box[1]<box[3]<=original.height):
            raise ValueError('Artwork reviewed rectangle outside resource')
        ImageDraw.Draw(mask).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=255)
    for box in patch.get('protected_regions',[]):
        if (not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box) or
                not 0<=box[0]<box[2]<=original.width or not 0<=box[1]<box[3]<=original.height):
            raise ValueError('Artwork protected rectangle outside resource')
        if original.crop(box).tobytes()!=edited.crop(box).tobytes():
            raise ValueError('Artwork changed protected source pixels')
    changed=0
    for a,b,ok in zip(original.get_flattened_data(),edited.get_flattened_data(),mask.get_flattened_data()):
        if a!=b:
            if not ok:raise ValueError('Artwork changed pixels outside reviewed regions')
            changed+=1
    return changed


def _scaled_regions(regions, original_size, level_size):
    w,h=original_size;lw,lh=level_size
    return [[box[0]*lw//w,box[1]*lh//h,
             (box[2]*lw+w-1)//w,(box[3]*lh+h-1)//h] for box in regions]


def rebuild_mips(resource, edited, *, alpha_policy='preserve-source', regions=None):
    """Regenerate the reviewed region in every mip; retain all other source pixels.

    ``preserve-source`` retains every original alpha byte. ``reviewed-regions``
    allows alpha edits only inside explicitly reviewed rectangles, projected by
    floor/ceil integer coverage into each mip. Complete original mip allocations
    are serialized, including unchanged padding and out-of-region pixels. A no-op
    preserves the original compressed bytes and engine-authored lower mipmaps.
    """
    w,h,_=resource.levels[0]
    original=Image.frombytes(resource.mode,(w,h),resource.level_pixels()).convert('RGBA')
    if edited.mode!='RGBA' or edited.size!=(w,h):
        raise ValueError('Mipmap base image dimensions/mode mismatch')
    regions=regions or [[0,0,w,h]]
    _validate_art(original,edited,dict(reviewed_regions=regions),alpha_policy)
    if resource.mode=='RGB' and edited.getchannel('A').getextrema()!=(255,255):
        raise ValueError('RGB resource cannot encode reviewed transparency')
    if edited.tobytes()==original.tobytes():
        return resource.rebuild(),dict(mip_levels=len(resource.levels),all_mips_regenerated=False,
                                       allocation_padding_preserved=True,alpha_policy=alpha_policy,
                                       alpha_preserved=True,noop_byte_identical=True,
                                       outside_reviewed_regions_unchanged=True)
    pixels=bytearray(resource.pixels)
    expected=[];level_regions=[]
    for level,(lw,lh,offset) in enumerate(resource.levels):
        generated=edited if level==0 else edited.resize((lw,lh),Image.Resampling.LANCZOS)
        source=Image.frombytes(resource.mode,(lw,lh),resource.level_pixels(level))
        image=source.convert('RGBA')
        boxes=_scaled_regions(regions,(w,h),(lw,lh));level_regions.append(boxes)
        for box in boxes:image.paste(generated.crop(box),(box[0],box[1]))
        if alpha_policy=='preserve-source' and resource.mode=='RGBA':
            image.putalpha(source.getchannel('A'))
        image=image.convert(resource.mode)
        visible=image.tobytes();expected.append(visible)
        stride=resource.allocations[level][0]*resource.bpp
        row_size=lw*resource.bpp
        for row in range(lh):
            start=offset+row*stride
            pixels[start:start+row_size]=visible[row*row_size:(row+1)*row_size]
    encoded=resource.write(bytes(pixels))
    check=EngineImage(encoded,resource.prefix_size)
    if check.fields!=resource.fields or check.prefix!=resource.prefix:
        raise ValueError('Artwork mip metadata/prefix changed')
    if any(check.level_pixels(i)!=value for i,value in enumerate(expected)):
        raise ValueError('Artwork mip verification failed')
    return encoded,dict(mip_levels=len(expected),all_mips_regenerated=True,
                        allocation_padding_preserved=True,alpha_policy=alpha_policy,
                        alpha_preserved=alpha_policy=='preserve-source',noop_byte_identical=False,
                        outside_reviewed_regions_unchanged=True,mip_reviewed_regions=level_regions)


def build_art(z,c,config_path):
    """Return (inner resource replacements, outer replacements, verification report)."""
    path=Path(config_path).resolve()
    config=json.loads(path.read_text(encoding='utf-8'))
    if config.get('schema')!=1 or not isinstance(config.get('patches'),list):
        raise ValueError('Unsupported artwork configuration')
    inner={};outer={};records=[];preserved=[];paired=[]
    protected=set()
    for entry in config.get('preserve_source',[]):
        scope=entry['scope'];name=entry['resource']
        if scope not in ('inner','outer') or (scope,name) in protected:
            raise ValueError('Invalid or duplicate artwork source preservation entry')
        protected.add((scope,name))
        raw=(c if scope=='inner' else z).read(name)
        if _sha(raw)!=entry['source_sha256']:
            raise ValueError('Preserved artwork source hash mismatch: '+name)
        preserved.append(dict(scope=scope,resource=name,source_sha256=_sha(raw),
                              disposition='original-resource-byte-identical',reason=entry['reason']))
    for entry in config['patches']:
        scope=entry['scope'];name=entry['resource'];relative=Path(entry['patch'])
        if (scope,name) in protected:
            raise ValueError('Artwork patch conflicts with required source preservation: '+name)
        if relative.is_absolute() or '..' in relative.parts or relative.suffix!='.json':
            raise ValueError('Artwork patch path must remain relative to locale configuration')
        patch_path=(path.parent/relative).resolve()
        if path.parent not in patch_path.parents:
            raise ValueError('Artwork patch path escapes locale directory')
        patch=json.loads(patch_path.read_text(encoding='utf-8'))
        if patch.get('resource')!=name:raise ValueError('Artwork delta resource mismatch')
        if scope not in ('inner','outer'):raise ValueError('Unknown artwork resource scope')
        changes=inner if scope=='inner' else outer
        if name in changes:raise ValueError('Duplicate artwork resource')
        raw=(c if scope=='inner' else z).read(name)
        actual=_sha(raw)
        if actual!=entry['source_sha256']:raise ValueError('Artwork container source hash mismatch: '+name)
        prefix=entry.get('prefix_size',0)
        if scope=='inner':
            codec=EngineImage(raw,prefix)
            w,h,_=codec.levels[0]
            original=Image.frombytes(codec.mode,(w,h),codec.level_pixels()).convert('RGBA')
        else:
            if prefix!=0:raise ValueError('Outer texture cannot have an engine Image prefix')
            codec=Texture(raw,expected_sha256=entry['source_sha256'],expected_header=entry.get('header_words',(122,32)))
            original=Image.frombytes('RGBA',(codec.width,codec.height),codec.rgba)
        edited=apply(original,patch)
        aligned_labels=verify_alignment(edited,patch)
        if 'pair' in patch:paired.append((patch['pair'],edited))
        alpha_policy=entry.get('alpha_policy',patch.get('alpha_policy','preserve-source'))
        changed=_validate_art(original,edited,patch,alpha_policy)
        if scope=='inner':encoded,extra=rebuild_mips(codec,edited,alpha_policy=alpha_policy,regions=patch['reviewed_regions'])
        else:
            encoded=codec.rebuild(edited.tobytes(),expected_sha256=actual)
            if Texture(encoded).rgba!=edited.tobytes():raise ValueError('Outer artwork texture verification failed')
            extra=dict(mip_levels=1,all_mips_regenerated=False,alpha_policy=alpha_policy,
                       alpha_preserved=original.getchannel('A').tobytes()==edited.getchannel('A').tobytes(),
                       outside_reviewed_regions_unchanged=True,noop_byte_identical=encoded==raw)
        changes[name]=encoded
        records.append(dict(resource=name,scope=scope,source_sha256=actual,
                            output_sha256=_sha(encoded),source_pixels_sha256=patch['source_pixels_sha256'],
                            output_pixels_sha256=patch['output_pixels_sha256'],changed_pixels=changed,
                            aligned_labels=aligned_labels,
                            dimensions_unchanged=True,**extra))
    pair_checks=[]
    if paired:
        if len(paired)!=2:raise ValueError('Artwork lighting pair must contain two states')
        canonical=next((v for v in paired if v[0]['role']=='canonical'),None)
        variant=next((v for v in paired if v[0]['role']=='derived-lighting-only'),None)
        if canonical is None or variant is None:raise ValueError('Artwork lighting pair roles mismatch')
        metadata,source=canonical;other,target=variant
        if metadata['canonical_pixels_sha256']!=other['canonical_pixels_sha256']:
            raise ValueError('Artwork pair has independent geometry')
        expected,mask=lighting_variant(source,metadata['lighting_box'],metadata['lighting_gains'])
        if expected.tobytes()!=target.tobytes() or _sha(mask.tobytes())!=metadata['reflectance_mask_sha256']:
            raise ValueError('Artwork pair differs by more than shared lighting/gloss')
        pair_checks.append(dict(common_geometry=True,derived_lighting_exact=True,
                                top_text=metadata['top_text'],bottom_text=metadata['bottom_text']))
    return inner,outer,dict(schema=1,images=records,image_count=len(records),inner_count=len(inner),
                            outer_count=len(outer),preserved_sources=preserved,
                            centered_labels=sum(r['aligned_labels'] for r in records),artwork_lighting_pairs=pair_checks,
                            verification='offline source-dependent art and complete mipmap rebuild; no game launch')
