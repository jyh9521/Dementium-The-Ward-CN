"""Bounded double-LZ4 RGBA texture container codec.

The .PNG extension is not a PNG signature. Header words 0 and 1 are opaque:
observed values are 122 and 32; their semantic meanings are not asserted.
Both compressed blocks carry mandatory 1..4-byte zero alignment tails.
No source asset, resource name, game path or executable offset is embedded.
"""
from __future__ import annotations

import hashlib
import hmac
import struct

import lz4.block


DEFAULT_MAX_SIZE = 64 * 1024 * 1024
DEFAULT_MAX_DIMENSION = 16384


def _dimensions(width, height, max_size, max_dimension):
    if (not isinstance(width, int) or not isinstance(height, int) or
            not 0 < width <= max_dimension or not 0 < height <= max_dimension):
        raise ValueError('Texture dimensions outside bounds')
    size = width * height * 4
    if size > max_size:
        raise ValueError('RGBA byte count outside bound')
    return size


def _padding(compressed_size):
    # The observed writer always emits a full word when already aligned.
    return b'\0' * (4 - compressed_size % 4)


def _inflate(block, expected_size, max_size):
    if not 0 < expected_size <= max_size or not block:
        raise ValueError('Invalid LZ4 frame size')
    try:
        raw = lz4.block.decompress(block, uncompressed_size=expected_size)
    except (ValueError, OverflowError, lz4.block.LZ4BlockError) as exc:
        raise ValueError('Invalid LZ4 block') from exc
    if len(raw) != expected_size:
        raise ValueError('LZ4 output length mismatch')
    return raw


def _compress(raw):
    return lz4.block.compress(raw, mode='high_compression', compression=12,
                              store_size=False)


class Texture:
    """Decode and rebuild one RGBA container, preserving opaque header words.

    Supplying ``expected_sha256`` binds edits to an independently recorded input
    identity. Optional ``expected_header`` binds a known header variant. Defaults
    preserve opaque header fields without interpreting them as format flags.
    Unchanged writes return the original encoded bytes, not a recompression.
    """

    def __init__(self, data: bytes, *, expected_sha256=None, expected_header=None,
                 max_size=DEFAULT_MAX_SIZE, max_dimension=DEFAULT_MAX_DIMENSION):
        if not isinstance(data, bytes):
            raise ValueError('Texture input must be immutable bytes')
        if not isinstance(max_size, int) or not 0 < max_size <= 1024 * 1024 * 1024:
            raise ValueError('Invalid resource bound')
        if not isinstance(max_dimension, int) or not 0 < max_dimension <= 65535:
            raise ValueError('Invalid dimension bound')
        if len(data) < 36 or len(data) > max_size * 2 + 65536:
            raise ValueError('Texture encoded size outside bounds')
        self.sha256 = hashlib.sha256(data).hexdigest()
        self._verify_hash(expected_sha256)
        word0, word1, self.width, self.height, inner_size, outer_csize = struct.unpack_from('<6I', data)
        self.header_words = (word0, word1)
        if expected_header is not None and self.header_words != tuple(expected_header):
            raise ValueError('Unsupported texture header variant')
        rgba_size = _dimensions(self.width, self.height, max_size, max_dimension)
        # An incompressible LZ4 block may be larger than its raw input.
        inner_bound = max_size + max_size // 255 + 65536
        if not 8 < inner_size <= inner_bound or not 0 < outer_csize <= len(data) - 24:
            raise ValueError('Outer LZ4 bounds mismatch')
        self.outer_tail = data[24 + outer_csize:]
        if self.outer_tail != _padding(outer_csize):
            raise ValueError('Invalid outer alignment tail')
        inner = _inflate(data[24:24 + outer_csize], inner_size, inner_bound)
        if len(inner) < 9:
            raise ValueError('Truncated inner header')
        decoded_size, inner_csize = struct.unpack_from('<2I', inner)
        if decoded_size != rgba_size or not 0 < inner_csize <= len(inner) - 8:
            raise ValueError('Inner RGBA size/bounds mismatch')
        self.inner_tail = inner[8 + inner_csize:]
        if self.inner_tail != _padding(inner_csize):
            raise ValueError('Invalid inner alignment tail')
        self.rgba = _inflate(inner[8:8 + inner_csize], rgba_size, max_size)
        self.data = data
        self.inner_size = inner_size
        self.outer_compressed_size = outer_csize
        self.inner_compressed_size = inner_csize
        self.max_size = max_size
        self.max_dimension = max_dimension

    def _verify_hash(self, expected):
        if expected is not None and (not isinstance(expected, str) or
                len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected) or
                not hmac.compare_digest(self.sha256, expected)):
            raise ValueError('Texture source hash mismatch')

    def describe(self):
        """Return JSON-compatible identity and uninterpreted tail/header evidence."""
        return dict(width=self.width, height=self.height, source_sha256=self.sha256,
                    rgba_sha256=hashlib.sha256(self.rgba).hexdigest(),
                    encoded_size=len(self.data), rgba_size=len(self.rgba),
                    header_words=list(self.header_words), inner_size=self.inner_size,
                    outer_compressed_size=self.outer_compressed_size,
                    inner_compressed_size=self.inner_compressed_size,
                    outer_tail_hex=self.outer_tail.hex(),
                    inner_tail_hex=self.inner_tail.hex())

    def rebuild(self, rgba=None, *, expected_sha256=None):
        """Return exact original bytes for no-op; encode same-dimension RGBA edits."""
        self._verify_hash(expected_sha256)
        if rgba is not None and not isinstance(rgba, bytes):
            raise ValueError('Replacement RGBA must be immutable bytes')
        if rgba is None or rgba == self.rgba:
            return self.data
        if not isinstance(rgba, bytes) or len(rgba) != len(self.rgba):
            raise ValueError('Replacement RGBA byte count mismatch')
        output = self.encode(self.width, self.height, rgba, header_words=self.header_words,
                             max_size=self.max_size, max_dimension=self.max_dimension)
        check = Texture(output, expected_header=self.header_words, max_size=self.max_size,
                        max_dimension=self.max_dimension)
        if check.rgba != rgba:
            raise ValueError('Rebuilt texture pixel verification failed')
        return output

    @staticmethod
    def encode(width, height, rgba, *, header_words=(122, 32),
               max_size=DEFAULT_MAX_SIZE, max_dimension=DEFAULT_MAX_DIMENSION):
        expected = _dimensions(width, height, max_size, max_dimension)
        if not isinstance(rgba, bytes) or len(rgba) != expected:
            raise ValueError('RGBA byte count mismatch')
        if len(header_words) != 2 or any(not isinstance(n, int) or not 0 <= n <= 0xffffffff
                                         for n in header_words):
            raise ValueError('Opaque header words must be two unsigned dwords')
        compressed = _compress(rgba)
        inner = struct.pack('<2I', len(rgba), len(compressed)) + compressed + _padding(len(compressed))
        outer = _compress(inner)
        return struct.pack('<6I', *header_words, width, height, len(inner), len(outer)) + outer + _padding(len(outer))
