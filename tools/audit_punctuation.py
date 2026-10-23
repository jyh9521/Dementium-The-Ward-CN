"""Audit terminal stops only in explicitly classified non-narrative resources.

Classification and preserved-record fingerprints belong to the locale policy,
not this generic Unicode punctuation implementation. No binary inputs are read.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata


def target_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def without_terminal_stop(text):
    """Preserve every byte-equivalent character except one eligible final stop.

    CR/LF, whitespace and engine C0 controls are not punctuation. A heading
    separated by a blank line is not part of the description sentence. A dot
    directly before a digit is a numeric decimal separator (.357), not a clause.
    """
    visible = [(i, c) for i, c in enumerate(text) if not c.isspace() and ord(c) >= 32]
    if not visible or visible[-1][1] not in ('。', '.'):
        return text
    terminal = visible[-1][0]
    body = text[:terminal]
    # Remove only a one-line heading from the predicate, never from the output.
    paragraphs = body.replace('\r\n', '\n').replace('\r', '\n').split('\n\n', 1)
    if (len(paragraphs) == 2 and '\n' not in paragraphs[0]
            and not any(unicodedata.category(c).startswith('P') for c in paragraphs[0])):
        body = paragraphs[1]
    for i, char in enumerate(body):
        if unicodedata.category(char).startswith('P'):
            if char == '.' and i + 1 < len(body) and body[i + 1].isdigit():
                continue
            return text
    return text[:terminal] + text[terminal + 1:]


def audit(locale_dir, policy):
    records = []
    for filename in policy['record_files']:
        for row in json.loads((Path(locale_dir) / filename).read_text(encoding='utf-8')):
            records.append((filename, row))
    classified = policy['resources']
    actual = {row['resource'] for _, row in records}
    if actual != set(classified):
        raise ValueError('Resource classification drift')
    changes = []
    for filename, row in records:
        if classified[row['resource']] in policy['eligible_categories']:
            after = without_terminal_stop(row['target'])
            if after != row['target']:
                changes.append(dict(file=filename, id=row['id'], before=row['target'], after=after))
    targets = {row['id']: row['target'] for _, row in records}
    for key, expected in policy['preserved_targets'].items():
        if target_hash(targets[key]) != expected:
            raise ValueError('Protected narrative/document target changed: ' + key)
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--locale-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'locales/zh-CN')
    args = parser.parse_args()
    policy = json.loads((args.locale_dir / 'punctuation-style.json').read_text(encoding='utf-8'))
    changes = audit(args.locale_dir, policy)
    print(json.dumps(dict(pending_terminal_stops=len(changes), protected_targets=len(policy['preserved_targets']), changes=changes), ensure_ascii=False, indent=2))
    return 1 if changes else 0


if __name__ == '__main__':
    raise SystemExit(main())
