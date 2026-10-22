# Installed font input for the minimal experiment

## Verified (2026-10-23)

- `tools/font_source.py` reuses `font_metadata`, `discover`, and `resolve_fonts` verbatim from `jyh9521/Dementium-II-CN` commit `c0ea10f93450972841e510ff82913920339bd058`, `tools/font_pipeline.py`. Only the import is adapted from `localize.filehash` to this project's `zar.filehash`. Upstream MIT attribution is retained in the module; project `LICENSE` supplies the license terms.
- `locales/zh-CN/font-profile.json` contains only the body role at 12 px. No upstream game resources, title aliases, title routes, UI metrics, or native offsets are copied.
- The installed file `fusion-pixel-12px-proportional-zh_hans.ttf` resolves under `%LOCALAPPDATA%/Microsoft/Windows/Fonts`. SHA-256: `60f62ae34b95eea47e5986dd425bcd51c4f785165bf06befade60a059f036066`, matching the upstream body profile exactly.
- Font names: Fusion Pixel 12px Prop zh-Hans / Regular; version 2026.10.16; weight 400; 1200 units/em; 37689 cmap entries; TrueType `glyf` outlines. The installed font metadata names TakWolf as copyright holder and SIL Open Font License 1.1 as the license.
- The installed font cmap covers 新 (U+65B0), 游 (U+6E38), 戏 (U+620F). Pillow 12.2.0 successfully rendered these three characters at 12 px. fontTools version: 4.63.0.
- `assets/fonts/Fusion-Pixel-OFL.txt` is an unchanged copy of the upstream license notice, including the attribution and complete OFL 1.1 terms. It is not a font file. No font binary is added to this repository, downloaded, or installed.

## Reproduction and limits

Use `resolve_fonts(json.loads(Path('locales/zh-CN/font-profile.json').read_text('utf-8')))` with `tools` on `sys.path`. Resolution fails on missing filenames or SHA mismatch instead of silently accepting another font version.

Ignored local evidence: `build/phase2/research/font_source_identity.json` records the resolved path and full names/metadata; `build/phase2/research/chinese_glyphs.png` previews only 新游戏, rendered at 12 px then nearest-neighbor enlarged 8x for inspection. This proves input identity, cmap availability and offline rasterization, not game text decoding, binary font consumption, or in-game visual quality. Those require separate format and runtime evidence.

Tests: `python -m unittest discover -s tests -p test_font_source.py -v` covers hash-verified resolution, case-insensitive basename matching, missing input, changed input and the body-only locale profile. The tests use synthetic files and do not depend on installed commercial or open fonts.

## Appended binfont generation

`tools/build_font.py:build_font(original_binfont, mapping, profile)` takes source Unicode scalar values mapped to explicitly allocated runtime BMP glyph slots. It does not choose a text encoding or guess runtime character decoding. Body cell size and advance are locale-profile data (12 x 15 cells, advance 12 in this experiment). The atlas width stays unchanged; appended rows begin immediately below the original atlas; height grows to the next sufficient power of two, with a hard 1024 limit for the ten-bit glyph-coordinate fields. Every existing glyph metric and its extracted pixels, the complete original atlas RGBA prefix and the original base_height are verified unchanged after binary serialization and reparsing.

Input failures include duplicate/occupied slots, invalid source scalars/runtime slots, missing cmap entries, empty rendered glyphs, clipping, invalid metrics and atlas overflow. The report records source font identity, mapping, per-glyph ink rectangles and pixel counts, atlas dimensions and preservation checks. `tests/test_build_font.py` supplies nine synthetic tests, including preservation and rejection paths; it mocks font loading and requires no installed font.

An additional local-only check used the installed hash-verified Fusion Pixel font and `build/phase2/research/original.binfont`: original 128 x 256 atlas, 180 glyphs, base_height 8; appended atlas 128 x 512; each of the three glyphs had ink box [0, 3, 11, 14] inside a 12 x 15 cell. Ink counts: 新 54, 游 51, 戏 44. Outputs `font_build_check.binfont`, `font_build_check.json` and `font_build_check.png` remain ignored research evidence. The provisional empty-slot choice in that research check is not a claim about the runtime decoder; the integrated experiment must use slots supported by separate executable evidence.

The serialized base_height=8 is not the final runtime line spacing; the audited parent initializer sets Font+0x818 to 13. This experiment does not change either initialization path.
