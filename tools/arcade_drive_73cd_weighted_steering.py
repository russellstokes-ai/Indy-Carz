#!/usr/bin/env python3
"""Original arcade master Z80 73CD-73F5 two-step weighted steering input.

The original code selects a factor byte from fixed ROM 7635+ceil(abs(E76C)/2),
multiplies by original register B through X-ROM slot1, and multiplies its
rounded low byte by original IX-1 through slot1 again. Exact original
byte-rounding requires TWO operations, not one combined float multiplication.

Original NEG 0x80 sets signed overflow and calls original 1C85, which
returns A=0x7F (saturated magnitude 127); it does NOT terminate the game.
The authentic source ROM and lookup values stay PRIVATE. This checker
executes genuine original Z80 CPU bytes and saturated helper 1C85,
challenging an independent fixed-point model.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA="f137ec1e52589f580d21bf370502753fa3b0ecbb4fac4f0f4b5482d8fba30afb"
TABLE_SHA="3a5d994a8ded086885bf45b3c630b760aad9b071cb327fa4f0b29c2de9461360"
HELPER_SHA="b2176ba933a6014e21c734665d4e0da5ef6dbf00c6a3a01314b8658ef8a8a79f"
START,STOP,BASE,HELPER=0x73CD,0x73F6,0x7635,0x1C85

def _valid(motion:int,b:int,car_ff:int)->None:
    if any(not isinstance(n,int) or not 0<=n<=255 for n in (motion,b,car_ff)):
        raise ValueError("Original motion byte, B and IX-1 require 8-bit inputs")

def round8(a:int,b:int)->int:
    if any(not 0<=n<=255 for n in (a,b)):
        raise ValueError("Original signed-free slot1 factors must be bytes")
    return (a*b+128)>>8

def table_index(motion:int)->int:
    if not 0<=motion<=255:raise ValueError("Original angular input must be 8-bit")
    value=motion if motion<=127 else 256-motion
    # Original NEG on -128 saturates through helper 1C85 to 127.
    value=min(127,value)
    return (value+1)>>1

def independent(motion:int,b:int,car_ff:int,factor:int)->dict:
    _valid(motion,b,car_ff)
    if not 0<=factor<=255:raise ValueError("Synthetic lookup factor must be a byte")
    pos=table_index(motion)
    first=round8(factor,b)
    second=round8(car_ff,first)
    return {"weighted":second,"first_low":first,"factor":factor,
            "table_index":pos,
            "xr_addresses":((factor<<8)|b,(car_ff<<8)|first),
            "neg128_saturated":motion==128,
            "next_pc":STOP}

def original_z80(master:bytes,xrom:bytes,motion:int,b:int,car_ff:int)->dict:
    _valid(motion,b,car_ff)
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Private original Z80 and X-ROM images required")
    a=h=l=0;pc=START
    sign=carry=zero=overflow=False
    xr=0;stack=[];addrs=[];first=None;weighted=None;factor=None
    for _ in range(40):
        op=master[pc]
        if op==0x3A:
            addr=master[pc+1]|master[pc+2]<<8
            if addr==0xE76C:a=motion
            elif addr==0xFFFE:
                a=xrom[0x20000+2*xr]
                weighted=a
            else:raise ValueError("Unexpected original Z80 input source")
            pc+=3
        elif op==0xB7:
            carry=False;sign=bool(a&128);zero=a==0
            overflow=False;pc+=1
        elif op==0xF2:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0x73D9:raise ValueError("Original positive motion branch changed")
            pc=target if not sign else pc+3
        elif op==0xED:
            if master[pc+1]!=0x44:raise ValueError("Expected original NEG opcode")
            before=a;a=(-a)&255
            carry=before!=0;overflow=before==128
            sign=bool(a&128);zero=a==0;pc+=2
        elif op==0xEC:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=HELPER:raise ValueError("Unexpected original signed saturation helper")
            if overflow:
                stack.append(pc+3);pc=HELPER
            else:pc+=3
        elif op==0x3E:
            if pc!=HELPER or master[pc+1]!=0x7F:
                raise ValueError("Original NEG-overflow saturation helper differs")
            a=0x7F;pc+=2
        elif op==0xC9:
            if pc!=HELPER+2 or not stack:
                raise ValueError("Unexpected original saturation return")
            pc=stack.pop()
        elif op==0xCB:
            if master[pc+1]!=0x3F:raise ValueError("Unexpected original SRL")
            carry=bool(a&1);a>>=1;zero=a==0;pc+=2
        elif op==0x21:
            value=master[pc+1]|master[pc+2]<<8
            if value!=BASE:raise ValueError("Unexpected original lookup table base")
            h,l=value>>8,value&255;pc+=3
        elif op==0x8D:
            value=a+l+int(carry)
            carry=value>255;a=value&255;zero=a==0
            sign=bool(a&128);pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0xD2:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0x73E4:raise ValueError("Unexpected original carry branch")
            pc=addr if not carry else pc+3
        elif op==0x24:h=(h+1)&255;pc+=1
        elif op==0x66:
            address=(h<<8)|l
            if not BASE<=address<BASE+65:raise ValueError("Original factor table index escaped")
            h=master[address];factor=h;pc+=1
        elif op==0x68:l=b;pc+=1
        elif op==0x22:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0xFFFE:raise ValueError("Unexpected original X-ROM latch")
            xr=(h<<8)|l;addrs.append(xr);pc+=3
        elif op==0x2A:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0xFFFE:raise ValueError("Unexpected original X-ROM word read")
            low=xrom[0x20000+2*xr];high=xrom[0x20000+2*xr+1]
            first=low;h,l=high,low;pc+=3
        elif op==0xDD:
            if master[pc+1:pc+3]!=bytes((0x66,0xFF)):
                raise ValueError("Unexpected original indexed car factor")
            h=car_ff;pc+=3
        elif op==0xF5:pc+=1
        else:raise ValueError(f"Unexpected original steering instruction {op:02X} at {pc:04X}")
        if pc==STOP:
            if stack or len(addrs)!=2 or factor is None:
                raise ValueError("Original weighted steering lookup incomplete")
            return {"weighted":weighted,"first_low":first,
                    "factor":factor,"table_index":table_index(motion),
                    "xr_addresses":tuple(addrs),
                    "neg128_saturated":motion==128,"next_pc":STOP}
        if not (START<=pc<STOP or HELPER<=pc<=HELPER+2):
            raise ValueError(f"Original weighted steering left bounded stage at {pc:04X}")
    raise ValueError("Original steering weighted stage exceeded opcode budget")

def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Private checksum-verified owner master required")
    if len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Private checksum-verified owner X-ROM required")
    for a,b,digest in ((START,STOP,STAGE_SHA),(BASE,BASE+65,TABLE_SHA),
                       (HELPER,HELPER+3,HELPER_SHA)):
        if sha256(master[a:b]).hexdigest()!=digest:
            raise ValueError(f"Original weighted steering source checksum differs at {a:04X}")
    rng=Random(0x73CD);paths=Counter()
    for i in range(cases):
        motion=i%256
        b=rng.randrange(256)
        car=rng.randrange(256)
        factor=master[BASE+table_index(motion)]
        expected=independent(motion,b,car,factor)
        actual=original_z80(master,xrom,motion,b,car)
        if expected!=actual:raise AssertionError(f"Original two-stage steering mismatch {i}")
        paths["saturated_negative_128" if motion==128 else
              "other_motion"]+=1
    return {"source":"Authentic original arcade master Z80 73CD-73F5 and 1C85",
            "cases":cases,"mismatches":0,
            "original_factor_table_entries":65,
            "original_neg128_overflow_helper":"1C85 returns A=0x7F, DOES NOT exit the game",
            "paths":dict(paths),
            "scope":"Bounded two-step steering input weighting; 73F6+ angle adjustment still open"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_master",type=Path)
    p.add_argument("private_xrom",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    args=p.parse_args()
    print(json.dumps(verify(args.private_master.read_bytes(),args.private_xrom.read_bytes(),args.cases),indent=2))
