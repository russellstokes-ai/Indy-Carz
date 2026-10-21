#!/usr/bin/env python3
"""Exact original 1991 Indy Heat live collision category ROM lookup parity.

Consumes PRIVATE MAME original Z80 CPU-write trace E925@B6FC and the
authenticated user-owned original master and X-ROM memory images.
Reports numerical/categorical evidence only, NO original ROM/table
contents, gameplay images, car-state values or proprietary disassembly.

Crucial MAME 0.264 finding: (E919 & 0x1F) can be 24..31 in actual
racing. The original indexed helper does NOT guard the 24-record table,
and reads eight adjacent ROM instruction-byte pairs. Rejecting these
indices changes authentic collision effects and was fixed 2026-10-21.

Projected next paths are MATH-PREDICTED from original inputs at B6FC;
the live trace at this instruction does NOT prove branch targets taken.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path

from arcade_collision_projection_classification import (
    MASTER_HASH, XROM_HASH, TABLE_COUNT, ORIGINAL_CATEGORY_COUNT,
    lookup_original_indexed_byte, model
)

FIELDS=('frame','pc','ix','iy','d','e','angle3d','event_index','table0',
        'e925_write','prev_e925','course','round','reg_H','reg_L')
CAR_POINTERS=tuple(0xE080+i*0x100 for i in range(5))


def audit_rows(rows:list[dict[str,str]],master:bytes)->dict:
    if not rows:raise ValueError('Original collision trace is empty')
    if len(master)!=0x90000:raise ValueError('Original master ROM image must be 0x90000 bytes')
    categories=Counter();paths=Counter();prev=-1;first=None;last=None
    for i,row in enumerate(rows):
        if not set(FIELDS).issubset(row):
            raise ValueError('Missing original MAME collision trace columns')
        try:
            frame=int(row['frame'])
            pc=int(row['pc'],16)
            ix=int(row['ix'],16)
            iy=int(row['iy'],16)
            regs={key:int(row[key]) for key in
                ('d','e','angle3d','event_index','table0',
                 'e925_write','prev_e925','course','round','reg_H','reg_L')}
        except (TypeError,ValueError) as exc:
            raise ValueError('Invalid original collision register/trace record') from exc
        if frame<=0 or frame<prev:
            raise ValueError('Original collision frame indices out of order')
        if pc!=0xB6FC or ix not in CAR_POINTERS or iy not in CAR_POINTERS:
            raise ValueError('Original Z80 collision PC, IX or IY unexpectedly changed')
        if any(not 0<=v<256 for v in regs.values()) or regs['event_index']>=32:
            raise ValueError('Original collision inputs must be unsigned bytes/categories 0..31')
        index=regs['event_index']
        source=lookup_original_indexed_byte(master,index)
        if source!=regs['table0'] or source!=regs['reg_H']:
            raise ValueError(f'Original indexed ROM source byte differs from MAME at event {i}')
        if source&0x33!=regs['e925_write']:
            raise ValueError(f'Original Z80 E925 contact mask differs at event {i}')
        _,_,destination=model(source,regs['angle3d'],regs['d'],regs['e'])
        paths[destination]+=1
        categories[index]+=1
        if first is None:first=frame
        last=frame;prev=frame
    return {
        'source':'original MAME 0.264, Indy Heat 1991 rev1 master Z80 E925 write at B6FC',
        'live_collision_lookup_events':len(rows),
        'original_structured_category_count':TABLE_COUNT,
        'original_masked_category_range':[0,ORIGINAL_CATEGORY_COUNT-1],
        'observed_category_indices':sorted(categories),
        'live_adjacent_code_rom_reads':sum(n for k,n in categories.items() if k>=TABLE_COUNT),
        'first_frame':first,'last_frame':last,
        'observed_source_or_mask_mismatches':0,
        'predicted_next_branch_counts':dict(sorted(paths.items())),
        'limits':[
            'The B6FC write tap independently verifies actual E925 output/ROM source, NOT branch target execution.',
            'Predicted B728/B778/B86C are mathematical projections from live D/E/IY, not observed branch hits.',
            '24 structured entries PLUS eight original instruction-adjacent byte pairs; no ROM data distributed.',
            'Physical car collision effects, restitution and track-wall responses remain open.'
        ]
    }


def audit_file(trace:Path,master_file:Path,xrom_file:Path)->dict:
    master,xrom=master_file.read_bytes(),xrom_file.read_bytes()
    if (sha256(master).hexdigest()!=MASTER_HASH or len(master)!=0x90000
        or sha256(xrom).hexdigest()!=XROM_HASH or len(xrom)!=0x40000):
        raise ValueError('Authentic privately checksum-verified original arcade ROM and X-ROM required')
    with trace.open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError('Private original MAME collision capture header differs')
        result=audit_rows(list(reader),master)
    h=sha256()
    with trace.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    result['private_trace_sha256']=h.hexdigest()
    return result


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_live_trace',type=Path)
    parser.add_argument('private_master',type=Path)
    parser.add_argument('private_xrom',type=Path)
    parser.add_argument('--out',type=Path,
                        default=Path('local/private-runtime/live_contact_category_audit.json'))
    args=parser.parse_args()
    result=audit_file(args.private_live_trace,args.private_master,args.private_xrom)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
