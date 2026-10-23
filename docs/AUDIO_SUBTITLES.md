# Native audio subtitle overlay

## Status and boundaries

Verified offline against the Steam PC executable SHA-256
`26186ceb1142e1c84298aa528627531e3821b8068e4e777e3975403a272c530e`
(4,673,536 bytes). The installation is read-only input. No game process has
been launched. Instruction replay is not in-game acceptance or GPU validation.

`tools/audio_subtitles.py` generates a copied executable with an additional RX
`.locsub` section and a guarded HUD call. Locale text and timing remain in
`locales/<locale>/audio-subtitles.json`; generic code has no Chinese literals.
The native table is generated from this source at build time. `build_resource`
also serializes a portable `SUB1` resource, but this patch does **not** dynamically
load that external resource: catalog edits require rebuilding the executable.
Audio files are neither replaced nor synthesized.

## Verified native audio route

All addresses below are RVAs for this exact build, not offsets imported from
Dementium II. `FD730(RCX=wrapper, EDX=cue ID)` allocates a 0x100-byte sound record,
inserts it into the doubly linked active list at `C14E20`, and calls `FA990`.
`FA990(RCX=record, EDX=cue ID)` writes the ID at record+0 and dispatches to
`FDA70(RCX=record, RDX=ASCII leaf path, R8b=loop)`; the latter constructs `/sfx/`
plus the leaf into the record's pending resource string at +18. `FD620` stops
playback; it is not a playback entry.

Original dispatcher instruction replay confirms these mappings:

| Resource | Cue ID | Native loop |
|---|---:|---|
| SFX/EMERGENCY/EMERGENCY_01_MONOMIX_8HZ_8BIT.FLAC | 0100001F | yes |
| SFX/SINGING/SINGING_8HZ_8BIT.FLAC | 01000028 | no |
| SFX/ENEMYBT/TALK01LO.FLAC .. TALK05LO.FLAC | 01000070 .. 01000074 | no |

`FDC60` owns record updates. Record+C0 points to the PCM channel, whose +8
points to the buffer; buffer+28 is the source sample rate. Channel+60 is a
double source-sample position; +1 is paused, +30 stopped, +31 playing.
`1096A0` advances source position by sourceRate/48000 times pitch for each output
frame. `127950` sets the stopped/playing flags at non-looping EOF and resets
loop position at looping EOF. Captions therefore follow real source position,
including pause, pitch, stop and the complete clip loop period, rather than a
wall-clock estimate or the final subtitle cue's endpoint.

The mixer subtracts 100,000 from large sample positions. The current adapter
therefore rejects captioned clips unless original FLAC STREAMINFO confirms mono
and fewer than 100,000 samples. It also guards original audio hashes, duration,
sample rate, and audited cue mapping. All currently accepted speech clips meet
these conditions. Newly discovered playback IDs need independent verification;
they are rejected rather than silently ignored.

### Ownership and concurrency

Verified: mixer `1096A0` iterates a separate fixed 64-slot PCM table `C1A090`
(streaming table `C1A290`) under audio spinlock `C1AF90`, not the `C14E20` list.
Mixer-side channel deletion is conditional on channel+2E ownership. Channels
created for the inspected sound-record route have ownership+2E=0 and are freed
by main-logic `FDC60`, not the mixer. Original scene loader `3A420`, pause
`3CA80`, cinema suspension `BBF80`, and cleanup `FDBF0` iterate the same active
list without an independent list lock. Scene cleanup and stop remove/disable
native entries; the overlay caches neither pointers nor subtitle state.

High-confidence static deduction: list insertion/removal and HUD traversal use
the main-logic thread, consistent with the original unlocked iterators. This is
not a live scheduling proof. The overlay reads mixer-updated position and flags
without mutating them; a frame at a cue boundary may observe either adjacent
state. No lock is added to the original render/audio relationship.

## Guarded PE change and ABI

The builder first rolls back the supplied UTF-8 runtime recipe, verifies the
complete original hash, and reproduces `runtime_patch.patch_bytes` exactly.
It additionally checks original neighborhood RVA `BFE00..C0000` SHA-256:
`e20bb5539ce956169192cde63e489227e50d8bef7a74a95f683186f84b7617e4`.

The sole existing code hook is RVA `BFF10`, 14 original bytes:
`48 8B 05 59 57 2E 00 48 8D 0D 52 57 2E 00`.
These load the renderer global at `3A5670` into RAX and its address into RCX.
The patch CALLs the new function, JMPs to `BFF1E`, and pads four NOPs. The new
function restores those exact RAX/RCX semantics before the original epilogue.
All newly generated image references are PC-relative; no new imports are used.

The function saves RBX/RSI/RDI/RBP/R12..R15 and subtracts 0xE8 bytes. RDX/R8/R9/
R10/R11 are saved in the frame and restored. Native calls use Win64 shadow
space and alignment. The PE exception directory points to a copy of the entire
original function table plus the new runtime-function entry. New UNWIND_INFO
uses eight PUSH_NONVOL codes and ALLOC_LARGE(232), prologue length 19. Replay
checks saved values, return address, stack restoration and unwind frame layout.
ASLR replay relocates the image to `150000000` and produces identical captions.

Each HUD frame walks at most 1,024 list nodes and draws at most three concurrent
caption blocks. It rejects missing/stopped/paused/non-playing channels and a
sample-rate mismatch. Caption lines wrap against actual font metrics at 400
logical pixels; at most two lines are accepted. Blocks are centered at x=214,
y=160/186/212. Those coordinates still require human visual/clipping review.

### Text object lifetime

The 0x60-byte stack text object is a non-owning descriptor, not a heap object.
Patched `EA700` widens into original global buffer RVA `D1BC40`. It passes original
shared script storage RVA `3A83C0` to `EA950`, which resets the script command
count at +4 on each compile. `EA950` assigns object+48 to script storage and
object+50 to the wide string. Its only callees are `E9E10` measurement and
`2F410` diagnostic output; it has no allocator/deallocator calls. The original
HUD similarly compiles/draws stack temporaries without text destructors.
Caption compilation and drawing are synchronous; the next caption may reuse
the shared buffers after the previous draw returns.

Actual compiler replay with the 848-glyph full font ran 1,000 caption frames:
1,000 actual EA950 calls, zero calls to monitored game allocation/free entries
FF5B0/FFC30/3BF20/3BFE0, stable script counts for every cue. This establishes no
per-frame text allocation in this path. GPU submission is a boundary double;
this result does not establish renderer-driver resource lifetime.

## Reproduction and rollback API

```python
runtime, runtime_recipe = runtime_patch.patch_bytes(original)
modified, overlay_recipe = audio_subtitles.build_native_overlay(
    runtime, runtime_recipe, catalog, original_audio_members, full_font)
restored_runtime = audio_subtitles.rollback_overlay(modified, overlay_recipe)
assert restored_runtime == runtime
assert runtime_patch.rollback_bytes(restored_runtime, runtime_recipe) == original
```

The overlay recipe records original/modified whole-file hashes and sizes,
sparse pre-existing-byte runs (`offset`, `before`, `after`), appended section,
section/unwind RVAs and cue rows. Rollback checks modified identity and every
changed run, removes the appended data and confirms the runtime-only hash.
Unknown versions or modified inputs fail, and Steam files are never targets.

`python -m unittest discover -s tests -p test_audio_subtitles.py -v` passes five
tests, including real original dispatcher mapping, installed hook/decoder,
stop/pause/unknown ID/sample-rate/empty-list gates, three-block cap, ASLR,
unwind metadata/frame, actual compiler repeated lifetime and exact rollback.
`verify_overlay_font` additionally executes original E9980 loader, E9E10
measurement and EADC0 sprite dispatch for all current cues with the complete
79-page font. Loader sprite-constructor side effects and GPU submission are
explicit doubles, not visual acceptance.

Local evidence under ignored `build/full-research/audio-subtitles/` includes
`native-dispatch.json`, `native-replay.json`, `lifetime-replay.json`,
`MODIFIED_FILE.exe`, `DIFF_FILE.json`, and isolated `ROLLBACK_COPY.exe`.
Current research overlay SHA-256 is
`02ee5ef7378e39f00f6ece2b020243c1266c132f49924ee047e19cf472344d32`;
its isolated rollback reproduces runtime-only SHA-256
`5f2b955b9af968107cadb6af8ec5121be8dc39ae599b9b88cc215343035d007d`.
Later full builds may regenerate a different overlay as locale data changes.

## Remaining manual acceptance

Human testing must cover emergency looping and pause/resume, all boss lines,
the singing source, concurrent sounds, cutscene suspension, scene transitions,
aspect ratios and caption overlap with existing HUD/document screens. No such
in-game test has been performed by the tooling. Only the audited PCM route is
captioned; future streaming dialogue requires a separate adapter and tests.
