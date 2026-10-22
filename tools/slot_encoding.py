"""Explicit, reversible, locale-configured single-byte glyph aliases.

This is a bounded experiment codec, not an assertion of native UTF-8 support.
"""


def validate_slots(mapping, font, source_resources):
    if not mapping or len(set(mapping.values()))!=len(mapping):
        raise ValueError('Empty/duplicate runtime slots')
    occupied=set(b for raw in source_resources for b in raw)
    for char,slot in mapping.items():
        if len(char)!=1 or ord(char)<256 or 0xD800<=ord(char)<=0xDFFF:
            raise ValueError('Invalid logical alias character')
        # Keep ASCII, line/control syntax and original font mappings untouched.
        if not isinstance(slot,int) or not 0x80<=slot<=0xff or slot in font.glyphs or slot in occupied:
            raise ValueError('Occupied or unsupported runtime slot')


def encode(text,mapping):
    out=bytearray()
    for char in text:
        if char in mapping:out.append(mapping[char])
        elif 32<=ord(char)<127:out.append(ord(char))
        else:raise ValueError('Character lacks explicit runtime mapping')
    return bytes(out)


def decode(raw,mapping):
    inverse={v:k for k,v in mapping.items()}
    if len(inverse)!=len(mapping):raise ValueError('Duplicate runtime slot')
    return ''.join(inverse[b] if b in inverse else chr(b) for b in raw)
