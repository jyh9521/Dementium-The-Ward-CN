"""Installed font input, reused from Dementium-II-CN font_pipeline.py.

Upstream c0ea10f93450972841e510ff82913920339bd058; MIT,
Copyright (c) 2026 jyh9521. No game resource names or native patches.
font_metadata, discover and resolve_fonts are verbatim function copies.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
from zar import filehash


def font_metadata(path):
    from fontTools.ttLib import TTFont
    with TTFont(path) as font:
        names = {str(i): list(dict.fromkeys(n.toUnicode() for n in font['name'].names if n.nameID == i))
                 for i in (0, 1, 2, 5, 6, 13, 14)}
        return dict(file=Path(path).name, sha256=filehash(Path(path)), format=font.sfntVersion,
                    names=names, weight=font['OS/2'].usWeightClass, units_per_em=font['head'].unitsPerEm,
                    cmap_count=len(font.getBestCmap()), outline_tables=[t for t in ('glyf', 'CFF ', 'CBDT', 'EBDT') if t in font])


def discover():
    roots = [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts',
             Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'Microsoft/Windows/Fonts']
    candidates = set()
    for root in roots:
        if root.exists():
            candidates.update(p.resolve() for p in root.iterdir() if p.suffix.lower() in ('.ttf', '.otf', '.ttc')
                              and re.search(r'fusion|chillbitmap', p.name, re.I))
    if os.name == 'nt':
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            with winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    name, value, _ = winreg.EnumValue(key, i)
                    if not re.search(r'fusion|chillbitmap|寒蝉点阵|缝合像素', name, re.I):
                        continue
                    for p in [Path(value), *(root / value for root in roots)]:
                        if p.is_file():
                            candidates.add(p.resolve())
    return sorted(candidates)


def resolve_fonts(profile):
    candidates = discover()
    selected = {}
    for role, spec in profile['fonts'].items():
        hits = [p for p in candidates if p.name.casefold() == spec['file'].casefold()]
        if not hits:
            raise ValueError('Installed font not found: ' + spec['file'])
        path = next((p for p in hits if filehash(p) == spec['sha256']), None)
        if path is None:
            raise ValueError('Installed font identity changed: ' + spec['file'])
        selected[role] = path
    return selected
