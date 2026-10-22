#!/usr/bin/env python3
"""Exact original 1991 arcade live MAME movement and car-footprint parity.

Reads PRIVATE MAME Z80 CPU write-tap CSV from mame_capture_drive_geometry.lua.
Never publishes private ROM bytes, QRAM maps, artwork or original tracks.
Accepts actual ORIGINAL original geometry-only path as well as integrated
position->geometry path; unrecognised write order fails closed.

This is motion-integration and footprint parity, NOT complete car physics,
traction, terrain impacts, AI paths, fuel or damage.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
import math
from pathlib import Path

FIELDS = ('frame','pc','ix','addr','data','angle','motion','x','y','course','round')
PAIRS = ((0x7555,0xE735),(0x756F,0xE72B),
         (0x75B2,0xE73D),(0x75BB,0xE737),(0x75C3,0xE73B),
         (0x75CC,0xE739),(0x75D4,0xE733),(0x75DD,0xE72D),
         (0x75E5,0xE731),(0x75EE,0xE72F))
CAR_IX = tuple(0xE080 + i*0x100 for i in range(6))


def signed8(v:int)->int:
    if not 0<=v<256:raise ValueError('Original byte outside 0..255')
    return v-256 if v>=128 else v


def trig8(angle:int, sine:bool)->int:
    if not 0<=angle<256:raise ValueError('Original heading outside 8-bit domain')
    fn=math.sin if sine else math.cos
    return max(-128,min(127,round(128*fn(angle*math.tau/256))))


def step(original_trig:int, motion:int)->int:
    value=min(32767,max(-32768,original_trig*signed8(motion)*2))
    return (value*4+128)//256


def center_after(angle:int,motion:int,x:int,y:int)->tuple[int,int]:
    if not 0<=x<65536 or not 0<=y<65536:
        raise ValueError('Original centre outside 16-bit domain')
    return ((x+step(trig8(angle,True),motion))&65535,
            (y+step(trig8(angle,False),motion))&65535)


def corners(angle:int,x:int,y:int)->dict[int,int]:
    if not 0<=x<65536 or not 0<=y<65536:
        raise ValueError('Original centre outside 16-bit domain')
    s,c=trig8(angle,True),trig8(angle,False)
    return {0xE73D:(x+3*s-2*c)&65535,
            0xE737:(x-3*s+2*c)&65535,
            0xE73B:(x+3*s+2*c)&65535,
            0xE739:(x-3*s-2*c)&65535,
            0xE733:(y+3*c+2*s)&65535,
            0xE72D:(y-3*c-2*s)&65535,
            0xE731:(y+3*c-2*s)&65535,
            0xE72F:(y-3*c+2*s)&65535}


def parse_row(row:dict[str,str])->dict[str,int]:
    if not set(FIELDS).issubset(row):
        raise ValueError('Original trace CSV header missing columns')
    result={}
    for key in FIELDS:
        try:result[key]=int(row[key],16 if key in ('pc','ix','addr') else 10)
        except (ValueError,TypeError) as exc:
            raise ValueError(f'Invalid original trace {key}') from exc
    for key in ('data','angle','motion','course','round'):
        if not 0<=result[key]<256:raise ValueError(f'Original {key} not 8-bit')
    if not 0<=result['x']<65536 or not 0<=result['y']<65536:
        raise ValueError('Invalid original 16-bit centre')
    if result['ix'] not in CAR_IX or result['frame']<=0:
        raise ValueError('Unrecognized original car pointer or frame')
    return result


def audit_trace_rows(rows:list[dict[str,str]])->dict:
    """Require authentic instruction/write ordering and exact byte output.

    Original vehicle geometry sometimes runs WITHOUT the original position
    integrator. Accept 20-write integrated groups and 16-write geometry-only
    groups independently rather than inventing a missing motion step.
    """
    if not rows:raise ValueError('Original movement trace is empty')
    parsed=[parse_row(row) for row in rows]
    n=len(parsed);i=0;last_frame=-1;counts=Counter();car_counts=Counter()
    movement_angles=set();geometry_angles=set();first_frame=parsed[0]['frame']
    while i<n:
        start=parsed[i]
        if start['pc'] not in (0x7555,0x75B2):
            raise ValueError(f'Unexpected original write at row {i}')
        integrated=start['pc']==0x7555
        order=PAIRS if integrated else PAIRS[2:]
        size=len(order)*2
        if i+size>n:
            raise ValueError('Incomplete original movement/footprint instruction group')
        group=parsed[i:i+size]
        frame,ix=start['frame'],start['ix']
        if frame<last_frame or any(row['frame']!=frame or row['ix']!=ix for row in group):
            raise ValueError('Original frame/car continuity changed inside instruction group')
        last_frame=frame
        for j,(pc,addr) in enumerate(order):
            if (group[j*2]['pc'],group[j*2]['addr'],
                group[j*2+1]['pc'],group[j*2+1]['addr'])!=(pc,addr,pc,addr+1):
                raise ValueError(f'Unexpected original instruction/write order at row {i+j*2}')
        observed={addr:group[j*2]['data']|(group[j*2+1]['data']<<8)
                  for j,(_,addr) in enumerate(order)}
        if integrated:
            heading,motion=start['angle'],start['motion']
            x,y=center_after(heading,motion,start['x'],start['y'])
            if observed[0xE735]!=x or observed[0xE72B]!=y:
                raise ValueError(f'Original position calculation mismatch at event {i}')
            if any(row['angle']!=heading or row['motion']!=motion for row in group[:4]):
                raise ValueError('Original movement inputs changed mid-step')
            geometry_start=4
            movement_angles.add(heading)
            counts['integrated_position_updates']+=1
            counts['nonzero_motion_updates']+=motion!=0
        else:
            x,y=start['x'],start['y']
            geometry_start=0
            counts['geometry_only_updates']+=1
        geometry_heading=group[geometry_start]['angle']
        if any((row['x'],row['y'],row['angle'])!=(x,y,geometry_heading)
               for row in group[geometry_start:]):
            raise ValueError('Original footprint centre/angle changed mid-group')
        for address,expected in corners(geometry_heading,x,y).items():
            if observed[address]!=expected:
                raise ValueError(
                    f'Original footprint word mismatch at event {i}, address {address:04X}')
        geometry_angles.add(geometry_heading)
        car_counts[f'{ix:04X}']+=1
        counts['geometry_updates']+=1
        counts['geometry_coordinate_words']+=8
        i+=size
    return {
        'source':'authentic 1991 Indy Heat arcade live MAME master Z80 instruction writes',
        'original_bus_byte_writes':n,'first_frame':first_frame,'last_frame':last_frame,
        'verified_position_updates':counts['integrated_position_updates'],
        'nonzero_motion_updates':counts['nonzero_motion_updates'],
        'verified_geometry_updates':counts['geometry_updates'],
        'verified_geometry_words':counts['geometry_coordinate_words'],
        'geometry_only_original_branches':counts['geometry_only_updates'],
        'movement_angles_seen':len(movement_angles),
        'geometry_angles_seen':len(geometry_angles),
        'updates_by_car':dict(sorted(car_counts.items())),
        'mismatches':0,
        'scope':'exact movement integration/rotated footprint writes only; not acceleration, terrain impacts, AI or full collision'
    }


def audit_file(path:Path)->dict:
    with path.open(newline='',encoding='utf-8') as fh:
        reader=csv.DictReader(fh)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError('Original movement capture has unexpected CSV header')
        report=audit_trace_rows(list(reader))
    digest=sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b''):
            digest.update(chunk)
    report['private_trace_sha256']=digest.hexdigest()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('private_trace',type=Path)
    p.add_argument('--out',type=Path,
                   default=Path('local/private-runtime/live_drive_parity_report.json'))
    args=p.parse_args()
    result=audit_file(args.private_trace)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
