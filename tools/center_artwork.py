"""Position existing painted artwork by its visible ink, never by crop padding.

Authoring only: restoration plates come from reviewed image edits. The resulting
source-dependent delta is sufficient for clean release builds without these PNGs.
"""
from PIL import Image, ImageFilter
from art_delta import apply, capture, sha
from build_image_text import checked_box


def foreground(image, palette):
    def selected(p):
        r, g, b, _ = p
        if palette == 'ivory': return g > 110 and b > 85 and r < g*1.6 and r > 110
        if palette == 'brown': return r > g*1.23 and r > b*1.2 and g < 115
        if palette == 'red': return r > g*1.5 and r > b*1.4 and r > 80
        if palette == 'green': return g > r*1.18 and g > b*1.05 and g > 65
        if palette == 'blue': return b > r*1.13 and b > g*1.01 and b > 65
        if palette == 'dark-blue': return b > r*1.18 and b > g*.8 and r < 105
        if palette == 'black': return r < 65 and g < 45 and b < 45
        if palette == 'yellow': return r > 125 and g > 125 and b < 135
        if palette == 'green-letter': return g > 105 and g > r*1.35 and g > b*1.08
        if palette == 'blue-letter': return b > 170 and g > 110 and b > r*1.25 and g > r*1.1
        if palette == 'dark-red': return r < 170 and g < 20 and b < 20
        raise ValueError('Unknown artwork palette')
    mask = Image.new('L', image.size)
    mask.putdata([255 if selected(p) else 0 for p in image.get_flattened_data()])
    return mask


def center_box(ink_size, frame):
    w, h = ink_size
    x0, y0, x1, y1 = frame
    if w > x1-x0 or h > y1-y0:
        raise ValueError('Artwork ink exceeds frame')
    left, top = x0+(x1-x0-w)//2, y0+(y1-y0-h)//2
    return [left, top, left+w, top+h]


def component_bounds(mask):
    """Ignore isolated patina specks when measuring; keep original glyph pixels."""
    w,h=mask.size
    points={(x,y) for y in range(h) for x in range(w) if mask.getpixel((x,y))}
    groups=[]
    while points:
        seed=points.pop();group={seed};pending=[seed]
        while pending:
            x,y=pending.pop()
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
                q=(x+dx,y+dy)
                if q in points:points.remove(q);group.add(q);pending.append(q)
        groups.append(group)
    if not groups:return None
    largest=max(map(len,groups))
    cutoff=max(2,min(6,largest//15)) if w*h>450 else 1
    kept=[q for g in groups if len(g)>=cutoff for q in g]
    if not kept:return mask.getbbox()
    return min(x for x,y in kept),min(y for x,y in kept),max(x for x,y in kept)+1,max(y for x,y in kept)+1


def center_artwork(original, base, plate, labels, plate_sha):
    current = apply(original, base)
    result = current.copy()
    background = plate.convert('RGBA').resize(original.size, Image.Resampling.LANCZOS)
    regions = list(base['reviewed_regions'])
    records = []
    for label in labels:
        search = checked_box(label['search'], original.size)
        clear = checked_box(label['clear'], original.size)
        frame = checked_box(label['frame'], original.size)
        mask = foreground(current.crop(search), label['palette'])
        bounds = component_bounds(mask)
        if bounds is None:
            raise ValueError('Artwork ink was not found: '+label['text'])
        source_box = [bounds[0]+search[0], bounds[1]+search[1],
                      bounds[2]+search[0], bounds[3]+search[1]]
        destination = center_box((source_box[2]-source_box[0], source_box[3]-source_box[1]), frame)
        # Keep a one-pixel fringe, including existing paint wear and antialiasing.
        full_mask = Image.new('L', original.size)
        full_mask.paste(mask, search[:2])
        fringe = full_mask.filter(ImageFilter.MaxFilter(3))
        pad = [max(clear[0],source_box[0]-1),max(clear[1],source_box[1]-1),
               min(clear[2],source_box[2]+1),min(clear[3],source_box[3]+1)]
        dx, dy = destination[0]-source_box[0], destination[1]-source_box[1]
        shifted = [pad[0]+dx,pad[1]+dy,pad[2]+dx,pad[3]+dy]
        if not (clear[0] <= shifted[0] < shifted[2] <= clear[2] and
                clear[1] <= shifted[1] < shifted[3] <= clear[3]):
            # Fringe must never move over an original frame edge or screwhead.
            pad = source_box
            shifted = destination
        if not (clear[0] <= shifted[0] < shifted[2] <= clear[2] and
                clear[1] <= shifted[1] < shifted[3] <= clear[3]):
            raise ValueError('Centered artwork leaves reviewed interior: '+label['text'])
        result.paste(background.crop(clear), clear[:2])
        result.paste(current.crop(pad), shifted[:2], fringe.crop(pad))
        regions.append(list(clear))
        records.append(dict(text=label['text'], frame_box=list(frame),
                            source_ink_box=source_box, ink_box=destination,
                            center_error=[(destination[0]+destination[2]-frame[0]-frame[2])/2,
                                          (destination[1]+destination[3]-frame[1]-frame[3])/2],
                            glyph_source='existing painted artwork pixels, no font redraw'))
    # Restore every protected original pixel, including unreadable print/blood.
    for box in base.get('protected_regions', []):
        result.paste(original.crop(box), tuple(box[:2]))
    result.putalpha(original.getchannel('A'))
    patch = dict(base)
    patch.update(capture(original,result,resource=base['resource'],
                         prompt=base['prompt']+' Reposition existing painted glyphs by visible-ink bounds relative to surveyed original frames.',
                         regions=regions))
    patch['alignment'] = dict(method='visible painted-ink bounding box; integer native-pixel centering',
                              maximum_center_error_pixels=.5, restoration_plate_sha256=plate_sha,
                              labels=records)
    for row in records:
        row['output_frame_pixels_sha256'] = sha(result.crop(row['frame_box']).tobytes())
    return patch,result


def verify_alignment(image, patch):
    report=patch.get('alignment')
    if not report:return 0
    for row in report['labels']:
        frame=checked_box(row['frame_box'],image.size)
        ink=checked_box(row['ink_box'],image.size)
        errors=[(ink[0]+ink[2]-frame[0]-frame[2])/2,
                (ink[1]+ink[3]-frame[1]-frame[3])/2]
        if errors!=row['center_error'] or max(map(abs,errors))>.5:
            raise ValueError('Artwork visible ink is not centered: '+row['text'])
        if sha(image.crop(frame).tobytes())!=row['output_frame_pixels_sha256']:
            raise ValueError('Centered artwork frame pixels changed: '+row['text'])
    return len(report['labels'])
