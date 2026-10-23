# Additional engine Image formats

Verified against original EXE SHA-256
`26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`.
The read-only adapter `tools/engine_image_extra.py` supplements, rather than
changes, the established format-0/1 `EngineImage` implementation.

## Verified native conversion

Image loader RVA E9EE0 obtains the format from the first uint16, the dimensions
from +4/+6 and allocation dimensions from +8/+A. It inflates the existing nested
zlib frames and calls F9340 with RCX=image object, RDX=decoded source bytes,
R8d=format. F9340 creates/locks a GPU image and converts only the base allocation
width*height. It does not traverse the resource's other mip bytes on this route.
After the conversion, the F9340 tail at F995D checks/sets the texture's +A4 generated flag
and calls backend 1EACF0 to generate mipmaps. Thus the audited PC path regenerates
its mip chain from the uploaded base instead of uploading the stored tail.

* Format **5**: F9790 reads two bytes, advances source by two, copies byte 0 to
  output B/G/R and byte 1 to alpha. This is 8-bit luminance plus 8-bit alpha,
  **not** RGBA4444, RGB565, or compressed texture blocks.
* Format **8**: F9651 reads one byte and copies it to all four output bytes.
  The source byte supplies both luminance and alpha, **not** an RGB-only gray
  conversion or palette index.

The adapter executes the original F9768..F97BD or F9635..F9679 loop instructions
in Unicorn with synthetic source/output/pitch memory. Every resulting output
byte must equal the adapter's conversion. It neither launches an executable
process nor creates a graphics context. Image locking and upload are explicit
unexecuted boundaries, not GPU acceptance.

## Remaining three resources

| Resource | Format | Dimensions | Raw bytes | Base bytes | Visual review |
|---|---:|---|---:|---:|---|
| art/flares.art | 5 | 128x32 | 8192 | 8192 | Four rings/light blobs, no text |
| art/sunglow.art | 5 | 32x32 | 2048 | 2048 | Radial corner gradient, no text |
| art/splat01.art | 8 | 64x64 | 5440 | 4096 | Alpha splatter, no text |

All three decode with exact native output comparison and byte-identical no-op
rebuild. All have been viewed against black, gray and light backgrounds.
Splat01's header has mip field 3 and count 5376 (=4096+1024+256), but its payload
contains 5440 bytes. Additional views partitioning all remaining bytes as 32x32,
16x16 and 8x8 grayscale images show progressively reduced splatter patterns and
no text. The first two agree with the declared count; the final 64 bytes do not.

High-confidence deduction: these are downsampled image levels. **Unverified**:
why the final 8x8 allocation is excluded from the count, and whether any other
platform/backend consumes it. The adapter preserves the entire source, exposes
all trailing bytes as `tail`, and offers no writer. It does not silently add a
mipmap or rewrite the inconsistent count. This ambiguity does not prevent exact
base-level display or complete byte-level visual inspection of these originals.

## Reproduction

```powershell
python tools/engine_image_extra.py --game 'C:\Program Files (x86)\Steam\steamapps\common\Dementium - The Ward' --out build/full-research/extra-images
python -m unittest discover -s tests -p test_engine_image_extra.py -v
```

The first command reports `{"images": 3, "native_match": true}`. Local report
and PNG previews are ignored build outputs. Source game assets remain unchanged;
no complete original assets belong in Git. The original format-0/1 image audit
plus these three adapters removes the 3-image unsupported-format coverage gap.

Combined coverage is **507/507 base image layers readable and visually audited**;
this is offline asset inspection, not proof of every in-game render.
The three original file SHA-256 identities are:

* flares.art: `e0c2feab3b4b5cf30c57cba5fb6d9bc37ff15b08b6d2b2d48f17be142710af4d`
* splat01.art: `169555f841d6fbc351c419569ac7d2e5821ca7693a84c62351513cbddb2274c5`
* sunglow.art: `5671f6cbf7e5743ed40aa591ce9bf3af9e3a2f23439ff4116cf4b745fd3854ed`

The adapter's `rebuild()` returns the original byte string unchanged, including
every header, compressed byte, padding byte and uninterpreted trailing pixel.
The audit asserts this equality for each input; there is no mutation command.
