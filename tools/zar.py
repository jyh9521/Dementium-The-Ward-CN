"""ZAR1 core reused from jyh9521/Dementium-II-CN.
Upstream c0ea10f93450972841e510ff82913920339bd058; MIT, copyright 2026 jyh9521.
Selected definitions are byte-for-byte source copies; game routing is separate.
"""
from __future__ import annotations
import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def filehash(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


@dataclass(frozen=True)
class Entry:
    name: str
    offset: int
    size: int
    reserved: int
    toc: int


def index_rows(data):
    """VFS ~INDEX: u64 count, records <u32 size,u32 flags,u64 name offset>."""
    if len(data) < 8:
        raise ValueError('Truncated VFS index header')
    count = struct.unpack_from('<Q', data)[0]
    if count > (len(data) - 8) // 16:
        raise ValueError('Truncated VFS index records')
    base = 8 + count * 16
    seen = set()
    for i in range(count):
        offset = 8 + 16 * i
        size, flags, name_offset = struct.unpack_from('<IIQ', data, offset)
        start = base + name_offset
        if not base <= start < len(data):
            raise ValueError('VFS name outside pool')
        end = data.find(b'\0', start)
        if end < 0:
            raise ValueError('Unterminated VFS name')
        name = data[start:end].decode('ascii')
        if not name.startswith('/') or '..' in name.split('/') or '\\' in name or ':' in name:
            raise ValueError('Invalid VFS name')
        key = name.lstrip('/').upper()
        if key in seen:
            raise ValueError('Duplicate VFS name')
        seen.add(key)
        yield key, size, flags, offset


class Zar:
    def __init__(self, data: bytes):
        self.data = data
        if len(data) < 32 or data[:4] != b'ZAR1':
            raise ValueError('Not a ZAR1 archive')
        _, count, self.header_size, reserved, names, strings, toc, tail = struct.unpack_from('<8I', data)
        if not count or reserved != 0 or tail != 0:
            raise ValueError('Unsupported header variant')
        if not (32 <= names <= strings <= toc <= self.header_size <= len(data)):
            raise ValueError('Invalid header table bounds')
        if count > (strings - names) // 4 or count > (self.header_size - toc) // 24:
            raise ValueError('Truncated index')
        self.entries = {}
        previous = ''
        ranges = []
        for i in range(count):
            name_offset = strings + struct.unpack_from('<I', data, names + 4 * i)[0]
            if not strings <= name_offset < toc:
                raise ValueError('Name offset outside string pool')
            end = data.find(b'\0', name_offset, toc)
            if end < 0:
                raise ValueError('Unterminated name')
            name = data[name_offset:end].decode('ascii')
            if not name or name <= previous or '\\' in name or ':' in name or name.startswith('/') or '..' in PurePosixPath(name).parts:
                raise ValueError('Unsafe, duplicate or unsorted member name')
            offset, size, unknown = struct.unpack_from('<QQQ', data, toc + i * 24)
            if offset < self.header_size or offset % 512 or offset + size > len(data):
                raise ValueError('Member bounds/alignment error: ' + name)
            if unknown != 0:
                raise ValueError('Unrecognized member metadata: ' + name)
            self.entries[name] = Entry(name, offset, size, unknown, toc + i * 24)
            ranges.append((offset, offset + size))
            previous = name
        ranges.sort()
        if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
            raise ValueError('Overlapping members')

    def read(self, name):
        e = self.entries[name]
        return self.data[e.offset:e.offset + e.size]

    def rebuild(self, replacements):
        if set(replacements) - self.entries.keys():
            raise ValueError('Unknown replacement member')
        replacements = dict(replacements)
        if '~INDEX' in self.entries:
            original_index = self.read('~INDEX')
            if replacements.get('~INDEX', original_index) != original_index:
                raise ValueError('VFS index is derived; replace its referenced members instead')
            index = bytearray(original_index)
            for name, size, flags, offset in index_rows(original_index):
                if name in self.entries and flags == 0 and size != self.entries[name].size:
                    raise ValueError('Original VFS/ZAR size mismatch: ' + name)
                if name in replacements and len(replacements[name]) != size:
                    if flags != 0 or len(replacements[name]) >= 0x80000000:
                        raise ValueError('Unsupported VFS size/flags: ' + name)
                    struct.pack_into('<I', index, offset, len(replacements[name]))
            if bytes(index) != original_index:
                replacements['~INDEX'] = bytes(index)
        out = bytearray(self.data)
        for name in sorted(replacements):
            payload = replacements[name]
            if payload == self.read(name):
                continue
            e = self.entries[name]
            out.extend(b'\0' * (-len(out) % 512))
            offset = len(out)
            out.extend(payload)
            struct.pack_into('<QQ', out, e.toc, offset, len(payload))
        result = bytes(out)
        parsed = Zar(result)
        for name in self.entries:
            if parsed.read(name) != replacements.get(name, self.read(name)):
                raise ValueError('Rebuild verification failed: ' + name)
        return result


def make_delta(original, modified):
    if len(modified) < len(original):
        raise ValueError('Delta requires append-preserving rebuild')
    runs = []
    i = 0
    while i < len(original):
        if original[i:i + 65536] == modified[i:i + 65536]:
            i += 65536
            continue
        if original[i] == modified[i]:
            i += 1
            continue
        start = i
        while i < len(original) and original[i] != modified[i]:
            i += 1
        runs.append({'offset': start, 'old': original[start:i].hex(), 'new': modified[start:i].hex()})
    return {'format': 'zar-sparse-delta-v1', 'original_size': len(original), 'modified_size': len(modified),
            'original_sha256': digest(original), 'modified_sha256': digest(modified), 'runs': runs,
            'append': base64.b64encode(modified[len(original):]).decode('ascii')}


def apply_delta(data, patch, reverse=False):
    if patch['format'] != 'zar-sparse-delta-v1':
        raise ValueError('Unsupported delta format')
    tag = 'modified' if reverse else 'original'
    if len(data) != patch[tag + '_size'] or digest(data) != patch[tag + '_sha256']:
        raise ValueError('Version/hash mismatch')
    out = bytearray(data)
    for run in patch['runs']:
        a, b = bytes.fromhex(run['old']), bytes.fromhex(run['new'])
        if reverse:
            a, b = b, a
        o = run['offset']
        if len(a) != len(b) or o < 0 or o + len(a) > patch['original_size'] or out[o:o + len(a)] != a:
            raise ValueError('Invalid delta run')
        out[o:o + len(a)] = b
    if reverse:
        del out[patch['original_size']:]
    else:
        out.extend(base64.b64decode(patch['append'], validate=True))
    result = bytes(out)
    tag = 'original' if reverse else 'modified'
    if len(result) != patch[tag + '_size'] or digest(result) != patch[tag + '_sha256']:
        raise ValueError('Delta result hash mismatch')
    Zar(result)
    return result
