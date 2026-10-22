"""Bounded binfont resource inspection and metrics codec (no game execution).

The observed Steam resource uses a two-level 16-bit character page table.
Opaque texture/footer fields are preserved, not assigned speculative meanings.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct
import zlib


@dataclass(frozen=True)
class Glyph:
    x: int
    y: int
    height: int
    width: int
    advance: int
    bearing_x: int
    bearing_y: int

    @classmethod
    def unpack(cls, raw):
        if len(raw) != 8:
            raise ValueError('Glyph metric must be eight bytes')
        value, width, advance, bx, by = struct.unpack('<IBBbb', raw)
        return cls(value & 1023, value >> 10 & 1023, value >> 20,
                   width, advance, bx, by)

    def pack(self):
        if not (0 <= self.x < 1024 and 0 <= self.y < 1024 and
                0 <= self.height < 4096 and 0 <= self.width < 256 and
                0 <= self.advance < 256 and -128 <= self.bearing_x < 128 and
                -128 <= self.bearing_y < 128):
            raise ValueError('Glyph metric overflow')
        return struct.pack('<IBBbb', self.x | self.y << 10 | self.height << 20,
                           self.width, self.advance, self.bearing_x, self.bearing_y)


def inflate_frame(data, expected, max_size=64 * 1024 * 1024, compressed_size=None):
    """A bounded zlib stream with at most three zero alignment bytes."""
    if not 0 <= expected <= max_size:
        raise ValueError('Inflation size outside bound')
    stream = zlib.decompressobj()
    result = stream.decompress(data, expected + 1)
    if (len(result) != expected or not stream.eof or stream.unconsumed_tail or
            len(stream.unused_data) > 3 or any(stream.unused_data) or
            (compressed_size is not None and len(data) - len(stream.unused_data) != compressed_size)):
        raise ValueError('Invalid compressed frame')
    return result


class BinFont:
    def __init__(self, data):
        self.data = bytes(data)
        if len(data) < 1032 or struct.unpack_from('<I', data)[0] != 1:
            raise ValueError('Unsupported binfont header')
        self.header_word, self.base_height = struct.unpack_from('<II', data)
        self.pages = {}
        self.glyphs = {}
        ends = []
        for page, offset in enumerate(struct.unpack_from('<256I', data, 8)):
            if not offset:
                continue
            if offset < 1032 or offset + 2080 > len(data):
                raise ValueError('Font page outside resource')
            if any(offset < end and offset + 2080 > start for start, end in ends):
                raise ValueError('Overlapping font pages')
            ends.append((offset, offset + 2080))
            self.pages[page] = offset
            for low in range(256):
                present = data[offset + low // 8] >> (low % 8) & 1
                raw = data[offset + 32 + low * 8:offset + 40 + low * 8]
                if not present:
                    if any(raw):
                        raise ValueError('Absent glyph has nonzero metrics')
                    continue
                self.glyphs[page * 256 + low] = Glyph.unpack(raw)
        if not ends:
            raise ValueError('Font has no character pages')
        self.texture_offset = max(end for _, end in ends)
        t = self.texture_offset
        if t + 36 > len(data):
            raise ValueError('Truncated texture')
        self.texture_header = data[t:t + 20]
        self.texture_fields = struct.unpack_from('<6H2I', data, t)
        self.width, self.height = self.texture_fields[2:4]
        marker, expanded, compressed, aligned = struct.unpack_from('<4I', data, t + 20)
        if marker != 0x20000 or aligned != (12 + compressed + 3) // 4 * 4:
            raise ValueError('Unsupported outer texture frame')
        self.texture_end = t + 24 + aligned
        if self.texture_end > len(data):
            raise ValueError('Texture frame outside resource')
        inner = inflate_frame(data[t + 36:self.texture_end], expanded, compressed_size=compressed)
        if len(inner) < 12:
            raise ValueError('Truncated inner texture frame')
        marker2, compressed2, aligned2 = struct.unpack_from('<3I', inner)
        if (marker2 != 0x20000 or aligned2 != len(inner) or
                aligned2 != (12 + compressed2 + 3) // 4 * 4):
            raise ValueError('Unsupported inner texture frame')
        if compressed2 > len(inner) - 12:
            raise ValueError('Inner compressed size outside frame')
        self.rgba = inflate_frame(inner[12:], self.width * self.height * 4, compressed_size=compressed2)
        self.footer = data[self.texture_end:]
        if len(data) < 36 or struct.unpack_from('<I', data, len(data) - 4)[0] != 2:
            raise ValueError('Unsupported font section count')
        self.sections = struct.unpack_from('<8I', data, len(data) - 36)
        o0, n0, r0, rn0, o1, n1, r1, rn1 = self.sections
        if (o0 != 0 or n0 != t or o1 != t or n1 != self.texture_end - t or
                r0 != self.texture_end or rn0 != len(self.pages) * 2 or
                r1 != r0 + rn0 or rn1 != 0 or
                len(data) - 36 != (r1 + 3) // 4 * 4 or any(data[r1:len(data)-36])):
            raise ValueError('Invalid font section descriptors')
        relocations = []
        position = 0
        for delta in struct.unpack_from('<' + 'H' * len(self.pages), data, r0):
            if not 0 < delta < 32768:
                raise ValueError('Unsupported relocation delta')
            position += delta
            relocations.append(position)
        if relocations != [8 + page * 4 for page in self.pages]:
            raise ValueError('Page relocations mismatch')
        self.frame_fields = (marker, expanded, compressed, aligned,
                             marker2, compressed2, aligned2)
        for glyph in self.glyphs.values():
            if glyph.x + glyph.width > self.width or glyph.y + glyph.height > self.height:
                raise ValueError('Glyph rectangle outside atlas')

    def rebuild(self):
        """Exact no-op serialization, retaining original compressed representation."""
        return self.data

    def write(self, glyphs, rgba, width, height):
        """Serialize explicit BMP glyph mapping and RGBA atlas; preserve header style.

        No text encoding or locale policy lives here. All glyphs must be supplied,
        including the original glyphs that the caller wishes to preserve.
        """
        glyphs = dict(glyphs)
        rgba = bytes(rgba)
        if (not isinstance(width, int) or not isinstance(height, int) or
                not 1 <= width <= 1024 or not 1 <= height <= 1024 or
                len(rgba) != width * height * 4 or not glyphs):
            raise ValueError('Invalid atlas dimensions/data')
        for cp, glyph in glyphs.items():
            if not isinstance(cp, int) or not 0 <= cp <= 0xFFFF or 0xD800 <= cp <= 0xDFFF:
                raise ValueError('Codepoint outside supported BMP mapping')
            glyph.pack()
            if glyph.x + glyph.width > width or glyph.y + glyph.height > height:
                raise ValueError('Glyph rectangle outside atlas')
        if (glyphs == self.glyphs and rgba == self.rgba and
                width == self.width and height == self.height):
            return self.data
        pages = sorted({cp >> 8 for cp in glyphs})
        font = bytearray(struct.pack('<II', self.header_word, self.base_height) + bytes(1024))
        for page in pages:
            offset = len(font)
            struct.pack_into('<I', font, 8 + page * 4, offset)
            payload = bytearray(2080)
            for cp, glyph in glyphs.items():
                if cp >> 8 != page:
                    continue
                low = cp & 255
                payload[low // 8] |= 1 << (low % 8)
                payload[32 + low * 8:40 + low * 8] = glyph.pack()
            font.extend(payload)
        inner = encode_frame(rgba)
        outer = encode_frame(inner)
        fields = list(self.texture_fields)
        fields[2:6] = width, height, width, height
        fields[7] = width * height
        texture = (struct.pack('<6H2I', *fields) + outer[:4] +
                   struct.pack('<I', len(inner)) + outer[4:])
        reloc = bytearray()
        previous = 0
        for page in pages:
            offset = 8 + page * 4
            reloc.extend(struct.pack('<H', offset - previous))
            previous = offset
        reloc_start = len(font) + len(texture)
        reloc_end = reloc_start + len(reloc)
        descriptors = struct.pack('<8I', 0, len(font), reloc_start, len(reloc),
                                  len(font), len(texture), reloc_end, 0)
        result = (bytes(font) + texture + bytes(reloc) + bytes(-reloc_end % 4) +
                  descriptors + struct.pack('<I', 2))
        parsed = BinFont(result)
        if (parsed.glyphs != glyphs or parsed.rgba != rgba or
                parsed.width != width or parsed.height != height):
            raise ValueError('Font serialization verification failed')
        return result

    def glyph_rgba(self, codepoint):
        g = self.glyphs[codepoint]
        rows = []
        for row in range(g.y, g.y + g.height):
            start = (row * self.width + g.x) * 4
            rows.append(self.rgba[start:start + g.width * 4])
        return b''.join(rows)


def encode_frame(raw):
    compressed = zlib.compress(raw, level=9)
    aligned = (12 + len(compressed) + 3) // 4 * 4
    return (struct.pack('<3I', 0x20000, len(compressed), aligned) + compressed +
            bytes(aligned - 12 - len(compressed)))
