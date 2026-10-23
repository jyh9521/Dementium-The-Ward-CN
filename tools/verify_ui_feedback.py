"""Replay the shipped feedback fixes without starting the game or changing inputs."""
import argparse
import json
import sys
from pathlib import Path
from audio_subtitles import NativeOverlayReplay
from debug_menu import rollback_debug
from movie_overlay import rollback_movie_overlay
from source_delta import filehash
from workspace_io import validate_output_tree

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    out = args.build.resolve()
    if not out.is_relative_to(ROOT / 'build'):
        raise ValueError('Output must stay under repository build/')
    validate_output_tree(out)
    source = args.game / 'Dementium.exe'
    original_sha = filehash(source)
    target = out / 'MODIFIED_EXECUTABLE.exe'
    target_sha = filehash(target)
    recipe = json.loads((out / 'DIFF_FILE.json').read_text(encoding='utf-8'))
    data = target.read_bytes()
    if recipe['movie_overlay']:
        data = rollback_movie_overlay(data, recipe['movie_overlay'])
    if recipe['debug_menu']:
        data = rollback_debug(data, recipe['debug_menu'])
    overlay = recipe['audio_overlay']
    row = overlay['rows'][0]
    event = dict(cue_id=row['cue_id'], sample_rate=row['sample_rate'],
                 position=(row['start'] + row['end']) / 2)
    later = next((r for r in overlay['rows'] if r['cue_id'] == row['cue_id'] and r['start'] > row['start']), row)
    later_event = dict(event, position=(later['start'] + later['end']) / 2)
    last = max(r['end'] for r in overlay['rows'] if r['cue_id'] == row['cue_id'])
    cases = [
        ('duplicate', [event, event], {}, 1),
        ('phase-different', [event, later_event], {}, 1),
        ('gap-first', [dict(event, position=last + .1), event], {}, 1),
        ('modal-open', [event], dict(modal=True), 0),
        ('modal-close-current', [later_event], dict(modal='closed'), 1),
        ('muted', [event], dict(muted=True), 0),
        ('master-zero', [event], dict(master_gain=0.), 0),
        ('channel-zero', [dict(event, gain=0.)], {}, 0),
        ('no-mixer-slot', [dict(event, mixer_active=False)], {}, 0),
        ('scheduled-future', [dict(event, scheduled=2.)], {}, 0),
        ('paused', [dict(event, paused=True)], {}, 0),
        ('stopped', [dict(event, stopped=True)], {}, 0),
    ]
    rows = []
    for base in (0x140000000, 0x150000000):
        replay = NativeOverlayReplay(source, data, overlay, image_base=base)
        for name, events, options, expected in cases:
            calls = replay.render(events, **options)
            expected_text = later['text'] if name == 'modal-close-current' else row['text']
            if len(calls) != expected or (expected and calls[0]['text'] != expected_text):
                raise ValueError((name, calls, expected))
            rows.append(dict(case=name, base=hex(base), expected=expected, calls=calls))
    if filehash(source) != original_sha or filehash(target) != target_sha:
        raise ValueError('Input changed')
    message = f'FEEDBACK PASS cases={len(rows)} bases=2 duplicate=1 modal=0 close=current gap-first=1 inaudible=0 inputs=unchanged game-launched=false'
    report = dict(command=[sys.executable, *sys.argv], stdout=message+'\n', exit_status=0,
                  executable_sha256=target_sha, original_sha256=original_sha,
                  cases=rows, game_launched=False, inputs_unchanged=True)
    (out / 'feedback-replay.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(message)


if __name__ == '__main__':
    main()
