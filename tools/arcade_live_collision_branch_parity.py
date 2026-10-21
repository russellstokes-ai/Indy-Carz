#!/usr/bin/env python3
"""Verify actual original 1991 Indy Heat collision path execution in MAME.

Consumes PRIVATE live debugger CSV created by mame_capture_collision_branches.lua
and private SHA256-authenticated original arcade master/X-ROM. Compares actual
branch hits and original A/E925 against independent integer/X-ROM arithmetic.
No ROM/graphics/byte tables or raw live data are included in public reports.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
import math
from pathlib import Path

MASTER_SHA = '521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7'
XROM_SHA = '1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb'
FIELDS=('frame','stage','ix','iy','d','e','e919','angle3d','a','e925')
CAR_IX=tuple(0xE080+0x100*i for i in range(5))
FOLLOW={
  'B86C':('B86C',),
  'B778':('B778','B86C'),
  'B728':('B728','B778','B86C'),
}


def s8(n:int)->int:
    return n-256 if n&0x80 else n


def original_projection(source:int,angle3d:int,d:int,e:int)->tuple[int,int,str]:
    if any(not 0<=v<=255 for v in (source,angle3d,d,e)):
        raise ValueError('Original collision operands must be 8-bit')
    heading=((source&0xC0)+angle3d)&255
    cosine=max(-128,min(127,round(128*math.cos(heading*math.tau/256))))
    sine=max(-128,min(127,round(128*math.sin(heading*math.tau/256))))
    def high(a,b):
        p=max(-32768,min(32767,s8(a)*b*2))
        return p>>8
    signed_projection=max(-128,min(127,high(d,cosine)+high(e,sine)+1))
    target='B86C' if signed_projection<0 else 'B778' if signed_projection<4 else 'B728'
    return source&0x33,signed_projection&255,target


def parse_row(row:dict[str,str])->dict:
    if not set(FIELDS).issubset(row):
        raise ValueError('Private original branch trace fields missing')
    try:
        o={'frame':int(row['frame']),'stage':row['stage']}
        for name in FIELDS[2:]:o[name]=int(row[name],16)
    except (ValueError,TypeError) as exc:
        raise ValueError('Invalid debugger register/collision trace') from exc
    if o['frame']<=0 or o['ix'] not in CAR_IX or o['iy'] not in CAR_IX:
        raise ValueError('Original collision frame/IX/IY not a valid five-car state')
    if o['stage'] not in ('START',*FOLLOW):
        raise ValueError('Original branch tracer reached an unknown PC')
    if any(not 0<=o[name]<=255 for name in FIELDS[4:]):
        raise ValueError('Original collision CPU registers must be 8-bit')
    return o


def audit_rows(rows:list[dict[str,str]],master:bytes)->dict:
    if not rows or len(master)!=0x90000:
        raise ValueError('Original collision data and complete master ROM required')
    parsed=[parse_row(row) for row in rows]
    starts=Counter();sequences=Counter();extended=Counter();cats=set()
    frame_min=parsed[0]['frame'];frame_max=parsed[-1]['frame']
    last_frame=-1;at=0
    while at<len(parsed):
        start=parsed[at]
        if start['frame']<last_frame or start['stage']!='START':
            raise ValueError('Original collision source/branch order invalid')
        last_frame=start['frame']
        following=[];j=at+1
        while j<len(parsed) and parsed[j]['stage']!='START':
            hit=parsed[j]
            if (hit['frame']!=start['frame'] or hit['ix']!=start['ix'] or
                hit['iy']!=start['iy'] or hit['e919']!=start['e919'] or
                hit['angle3d']!=start['angle3d']):
                raise ValueError('Original continuation did not match collision context')
            following.append(hit);j+=1
        if not following:raise ValueError('Unfinished original collision projection')
        category=start['e919']&31
        source=master[0xBC5C+2*category]
        mask,projection,first_pc=original_projection(
            source,start['angle3d'],start['d'],start['e'])
        actual=tuple(h['stage'] for h in following)
        if actual!=FOLLOW[first_pc]:
            raise ValueError(f'Original collision branch chain mismatch at event {at}')
        if following[0]['a']!=projection:
            raise ValueError('Original collision projected Z80 accumulator differs')
        if any(h['e925']!=mask for h in following):
            raise ValueError('Original collision event E925 mask differs')
        starts[first_pc]+=1
        sequences['>'.join(actual)]+=1
        cats.add(category)
        extended['adjacent_rom_category_events']+=category>=24
        extended['regular_table_category_events']+=category<24
        at=j
    return {
        'source':'original 1991 Indy Heat MAME 0.264 actual master Z80 breakpoint execution',
        'live_complete_collision_sequences':sum(starts.values()),
        'live_original_breakpoint_hits':len(parsed)-sum(starts.values()),
        'first_frame':frame_min,'last_frame':frame_max,
        'direct_first_branch_counts':dict(sorted(starts.items())),
        'actual_full_continuation_sequences':dict(sorted(sequences.items())),
        'observed_original_category_indices':sorted(cats),
        'adjacent_rom_category_events':extended['adjacent_rom_category_events'],
        'defined_table_category_events':extended['regular_table_category_events'],
        'mismatches':0,
        'scope':'actual B6ED branching and subsequent B728/B778/B86C fallthrough; does not prove physical collision impulses or damage',
    }


def audit_file(trace:Path,master_path:Path,xrom_path:Path)->dict:
    master=master_path.read_bytes();xrom=xrom_path.read_bytes()
    if (len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA or
        len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_SHA):
        raise ValueError('Checksum-verified original 1991 arcade master and X-ROM required')
    # Original ROM trigonometry and all signed X-ROM high-byte maths checked
    # independently before any live trace event is treated as proven.
    for angle in range(256):
        for base,func in ((0xA200,math.cos),(0xA500,math.sin)):
            original=s8(master[base+angle])
            expected=max(-128,min(127,round(128*func(angle*math.tau/256))))
            if original!=expected:
                raise ValueError('Original 8-bit trigonometric lookup changed')
    for aa in range(256):
        for bb in range(256):
            result=max(-32768,min(32767,s8(aa)*s8(bb)*2))>>8
            if xrom[2*((aa<<8)|bb)+1]!=result&255:
                raise ValueError('Original X-ROM signed high product lookup changed')
    with trace.open(newline='',encoding='utf-8') as fh:
        reader=csv.DictReader(fh)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError('Private debugger breakpoint CSV header differs')
        report=audit_rows(list(reader),master)
    report['private_trace_sha256']=sha256(trace.read_bytes()).hexdigest()
    report['trigonometry_entries_verified']=512
    report['signed_xrom_high_pairs_verified']=65536
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('original_private_branch_csv',type=Path)
    p.add_argument('original_private_master',type=Path)
    p.add_argument('original_private_xrom',type=Path)
    p.add_argument('--out',type=Path,default=Path('local/private-runtime/collision_branch_live_audit.json'))
    a=p.parse_args();result=audit_file(a.original_private_branch_csv,a.original_private_master,a.original_private_xrom)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
