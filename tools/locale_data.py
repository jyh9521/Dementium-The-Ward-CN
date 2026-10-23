"""Validated source-to-target import, UTF-8 serialization, and bounded CJK layout."""
import json
from pathlib import Path
import re
from content import extract,TOKEN,text_kind
from runtime_patch import validate_text


def read_records(paths):
    result=[]
    for path in paths:result.extend(json.loads(Path(path).read_text(encoding='utf-8')))
    return result


def transcode_preserved_locales(content,translated_locale='en'):
    """Keep other languages logically unchanged under a globally UTF-8 decoder.

    Latin-1 here exactly models the original byte-to-ushort instruction path;
    no CP1252 smart-quote substitutions or translations are inferred.
    """
    locales=sorted({n.split('/')[1] for n in content.entries if text_kind(n)}-{translated_locale})
    changes={};rows=[];runtime={};reports=[]
    for locale in locales:
        records=extract(content,locale,'latin-1');rows.extend(records)
        runtime.update({r['id']:r['source'] for r in records})
        changed=[]
        for name in content.entries:
            if not text_kind(name) or name.split('/')[1]!=locale:continue
            original=content.read(name);logical=original.decode('latin-1')
            encoded=logical.encode('utf-8')
            if encoded.decode('utf-8')!=logical:raise ValueError('Preserved locale transcoding lost text')
            if ('/open.' in name or '/unlock.' in name) and len(encoded)>255:
                raise ValueError('Preserved HUD text exceeds byte capacity')
            if encoded!=original:changes[name]=encoded;changed.append(name)
        reports.append(dict(locale=locale,records=len(records),changed_resources=changed,
                            translated=False,logical_text_unchanged=True,encoding='UTF-8'))
    return changes,rows,runtime,reports


def validate_records(content,records,locale='en',source_encoding='latin-1'):
    originals={r['id']:r for r in extract(content,locale,source_encoding)}
    seen=set()
    for row in records:
        key=row['id']
        if key in seen or key not in originals:raise ValueError('Duplicate/unknown translation ID: '+key)
        seen.add(key)
        original=originals[key]
        for k,v in original.items():
            if k not in ('target','status') and row[k]!=v:raise ValueError('Stale source metadata: '+key)
        if row.get('status') not in ('translated','preserved-name','preserved-technical') or not row['target']:
            raise ValueError('Missing translation/review status: '+key)
        validate_text(row['target'])
        if TOKEN.findall(row['target'])!=TOKEN.findall(row['source']):raise ValueError('Protected tokens changed: '+key)
        if row['kind']=='table' and ('\n' in row['target'] or '\r' in row['target']):
            raise ValueError('Table row injection: '+key)
    if seen!=originals.keys():raise ValueError('Missing translation records')


def advance(char,font,spacing=1):
    cp=ord(char)
    if cp<32:return 0
    if cp not in font.glyphs:raise ValueError('Missing runtime glyph: U+%04X'%cp)
    value=font.glyphs[cp].advance
    return value if char==' ' else value+spacing-(1 if cp>>8==0x30 else 0)


def line_width(text,font):return sum(advance(c,font) for c in text)


def wrap_line(text,font,width,forbidden_start='，。！？：；、）》】」』〉〕…',forbidden_end='（《【「『〈〔'):
    if width<=0:raise ValueError('Invalid layout width')
    lines=[];line=''
    for char in text:
        if line_width(char,font)>width:raise ValueError('Glyph exceeds layout budget')
        if line and line_width(line+char,font)>width:
            # Keep closing punctuation off the next line without exceeding the budget.
            carry=''
            if char in forbidden_start or (line and line[-1] in forbidden_end):
                cut=len(line)-1
                while cut>0 and ord(line[cut])<32:cut-=1
                carry,line=line[cut:],line[:cut]
            if not line or line_width(carry+char,font)>width:raise ValueError('Unbreakable glyph run')
            lines.append(line);line=carry
        line+=char
    if line or not lines:lines.append(line)
    return lines


def layout_record(row,font,zar_names):
    text=row['target']
    if row['kind']=='table':
        budget=428
        if line_width(text,font)>budget:raise ValueError('Table width exceeds measured surface: '+row['id'])
        return text,dict(width=line_width(text,font),budget=budget,lines=1)
    is_examine='/examine.' in row['resource']
    suffix=row['resource'].split('.')[-1]
    has_image=is_examine and f'TEXTURES/EXAMINE/EXAMINE{suffix}.PNG' in zar_names
    width=428 if is_examine or '/open.' in row['resource'] or '/unlock.' in row['resource'] else 280
    limit=5 if has_image else 18
    ending='\r\n' if '\r\n' in text else '\n'
    source_lines=text.replace('\r\n','\n').replace('\r','\n').strip('\n').split('\n')
    lines=[]
    for line in source_lines:lines.extend(wrap_line(line,font,width))
    if len(lines)>limit:raise ValueError(f'Document height overflow: {row["id"]} {len(lines)}>{limit}')
    result=ending.join(lines)
    if re.sub(r'[\r\n]','',result)!=re.sub(r'[\r\n]','',text):raise ValueError('Layout lost content')
    if TOKEN.findall(result)!=TOKEN.findall(text):raise ValueError('Layout lost protected tokens')
    validate_text(result)
    if ('/open.' in row['resource'] or '/unlock.' in row['resource']) and len(result.encode('utf-8'))>255:
        raise ValueError('HUD fixed field exceeds 255 bytes')
    return result,dict(width=max(line_width(line,font) for line in lines),budget=width,
                       lines=len(lines),line_limit=limit,has_image=has_image)


def build_resources(content,records,font,zar_names,locale='en'):
    validate_records(content,records,locale)
    resources={};runtime={};report=[]
    grouped={}
    for row in records:
        target,info=layout_record(row,font,zar_names)
        runtime[row['id']]=target
        grouped.setdefault(row['resource'],[]).append((row,target.encode('utf-8')))
        report.append(dict(id=row['id'],status=row['status'],source=row['source'],target=row['target'],runtime=target,**info))
    for name,rows in grouped.items():
        raw=content.read(name)
        for row,value in sorted(rows,key=lambda x:x[0]['offset'],reverse=True):
            at=row['offset'];raw=raw[:at]+value+raw[at+row['source_bytes']:]
        raw.decode('utf-8',errors='strict')
        if raw!=content.read(name):resources[name]=raw
    return resources,runtime,report
