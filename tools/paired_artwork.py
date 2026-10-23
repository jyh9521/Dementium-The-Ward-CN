"""Derive lighting variants from ONE artwork without changing its geometry."""
from PIL import Image


def lighting_variant(canonical, box, gains):
    if len(gains) != 3 or any(not .1 <= v <= 2 for v in gains):
        raise ValueError('Invalid artwork lighting gains')
    out = canonical.copy()
    mask = Image.new('L', canonical.size)
    x0,y0,x1,y1=box
    if not 0<=x0<x1<=out.width or not 0<=y0<y1<=out.height:
        raise ValueError('Lighting region outside artwork')
    for y in range(y0,y1):
        for x in range(x0,x1):
            r,g,b,a=canonical.getpixel((x,y))
            # Ivory reflectance, not the red/black substrate. The same mask and
            # coordinates serve every variant; no original Latin-shaped field.
            weight=max(0,min(1,(min(g,b)-r*.25)/100))
            mask.putpixel((x,y),round(weight*255))
            values=[round(v*(1+weight*(gain-1))) for v,gain in zip((r,g,b),gains)]
            out.putpixel((x,y),(*[max(0,min(255,v)) for v in values],a))
    return out,mask
