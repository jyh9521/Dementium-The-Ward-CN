"""Defensive in-memory TAR adapter; never extract game paths to disk."""
from __future__ import annotations
import io
from pathlib import PurePosixPath
import re
import tarfile
from zar import digest


class Content:
    def __init__(self, data):
        self.data = data
        self.entries = {}
        previous_end = 0
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
            for entry in archive:
                name = entry.name
                if (not name or name.startswith('/') or '\\' in name or ':' in name
                        or '..' in PurePosixPath(name).parts or name in self.entries):
                    raise ValueError('Unsafe or duplicate TAR name')
                if not (entry.isfile() or entry.isdir()) or entry.pax_headers:
                    raise ValueError('Unsupported TAR entry type')
                if entry.offset_data != entry.offset + 512:
                    raise ValueError('Extended TAR headers unsupported')
                end = entry.offset_data + ((entry.size + 511) // 512) * 512
                if entry.offset < previous_end or end > len(data):
                    raise ValueError('Invalid TAR bounds')
                self.entries[name] = entry
                previous_end = end
        if not self.entries or len(data) % 512 or len(data) - previous_end < 1024 or any(data[previous_end:]):
            raise ValueError('Invalid TAR terminator/padding')
        self.end = previous_end

    def read(self, name):
        e = self.entries[name]
        return self.data[e.offset_data:e.offset_data + e.size]

    def rebuild(self, replacements):
        if set(replacements) - self.entries.keys():
            raise ValueError('Unknown TAR member')
        out = bytearray()
        for name, e in self.entries.items():
            end = e.offset_data + ((e.size + 511) // 512) * 512
            if name not in replacements or replacements[name] == self.read(name):
                out.extend(self.data[e.offset:end])
                continue
            if not e.isfile():
                raise ValueError('Cannot replace TAR directory')
            payload = replacements[name]
            if len(payload) >= 8 ** 11:
                raise ValueError('TAR size overflow')
            header = bytearray(self.data[e.offset:e.offset_data])
            header[124:136] = f'{len(payload):011o}\0'.encode('ascii')
            header[148:156] = b' ' * 8
            header[148:156] = f'{sum(header):06o}\0 '.encode('ascii')
            out.extend(header)
            out.extend(payload)
            out.extend(b'\0' * (-len(payload) % 512))
        out.extend(self.data[self.end:])
        result = bytes(out)
        parsed = Content(result)
        if list(parsed.entries) != list(self.entries):
            raise ValueError('TAR order changed')
        for name in self.entries:
            if parsed.read(name) != replacements.get(name, self.read(name)):
                raise ValueError('TAR payload verification failed')
        return result


def text_kind(name):
    if re.fullmatch(r'loc/[^/]+/[^/]+\.tbl', name):
        return 'table'
    if re.fullmatch(r'loc/[^/]+/(?:examine|item|open|unlock)\.\d+', name):
        return 'document'
    return None


TOKEN = re.compile(r'%[-+0 #]*\d*(?:\.\d+)?[sdifuxX]|\{[^{}]*\}|<[^<>]*>|\$[^\s$]+\$?|[\x00-\x08\x0b\x0c\x0e-\x1f]|\|')


def extract(content, locale='en', encoding='ascii'):
    """Explicit source encoding; Latin-1 lossless view is not a runtime codec claim."""
    records = []
    for name, entry in content.entries.items():
        kind = text_kind(name)
        if not kind or name.split('/')[1] != locale:
            continue
        raw = content.read(name)
        raw.decode(encoding, errors='strict')
        offset = 0
        for line, piece in enumerate(raw.splitlines(keepends=True) if kind == 'table' else [raw]):
            ending = b'' if kind == 'document' else next((e for e in (b'\r\n', b'\n', b'\r') if piece.endswith(e)), b'')
            body = piece[:-len(ending)] if ending else piece
            if body.strip():
                source = body.decode(encoding)
                records.append(dict(id=f'{name}:{line:04d}', resource=name, line=line,
                    offset=offset, tar_offset=entry.offset_data + offset, source=source,
                    source_bytes=len(body), resource_sha256=digest(raw), encoding=encoding,
                    kind=kind, target='', status='untranslated', capacity_bytes=None,
                    tokens=TOKEN.findall(source)))
            offset += len(piece)
    return records


def import_text(content, records, locale='en', encoding='ascii'):
    original = {r['id']: r for r in extract(content, locale, encoding)}
    seen = set()
    changes = {}
    for row in records:
        key = row['id']
        if key in seen or key not in original:
            raise ValueError('Duplicate/unknown record')
        seen.add(key)
        if any(row[k] != v for k, v in original[key].items() if k not in ('target', 'status')):
            raise ValueError('Stale source or metadata')
        target = row['target']
        if not target:
            continue
        if '\0' in target or TOKEN.findall(target) != row['tokens']:
            raise ValueError('Protected token mismatch')
        if row['kind'] == 'table' and ('\n' in target or '\r' in target):
            raise ValueError('Table row count change')
        if row['kind'] == 'document' and re.findall(r'\r\n|\r|\n', target) != re.findall(r'\r\n|\r|\n', row['source']):
            raise ValueError('Document line endings changed')
        changes.setdefault(row['resource'], []).append((row, target.encode(encoding, errors='strict')))
    if seen != original.keys():
        raise ValueError('Missing source records')
    result = {}
    for name, rows in changes.items():
        raw = content.read(name)
        for row, value in sorted(rows, key=lambda x: x[0]['offset'], reverse=True):
            start = row['offset']
            raw = raw[:start] + value + raw[start + row['source_bytes']:]
        if raw != content.read(name):
            result[name] = raw
    return result


def verify_index(zar, external):
    from zar import index_rows
    rows = list(index_rows(zar.read('~INDEX')))
    for name, size, flags, _ in rows:
        if flags != 0:
            raise ValueError('Unknown VFS flags')
        if name not in zar.entries:
            if name not in external or external[name] != size:
                raise ValueError('Unexpected external VFS member')
        elif zar.entries[name].size != size:
            raise ValueError('Dual index mismatch')
    return rows
