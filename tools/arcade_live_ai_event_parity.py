#!/usr/bin/env python3
"""Original 1991 Indy Heat live Z80 AI pending-event instruction parity.

Consumes PRIVATE CSV from mame_capture_ai_event_writes.lua, verifies the
actual original 2336/235C SET opcodes and their bounded triggering conditions
independently of recovered ROM code. No original game data or private RAM
values are emitted in public reports; all original screenshots/QRAM stay local.
Full AI steering/pathfinding/strategy remains unverified.
"""
from __future__ import annotations
import csv,argparse,json
from hashlib import sha256
from collections import Counter
from pathlib import Path

FIELDS=('frame','pc','ix','addr','old','new','cmp','pedal_response',
        'b1','b2','fe','linked20','x','y','dc','bound_x','bound_y','course','round')
VALID_IX=tuple(0xE080+0x100*i for i in range(5))


def original_thresholds(b1:int,b2:int,response:int)->tuple[int,int,bool]:
    restricted=bool((b1&16) or (b2&128))
    if restricted:return (24,9,True)
    if response<60:return (128,72,False)
    if response<68:return (128,50,False)
    return (80,50,False)


def audit_rows(rows:list[dict[str,str]])->dict:
    if not rows:raise ValueError('Original MAME event trace missing')
    stats=Counter();per_car=Counter();first=-1;last=-1;previous=-1
    for i,line in enumerate(rows):
        if not set(FIELDS).issubset(line):
            raise ValueError('Original AI trace columns incomplete')
        try:
            f=int(line['frame']);pc=int(line['pc'],16)
            ix=int(line['ix'],16);addr=int(line['addr'],16)
            old,new,compare,response,b1,b2,fe,linked,x,y,dc,bx,by,course,round_idx=[
                int(line[k]) for k in ('old','new','cmp','pedal_response',
                'b1','b2','fe','linked20','x','y','dc','bound_x','bound_y','course','round')]
        except (TypeError,ValueError) as e:
            raise ValueError('Original AI trace contains malformed number') from e
        if f<previous or f<=0:
            raise ValueError('Original AI events out of frame order')
        if pc not in (0x2336,0x235C) or ix not in VALID_IX or addr!=ix-9:
            raise ValueError('Wrong original event opcode, IX or physical status address')
        if any(not 0<=v<=255 for v in
               (old,new,compare,response,b1,b2,fe,linked,x,y,dc,course,round_idx)):
            raise ValueError('Original AI event contains non-byte data')
        if any(not 0<=v<=65535 for v in (bx,by)):
            raise ValueError('Original event has invalid course bounds')
        expected=old|(2 if pc==0x2336 else 4)
        if new!=expected:
            raise ValueError(f'Original AI pending-event byte mismatch at event {i}')
        b,c,restricted=original_thresholds(b1,b2,response)
        if pc==0x2336:
            threshold=compare<b and compare<c
            forced=bool((fe&16) and linked==3 and not restricted)
            spatial=bool((bx&255)<=x<(bx>>8) and
                         (by&255)<=y<(by>>8) and (dc&2))
            if not (threshold or forced or spatial):
                raise ValueError(f'Original AI bit1 event has no proven source at event {i}')
            stats['bit1_event']+=1
            stats['bit1_threshold_condition']+=threshold
            stats['bit1_forced_condition']+=forced
            stats['bit1_spatial_condition']+=spatial
        else:
            excluded=bool((fe&16) and linked==2 and not restricted)
            if compare<b or excluded:
                raise ValueError(
                    f'Original AI bit2 event violates genuine Z80 threshold/gate at event {i}')
            stats['bit2_event']+=1
        per_car[f'{ix:04X}']+=1
        if first<0:first=f
        last=f;previous=f
    return {'source':'original MAME master Z80 2336/235C AI event writes',
            'events_checked':len(rows),'first_frame':first,'last_frame':last,
            'verified_event_bit1':stats['bit1_event'],
            'verified_event_bit2':stats['bit2_event'],
            'bit1_threshold_condition_observed':stats['bit1_threshold_condition'],
            'bit1_forced_condition_observed':stats['bit1_forced_condition'],
            'bit1_spatial_condition_observed':stats['bit1_spatial_condition'],
            'events_by_car':dict(sorted(per_car.items())),
            'mismatches':0,
            'scope':'live original AI event writes and bounded trigger conditions; complete route-following, steering and pit decisions still open'}


def audit_file(path:Path)->dict:
    with path.open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError('Private original MAME event capture CSV header differs')
        report=audit_rows(list(reader))
    digest=sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):digest.update(chunk)
    report['private_trace_sha256']=digest.hexdigest()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('private_capture',type=Path)
    p.add_argument('--out',type=Path,
                   default=Path('local/private-runtime/ai_event_audit.json'))
    args=p.parse_args()
    r=audit_file(args.private_capture)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,indent=2))
