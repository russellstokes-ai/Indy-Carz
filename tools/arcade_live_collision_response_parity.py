#!/usr/bin/env python3
"""Original 1991 arcade live two-car collision callback/restore parity.

Three PRIVATE original MAME captures, from exact Z80 PC breakpoint/LDIR taps:
- B86C dispatch (IX/IY status) with B884 call addresses
- B884, B8AB, B8AC, B8E3 and 1689 instruction hits
- 66 original LDIR CPU writes at B8BA per successful restoration

The public report includes count/branch evidence only, not game ROM,
source tables, graphics, or private car-state records. Collision forces
and the inner BC8C callback remain open.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

MASTER_SHA='521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7'
CARS=tuple(0xE080+i*0x100 for i in range(5))
DISPATCH_COLS=('frame','stage','ix','iy','status_ix','status_iy','e941')
HANDLER_COLS=('frame','pc','ix','iy','e941','car_b1','car_7c','e608','a')
COPY_COLS=('frame','pc','ix','hl','dest','data','src_before','source_val')


def _hex(row,field):
    try:return int(row[field],16)
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError(f'Original MAME {field} value invalid') from exc


def _dec(row,field):
    try:return int(row[field],10)
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError(f'Original MAME {field} value invalid') from exc


def dispatch_audit(rows:list[dict[str,str]])->dict:
    if not rows:raise ValueError('Empty original B86C dispatch trace')
    groups=[];current=None
    for row in rows:
        if not set(DISPATCH_COLS).issubset(row):raise ValueError('Original dispatch columns missing')
        f=_dec(row,'frame');ix=_hex(row,'ix');iy=_hex(row,'iy')
        ix_flag=_hex(row,'status_ix');iy_flag=_hex(row,'status_iy')
        if (f<=0 or ix not in CARS or iy not in CARS or
            (row['stage']=='DISPATCH' and ix==iy) or
            not all(0<=v<256 for v in (ix_flag,iy_flag))):
            raise ValueError('Original B86C branch frame, car pointers or status invalid')
        if current is not None and f<current['frame']:
            raise ValueError('Original B86C frame order changed')
        if row['stage']=='DISPATCH':
            current={'frame':f,'ix':ix,'iy':iy,'first_bit1':bool(ix_flag&2),
                     'second_bit1':bool(iy_flag&2),'actual':[]}
            groups.append(current)
        elif row['stage']=='SERVICE':
            if current is None or f!=current['frame']:
                raise ValueError('Original B884 handler lacks matching B86C dispatch')
            current['actual'].append(ix)
        else:raise ValueError('Unknown original collision debugger stage')
    paths=Counter();events=[]
    for group in groups:
        expected=[]
        if not group['first_bit1']:expected.append(group['ix'])
        if not group['second_bit1']:expected.append(group['iy'])
        if group['actual']!=expected:
            raise ValueError('Original B86C -> B884 handler pointer/call order mismatch')
        paths[f'{len(expected)}_calls']+=1
        events.extend((group['frame'],ptr) for ptr in group['actual'])
    return {'dispatches':len(groups),'b884_calls':len(events),
            'dispatch_call_counts':dict(sorted(paths.items())),
            'ordered_calls':events}


def handler_audit(rows:list[dict[str,str]])->dict:
    if not rows:raise ValueError('Empty original B884 callback trace')
    groups=[];last_frame=-1
    for row in rows:
        if not set(HANDLER_COLS).issubset(row):raise ValueError('Original handler fields missing')
        f=_dec(row,'frame');ix=_hex(row,'ix');iy=_hex(row,'iy')
        if f<=0 or f<last_frame or ix not in CARS or iy not in CARS:
            raise ValueError('Original B884 instruction frame/car register invalid')
        last_frame=f
        vals={key:_hex(row,key) for key in ('e941','car_b1','car_7c','e608','a')}
        if any(not 0<=v<256 for v in vals.values()):
            raise ValueError('Original B884 byte register outside range')
        pc=row['pc'].upper()
        if pc=='B884':groups.append({'frame':f,'ix':ix,'steps':[],'original':vals})
        elif pc in ('B8AB','B8AC','B8E3','1689'):
            if not groups or f!=groups[-1]['frame'] or ix!=groups[-1]['ix']:
                raise ValueError('Original callback return does not match B884 entry')
            groups[-1]['steps'].append((pc,vals))
        else:raise ValueError('Original unrecognised B884 handler PC')
    exits=Counter();ordered=[];full_events=[]
    for group in groups:
        events=group['steps'];path=tuple(pc for pc,_ in events)
        if path==('B8AB',):
            if events[0][1]['e941']!=255:
                raise ValueError('Original B8AB early return marker mismatch')
            exits['e941_ff_early_return']+=1
        elif path==('B8AB','B8AC','B8E3'):
            b8ab,b8ac,b8e3=(entry[1] for entry in events)
            if b8ab['e941']==255 or b8ac['e941']!=b8ab['e941']:
                raise ValueError('Original B8AB/B8AC continuation marker mismatch')
            if not b8ac['car_b1']&128:
                raise ValueError('Original BIT7 guard should have skipped B8E3')
            if b8e3['car_7c']!=(b8ac['car_7c']|2):
                raise ValueError('Original B8E3 car+7C bit1 status write mismatch')
            exits['complete_66byte_restore']+=1
            full_events.append((group['frame'],group['ix']))
        else:
            raise ValueError('Original collision callback reached unverified path')
        if events[0][1]['e608']&15 !=5:
            raise ValueError('Original B884 bank-5 control not restored after BC8C')
        ordered.append((group['frame'],group['ix']))
    return {'handler_calls':len(groups),'callback_exits':dict(sorted(exits.items())),
            'ordered_calls':ordered,'full_restores':full_events}


def ldir_audit(rows:list[dict[str,str]])->dict:
    if not rows or len(rows)%66:
        raise ValueError('Original B8AC LDIR snapshot not divisible by 66 bytes')
    active=[];last=-1
    for start in range(0,len(rows),66):
        group=rows[start:start+66]
        first=group[0]
        f=_dec(first,'frame');ix=_hex(first,'ix')
        if f<=0 or f<last or ix not in CARS:raise ValueError('Original B8AC car/frame invalid')
        last=f
        for i,row in enumerate(group):
            if not set(COPY_COLS).issubset(row):raise ValueError('Original LDIR trace fields missing')
            if _dec(row,'frame')!=f or _hex(row,'ix')!=ix or _hex(row,'pc')!=0xB8BA:
                raise ValueError('Original B8AC LDIR instruction/car continuity invalid')
            if _hex(row,'hl')!=0xE72B+i or _hex(row,'dest')!=ix-0x80+i:
                raise ValueError('Original 66-byte LDIR memory source/destination mismatch')
            data=_dec(row,'data');source=_dec(row,'src_before')
            if not 0<=data<256 or data!=source or _dec(row,'source_val')!=1:
                raise ValueError('Original B8AC original memory copy byte mismatch')
        active.append((f,ix))
    return {'original_ldir_cpu_byte_writes':len(rows),'original_66byte_transfers':len(active),
            'ordered_restores':active,
            'car_transfer_counts':dict(sorted(Counter(f'{ix:04X}' for _,ix in active).items()))}


def audit_traces(dispatch:list[dict[str,str]],handler:list[dict[str,str]],ldir:list[dict[str,str]])->dict:
    d=dispatch_audit(dispatch);h=handler_audit(handler);l=ldir_audit(ldir)
    if d['ordered_calls']!=h['ordered_calls']:
        raise ValueError('Original B86C dispatch sequence differs from B884 entries')
    # These are three separate, original running-MAME instrumentations:
    # their frame counters may drift. Verify the *original car order*,
    # copy-byte parity and count; do not pretend frame IDs are identical.
    if [ix for _,ix in h['full_restores']]!=[ix for _,ix in l['ordered_restores']]:
        raise ValueError('Original B8AC car restoration sequence differs from actual 66-byte LDIR')
    return {
        'source':'authentic Indy Heat 1991 MAME 0.264, fixed-master B86C/B884/B8AB/B8AC/B8E3/B8BA',
        'live_dispatches':d['dispatches'],'live_b884_invocations':h['handler_calls'],
        'original_dispatch_call_counts':d['dispatch_call_counts'],
        'original_callback_return_paths':h['callback_exits'],
        'real_cpu_66byte_ldir_transfers':l['original_66byte_transfers'],
        'real_cpu_ldir_byte_writes':l['original_ldir_cpu_byte_writes'],
        'ldir_transfers_by_car':l['car_transfer_counts'],
        'mismatches':0,
        'scope':'original 2-car B884 selection and 66-byte state restores; LDIR captured in a separate MAME run so car order/count, NOT exact frame numbers, are compared; inner BC8C impulse/terrain remains OPEN',
    }


def _read_csv(path:Path,columns:tuple[str,...])->list[dict[str,str]]:
    with path.open(newline='',encoding='utf-8') as fh:
        reader=csv.DictReader(fh)
        if not set(columns).issubset(reader.fieldnames or []):
            raise ValueError(f'Private original MAME CSV header differs: {path.name}')
        return list(reader)


def audit_files(dispatch:Path,handler:Path,ldir:Path,master:Path)->dict:
    source=master.read_bytes()
    if len(source)!=0x90000 or sha256(source).hexdigest()!=MASTER_SHA:
        raise ValueError('Authentic checksum-verified original arcade master required')
    report=audit_traces(_read_csv(dispatch,DISPATCH_COLS),
                        _read_csv(handler,HANDLER_COLS),_read_csv(ldir,COPY_COLS))
    report['private_input_sha256']={key:sha256(path.read_bytes()).hexdigest()
                                   for key,path in (('dispatch',dispatch),('callback',handler),('ldir',ldir))}
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('private_dispatch_csv',type=Path)
    p.add_argument('private_callback_csv',type=Path)
    p.add_argument('private_ldir_csv',type=Path)
    p.add_argument('private_master_rom',type=Path)
    p.add_argument('--out',type=Path,default=Path('local/private-runtime/collision_response_audit.json'))
    a=p.parse_args();report=audit_files(a.private_dispatch_csv,a.private_callback_csv,
                                       a.private_ldir_csv,a.private_master_rom)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
