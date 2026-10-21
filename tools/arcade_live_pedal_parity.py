#!/usr/bin/env python3
"""Original Indy Heat 1991 live MAME master Z80 pedal response verifier.

Authentic CPU write tap at 67D2 writes to PHYSICAL E0D7, since original
IX=E080 and original displacement +57 gives slot offset +D7.
Reads PRIVATE CSV from mame_capture_pedal_parity.lua; its report contains
only counts/metadata/hash, never original ROM, original RAM records or art.
This verifies original input arithmetic, NOT full vehicle acceleration.
"""
from __future__ import annotations
import argparse,csv,json
from collections import Counter
from hashlib import sha256
from pathlib import Path

FIELDS=('frame','pc','ix','addr','data','pedal','factor','bias','car_b1','car_b2')


def expected_response(raw:int,factor:int,bias:int)->int:
    if any(not isinstance(v,int) or not 0<=v<=255 for v in (raw,factor,bias)):
        raise ValueError('Original pedal/factor/bias outside 8-bit domain')
    result=((raw*factor+128)>>8)+bias
    return min(126,2*(result-256)) if result>=256 else 0


def audit_rows(rows:list[dict[str,str]],require_complete_sweep:bool=False)->dict:
    if not rows:raise ValueError('Original live pedal log empty')
    seen=Counter();per_pair=Counter();first=last=-1;previous=-1
    min_value=256;max_value=-1
    for i,r in enumerate(rows):
        if not set(FIELDS).issubset(r):raise ValueError('Original pedal trace column missing')
        try:
            frame=int(r['frame']);pc=int(r['pc'],16);ix=int(r['ix'],16)
            addr=int(r['addr'],16)
            data,raw,factor,bias,flag1,flag2=(int(r[k]) for k in
                ('data','pedal','factor','bias','car_b1','car_b2'))
        except (TypeError,ValueError) as err:
            raise ValueError('Malformed original pedal record') from err
        if frame<=0 or frame<previous:
            raise ValueError('Original pedal frames not monotonically nondecreasing')
        if pc!=0x67D2 or ix!=0xE080 or addr!=0xE0D7:
            raise ValueError('Unexpected original opcode/IX/physical pedal field')
        if any(not 0<=v<=255 for v in (data,raw,factor,bias,flag1,flag2)):
            raise ValueError('Original Z80 pedal values must be bytes')
        expected=expected_response(raw,factor,bias)
        if data!=expected:
            raise ValueError(f'Original MAME pedal output mismatch at event {i}')
        if first<0:first=frame
        last=frame;previous=frame
        seen[raw]+=1;per_pair[(factor,bias)]+=1
        min_value=min(min_value,data);max_value=max(max_value,data)
    if require_complete_sweep and len(seen)!=256:
        raise ValueError('All 256 original analogue pedal values were not tested')
    return {'source':'authentic 1991 arcade MAME original Z80 67D2 write tap',
            'source_pc':'67D2','original_ix':'E080',
            'physical_slot_address':'E0D7','original_opcode_writes':len(rows),
            'first_frame':first,'last_frame':last,
            'unique_8bit_pedal_inputs':len(seen),'min_response':min_value,
            'max_response':max_value,
            'distinct_factor_bias_pairs':len(per_pair),
            'mismatches':0,
            'scope':'Live original pedal-byte arithmetic, not acceleration/traction/steering dynamics'}


def audit_file(path:Path,require_complete_sweep:bool=False)->dict:
    with path.open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError('Original pedal trace header mismatch')
        report=audit_rows(list(reader),require_complete_sweep)
    digest=sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
    report['private_trace_sha256']=digest.hexdigest()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('private_pedal_trace',type=Path)
    p.add_argument('--complete-sweep',action='store_true')
    p.add_argument('--out',type=Path,
                   default=Path('local/private-runtime/pedal_parity.json'))
    args=p.parse_args()
    report=audit_file(args.private_pedal_trace,args.complete_sweep)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
