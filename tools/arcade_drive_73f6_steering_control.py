#!/usr/bin/env python3
"""Original arcade Z80 73F6–7441 bounded steering angular control.

Authentic 1991 Indy Heat rev1 CPU bytes from private user-owned ROM are
interpreted with original helpers 0B35/0B3E/1C85. All original source
and RAM data remain private. The independent model uses exact 16-bit
wrapped subtraction, carried borrow, arithmetic shifting, signed-8
saturation and car steering-sign comparison.

This stage exits with A=0x20..0x7F and PC7442, ready for the next
X-ROM geometry/steering computation. It is NOT full tyre handling,
wall impact, AI steering or an end-to-end playable game.
"""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="85ea5f2503ce591f3e5a3bac56f29a956b1e194e4c0a67eedc20ee196147cc8a"
HELPER_SHA="f6d4c3a683d4972678811aa2f950504d427857151a402945a268125e69bf3460"
SATURATION_SHA="52de6ed276b24bbecf3abd72b575221dc89da01a660d99a0cd65c937a293f4c5"
START,STOP=0x73F6,0x7442

def _check(e789:int,e773:int,e787:int,e771:int,car79:int)->None:
    if (any(not isinstance(x,int) or not 0<=x<=65535
            for x in (e789,e773,e787,e771))
            or not isinstance(car79,int) or not 0<=car79<=255):
        raise ValueError("Four original unsigned-16 words and indexed byte IX+79 required")

def signed16(value:int)->int:
    return value-65536 if value>=32768 else value

def clamp_signed8(value:int)->int:
    return min(127,max(-128,value))

def independent(e789:int,e773:int,e787:int,e771:int,car79:int)->dict:
    _check(e789,e773,e787,e771,car79)
    # Original 73DE ADC A,L leaves carry CLEAR for every valid E76C:
    # indexed factor address is only 0x7635..0x7675.
    first=e789-e773
    original_borrow=int(first<0)
    second=((first&65535)-e787-original_borrow)&65535
    wrapped=(second+e771)&65535
    angular=clamp_signed8(signed16(wrapped)>>7)

    # The 0B3E signed clamp returns -128 or +127.
    # The NEG on -128 calls original 1C85: returns +127.
    magnitude=min(127,abs(angular))
    same_direction=(angular<0)==bool(car79&128)
    if same_direction:
        control=min(127,64+magnitude)
    else:
        control=max(32,64-magnitude)
    return {
        "a":control,"wrapped_word":wrapped,
        "angular_sample":angular,
        "direction_matches":same_direction,
        "borrow_from_first_subtraction":original_borrow,
        "next_pc":STOP
    }

def original_z80(master:bytes,e789:int,e773:int,e787:int,
                 e771:int,car79:int)->dict:
    """Strictly interpret REAL Z80 opcodes and all returning helpers."""
    _check(e789,e773,e787,e771,car79)
    if len(master)!=0x90000:
        raise ValueError("Original privately authenticated arcade ROM size required")
    ram={0xE789:e789,0xE773:e773,0xE787:e787,0xE771:e771}
    pc=START
    a=b=c=d=e=h=l=0
    carry=zero=sign=overflow=False
    stack=[]
    wrapped_word=angular=None
    for _ in range(96):
        op=master[pc]
        if op==0x2A:
            addr=master[pc+1]|master[pc+2]<<8
            if addr not in ram:raise ValueError("Unknown original 16-bit steering state read")
            value=ram[addr];h,l=value>>8,value&255;pc+=3
        elif op==0xED:
            ext=master[pc+1]
            if ext==0x5B:
                addr=master[pc+2]|master[pc+3]<<8
                if addr not in ram:raise ValueError("Unknown original DE source")
                value=ram[addr];d,e=value>>8,value&255;pc+=4
            elif ext==0x52:
                raw=(h<<8|l)-(d<<8|e)-int(carry)
                carry=raw<0;value=raw&65535
                h,l=value>>8,value&255
                zero=value==0;sign=bool(value&32768);pc+=2
            elif ext==0x44:
                old=a;a=(-a)&255;carry=old!=0
                zero=a==0;sign=bool(a&128);overflow=old==128;pc+=2
            else:raise ValueError(f"Unknown original ED opcode {ext:02X}")
        elif op==0x19:
            raw=(h<<8|l)+(d<<8|e)
            carry=raw>65535;value=raw&65535
            h,l=value>>8,value&255;pc+=1
        elif op==0xCB:
            ext=master[pc+1]
            if ext==0x2C:
                carry=bool(h&1);h=(h>>1)|(h&128);sign=bool(h&128)
            elif ext==0x1D:
                old=l;l=(l>>1)|(int(carry)<<7);carry=bool(old&1)
            elif ext==0x25:
                carry=bool(l&128);l=(l<<1)&255
            elif ext==0x7C:
                zero=not bool(h&128);sign=bool(h&128);overflow=zero
            else:raise ValueError("Unknown original bit/shift opcode")
            pc+=2
        elif op==0x7C:a=h;pc+=1
        elif op==0x8F:
            old=a;raw=2*a+int(carry);a=raw&255;carry=raw>255
            zero=a==0;sign=bool(a&128);overflow=bool((old^a)&128);pc+=1
        elif op==0xEC:
            dest=master[pc+1]|master[pc+2]<<8
            if dest not in (0x0B35,0x0B3E,0x1C85):
                raise ValueError("Unknown original signed saturation CALL")
            if overflow:stack.append(pc+3);pc=dest
            else:pc+=3
        elif op==0xF2:
            dest=master[pc+1]|master[pc+2]<<8
            pc=dest if not sign else pc+3
        elif op==0x3E:a=master[pc+1];pc+=2
        elif op==0xB7:
            zero=a==0;sign=bool(a&128);carry=False
            overflow=a.bit_count()%2==0;pc+=1
        elif op==0xC9:
            if not stack:raise ValueError("Unbalanced original helper RET")
            pc=stack.pop()
        elif op==0xDD:
            if master[pc+1:pc+3]!=bytes((0x66,0x79)):
                raise ValueError("Unexpected original indexed heading field")
            h=car79;pc+=3
        elif op==0xFA:
            dest=master[pc+1]|master[pc+2]<<8
            pc=dest if sign else pc+3
        elif op==0x20:
            delta=master[pc+1]
            delta=delta-256 if delta>=128 else delta
            pc+=2+(delta if not zero else 0)
        elif op==0xC6:
            imm=master[pc+1]
            old=a;raw=a+imm;a=raw&255;carry=raw>255
            zero=a==0;sign=bool(a&128)
            overflow=bool((~(old^imm)&(old^a))&128);pc+=2
        elif op==0xC3:pc=master[pc+1]|master[pc+2]<<8
        elif op==0xC2:
            dest=master[pc+1]|master[pc+2]<<8
            pc=dest if not zero else pc+3
        elif op==0xFE:
            imm=master[pc+1]
            result=(a-imm)&255
            sign=bool(result&128);zero=result==0;carry=a<imm;pc+=2
        else:
            raise ValueError(f"Unexpected original steering opcode {op:02X} at {pc:04X}")

        if pc==0x740A:wrapped_word=(h<<8)|l
        if pc==0x741B:angular=a-256 if a>=128 else a
        if pc==STOP:
            if stack or wrapped_word is None or angular is None:
                raise ValueError("Original steering control path incomplete")
            return {
                "a":a,"wrapped_word":wrapped_word,
                "angular_sample":angular,
                "direction_matches":(angular<0)==bool(car79&128),
                "borrow_from_first_subtraction":int(e789<e773),
                "next_pc":STOP
            }
        if not (START<=pc<STOP or 0x0B35<=pc<=0x0B48
                or 0x1C85<=pc<=0x1C87):
            raise ValueError(f"Original steering left bounded stage at {pc:04X}")
    raise ValueError("Original steering control opcode budget exceeded")

def verify(master:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Private checksum-verified original master required")
    for start,stop,digest in ((START,STOP,STAGE_SHA),
                               (0x0B35,0x0B49,HELPER_SHA),
                               (0x1C85,0x1C88,SATURATION_SHA)):
        if hashlib.sha256(master[start:stop]).hexdigest()!=digest:
            raise ValueError(f"Original steering opcode/helper SHA mismatch {start:04X}")
    if not 0<=cases<=200000:
        raise ValueError("Invalid steering control parity case count")
    rng=Random(0x73F6);hist=Counter()
    for i in range(cases):
        sources=tuple(rng.choice((0,1,0x7FFF,0x8000,0xFFFF,rng.randrange(65536)))
                      for _ in range(4))
        car79=rng.randrange(256)
        inputs=(*sources,car79)
        independent_result=independent(*inputs)
        original_result=original_z80(master,*inputs)
        if independent_result!=original_result:
            raise AssertionError(f"Original 73F6 steering control discrepancy {i}")
        hist["same_direction" if independent_result["direction_matches"]
             else "opposite_direction"]+=1
    return {
        "source":"Original arcade master Z80 73F6-7441, helpers 0B35/0B3E/1C85",
        "cases":cases,"mismatches":0,
        "branch_histogram":dict(sorted(hist.items())),
        "control_range":[32,127],
        "scope":"Bounded saturated control angle A at 7442; subsequent X-ROM and steering writes still open"
    }

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_master",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    args=p.parse_args()
    print(json.dumps(verify(args.private_original_master.read_bytes(),args.cases),indent=2))
