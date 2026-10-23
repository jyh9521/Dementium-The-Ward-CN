"""Deterministic streaming source-relative copy/add patch, not whole-file payloads.

The 512-byte block size follows archive alignment, not locale-specific behavior.
Every COPY is bounded by the exact source file; every output is SHA-256 checked.
"""
import gzip
import hashlib
import mmap
from pathlib import Path
import struct

MAGIC = b'LOCDLT1\0'
BLOCK = 512
MAX_ADD = 1024 * 1024


def filehash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def build(source, target, output):
    source, target, output = map(Path, (source, target, output))
    if not source.stat().st_size or not target.stat().st_size:
        raise ValueError('Nonempty source and target required')
    if output.resolve() in (source.resolve(), target.resolve()):
        raise ValueError('Patch output aliases an input')
    stats = dict(copy_commands=0, add_commands=0, copy_bytes=0, add_bytes=0)
    with source.open('rb') as sf, target.open('rb') as tf, output.open('wb') as dst:
        with mmap.mmap(sf.fileno(), 0, access=mmap.ACCESS_READ) as a, mmap.mmap(tf.fileno(), 0, access=mmap.ACCESS_READ) as b:
            index = {}
            for pos in range(0, len(a) - BLOCK + 1, BLOCK):
                key = hashlib.blake2b(a[pos:pos + BLOCK], digest_size=12).digest()
                index.setdefault(key, pos)
            with gzip.GzipFile(filename='', mode='wb', fileobj=dst, compresslevel=9, mtime=0) as gz:
                gz.write(MAGIC)
                copy_start = 0
                copy_length = 0
                literal = bytearray()

                def flush_copy():
                    nonlocal copy_length
                    if copy_length:
                        gz.write(b'\x01' + struct.pack('<QQ', copy_start, copy_length))
                        stats['copy_commands'] += 1
                        stats['copy_bytes'] += copy_length
                        copy_length = 0

                def flush_add():
                    if literal:
                        gz.write(b'\x02' + struct.pack('<I', len(literal)) + literal)
                        stats['add_commands'] += 1
                        stats['add_bytes'] += len(literal)
                        literal.clear()

                for pos in range(0, len(b), BLOCK):
                    block = b[pos:pos + BLOCK]
                    candidate = None
                    if len(block) == BLOCK:
                        following = copy_start + copy_length
                        if copy_length and following + BLOCK <= len(a) and a[following:following + BLOCK] == block:
                            candidate = following
                        elif pos + BLOCK <= len(a) and a[pos:pos + BLOCK] == block:
                            candidate = pos
                        else:
                            candidate = index.get(hashlib.blake2b(block, digest_size=12).digest())
                            if candidate is not None and a[candidate:candidate + BLOCK] != block:
                                candidate = None
                    if candidate is None:
                        flush_copy()
                        literal.extend(block)
                        if len(literal) >= MAX_ADD:
                            flush_add()
                    else:
                        flush_add()
                        if copy_length and candidate != copy_start + copy_length:
                            flush_copy()
                        if not copy_length:
                            copy_start = candidate
                        copy_length += BLOCK
                flush_copy()
                flush_add()
                gz.write(b'\0')
    return dict(source_size=source.stat().st_size, target_size=target.stat().st_size,
                source_sha256=filehash(source), target_sha256=filehash(target),
                payload_size=output.stat().st_size, payload_sha256=filehash(output), **stats)


def apply(source, delta, destination, metadata):
    source, delta, destination = map(Path, (source, delta, destination))
    if source.stat().st_size != metadata['source_size'] or filehash(source) != metadata['source_sha256']:
        raise ValueError('Source identity mismatch')
    if destination.resolve() in (source.resolve(), delta.resolve()):
        raise ValueError('Destination aliases input')
    count = 0
    with source.open('rb') as src, gzip.open(delta, 'rb') as patch, destination.open('wb') as dst:
        def read(n):
            data = patch.read(n)
            if len(data) != n:
                raise ValueError('Truncated source-relative delta')
            return data
        if read(8) != MAGIC:
            raise ValueError('Unknown source-relative delta')
        while True:
            op = read(1)[0]
            if op == 0:
                if patch.read(1):
                    raise ValueError('Trailing delta data')
                break
            if op == 1:
                offset, length = struct.unpack('<QQ', read(16))
                if not length or offset > metadata['source_size'] - length:
                    raise ValueError('Copy range exceeds source')
                src.seek(offset)
            elif op == 2:
                length, = struct.unpack('<I', read(4))
                if not 0 < length <= MAX_ADD:
                    raise ValueError('Invalid literal length')
            else:
                raise ValueError('Unknown delta command')
            if length > metadata['target_size'] - count:
                raise ValueError('Output exceeds target')
            remaining = length
            while remaining:
                n = min(remaining, MAX_ADD)
                data = src.read(n) if op == 1 else read(n)
                if len(data) != n:
                    raise ValueError('Truncated copy source')
                dst.write(data)
                remaining -= n
            count += length
    if count != metadata['target_size'] or filehash(destination) != metadata['target_sha256']:
        raise ValueError('Output identity mismatch')
