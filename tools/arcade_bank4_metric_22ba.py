#!/usr/bin/env python3
"""Authentic Indy Heat 1991 arcade bank4 22BA–2304 integer/X-ROM metric.

First bank-4 racer selection at 20A8 invokes 22BA at CPU 213F.
This module independently reconstructs the bounded 22BA numeric result
using only integer arithmetic, comparing against genuine original Z80
instructions and the user's privately authenticated X-ROM slot1 lookup.

This is exact numerical parity, NOT verified AI strategy or race physics.
Original ROM contents/lookup tables remain private and excluded from GitHub.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA="3a2d4fc9529375ad9b0c0b847228e936b88edb5655c78ed47d542b380127a6ec"
START,STOP=0x22BA,0x2305
BANK4_BASE=0x30000


def _inputs(d:int,e:int,divider:int,e639:int,car3a:int,e623:int)->None:
    if (divider not in (2,4) or
        any(not 0<=v<256 for v in (d,e,e639,car3a,e623))):
        raise ValueError("Original two-axis bytes, bank4 divider 2/4, car/parameter bytes required")


def xrom_rounded_u8(a:int,b:int)->int:
    """Original X-ROM slot1 low output, independently exhaustively verified."""
    if not 0<=a<256 or not 0<=b<256:
        raise ValueError("Unsigned 8-bit X-ROM operands required")
    return (a*b+128)>>8


def independent(d:int,e:int,divider:int,e639:int,car3a:int,e623:int)->dict:
    """Original 22BA output HL. Z80 carry/rotate maths simplifies to this.

    First SUB B; INC A is modulo 256. OR A clears carry; SBC HL,DE.
    Negative 16-bit unsigned borrow returns initial DE immediately. For
    the other path, the Z80 CP/JR-C, RRA/RR-L sequence and original
    divider 2 or 4 select a capped 8-bit fraction. Both X-ROM slot1
    lookups use exact 8-bit round-to-nearest product, not floats.
    """
    _inputs(d,e,divider,e639,car3a,e623)
    de=(d<<8)|e
    numerator=(((e639-divider+1)&255)<<8)
    difference=numerator-de
    if difference<0:
        return {"path":"early_no_room","hl":de}

    fraction=min(255,difference//divider)
    first=xrom_rounded_u8((car3a*2)&255,fraction)
    second=xrom_rounded_u8(first,e623)
    return {
        "path":"computed","hl":(de+4*second)&65535,
        "fraction":fraction,"first":first,"second":second,
    }


def original_opcodes(master:bytes,xrom:bytes,d:int,e:int,divider:int,
                     e639:int,car3a:int,e623:int)->dict:
    """Execute only actual original bounded bank4 Z80 opcode forms.

    The external X-ROM memory-mapped FFFE latch reads are supplied by
    the original local user-owned ROM. Unsupported opcodes, addresses and
    branches reject; no guessed gameplay interpretation is performed.
    """
    _inputs(d,e,divider,e639,car3a,e623)
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Authentic master and X-ROM dimensions required")
    code=bytearray(master[:0xE000])
    code[0x2000:0xA000]=master[BANK4_BASE:BANK4_BASE+0x8000]
    ram={0xE638:divider,0xE639:e639,0xE623:e623,0xE624:17,
         0xE080+2:d,0xE080+4:e,0xE080+0x3A:car3a}
    a=b=h=l=de_hi=de_lo=0
    carry=zero=sign=False
    pc=START
    xrom_addr=0
    fraction=first=second=None

    def read(addr:int)->int:
        if addr==0xFFFE:
            return xrom[0x20000+2*xrom_addr]  # original slot1 low output
        if addr<0xE000:return code[addr]
        if addr not in ram:raise ValueError(f"Unexpected original RAM read {addr:04X}")
        return ram[addr]

    for _ in range(95):
        op=code[pc]
        if op==0xDD:
            ext,disp=code[pc+1:pc+3]
            if (ext,disp)==(0x56,2):de_hi=read(0xE080+2)
            elif (ext,disp)==(0x5E,4):de_lo=read(0xE080+4)
            elif (ext,disp)==(0x66,0x3A):h=read(0xE080+0x3A)
            else:raise ValueError("Unknown original car indexed opcode")
            pc+=3
        elif op==0x3A:
            addr=code[pc+1]|code[pc+2]<<8
            if addr not in (0xE638,0xE639,0xFFFE):
                raise ValueError("Unknown original global/X-ROM byte read")
            a=read(addr)
            if addr==0xFFFE:
                if first is None:first=a
                else:second=a
            pc+=3
        elif op==0x2A:
            addr=code[pc+1]|code[pc+2]<<8
            if addr!=0xE623:raise ValueError("Unknown original word input")
            l,h=read(addr),read(addr+1);pc+=3
        elif op==0x47:b=a;pc+=1
        elif op==0x90:
            v=a-b;carry=v<0;a=v&255
            zero=a==0;sign=bool(a&128);pc+=1
        elif op==0x3C:
            a=(a+1)&255;zero=a==0;sign=bool(a&128);pc+=1
        elif op==0x67:h=a;pc+=1
        elif op==0x2E:l=code[pc+1];pc+=2
        elif op==0xB7:
            zero=a==0;carry=False;sign=bool(a&128);pc+=1
        elif op==0xED:
            if code[pc+1]!=0x52:raise ValueError("Unexpected original 16-bit SBC")
            raw=((h<<8)|l)-((de_hi<<8)|de_lo)-int(carry)
            carry=raw<0
            answer=raw&65535
            h,l=answer>>8,answer&255
            zero=answer==0;sign=bool(answer&0x8000);pc+=2
        elif op in (0x30,0x38,0x28):
            delta=code[pc+1]
            if delta>=128:delta-=256
            taken=not carry if op==0x30 else carry if op==0x38 else zero
            pc+=2+(delta if taken else 0)
        elif op==0xEB:
            de_hi,de_lo,h,l=h,l,de_hi,de_lo
            pc+=1
        elif op==0xC9:
            if pc==0x22D2:
                return {"path":"early_no_room","hl":(h<<8)|l}
            if pc!=0x2304:raise ValueError("Unexpected original return site")
            if fraction is None or first is None or second is None:
                raise ValueError("Original X-ROM double lookup not completed")
            return {"path":"computed","hl":(h<<8)|l,
                    "fraction":fraction,"first":first,"second":second}
        elif op==0x7C:a=h;pc+=1
        elif op==0xB8:
            raw=a-b
            carry=raw<0;zero=raw==0;sign=bool(raw&128);pc+=1
        elif op==0x18:
            delta=code[pc+1]
            if delta>=128:delta-=256
            pc+=2+delta
        elif op==0x1F:    # RRA, signed carry from previous original CP
            prior=a
            a=((int(carry)<<7)|(a>>1))&255
            carry=bool(prior&1);pc+=1
        elif op==0xCB:
            ext=code[pc+1]
            if ext==0x1D:  # RR L
                prior=l
                l=((int(carry)<<7)|(l>>1))&255
                carry=bool(prior&1)
            elif ext==0x24: # SLA H
                prior=h;h=(h<<1)&255;carry=bool(prior&128)
            elif ext==0x14: # RL H
                prior=h;h=((h<<1)|int(carry))&255
                carry=bool(prior&128)
            else:raise ValueError("Unexpected original CB shift")
            pc+=2
        elif op==0x05:
            b=(b-1)&255;zero=b==0;sign=bool(b&128);pc+=1
        elif op==0x22:
            addr=code[pc+1]|code[pc+2]<<8
            if addr!=0xFFFE:raise ValueError("Unexpected original X-ROM address write")
            xrom_addr=(h<<8)|l;pc+=3
        elif op==0x87:
            product=a*2;carry=product>255
            a=product&255;zero=a==0;sign=bool(a&128);pc+=1
        elif op==0x26:h=code[pc+1];pc+=2
        elif op==0x6F:l=a;pc+=1
        elif op==0x19:
            raw=((h<<8)|l)+((de_hi<<8)|de_lo)
            carry=raw>65535
            out=raw&65535;h,l=out>>8,out&255;pc+=1
        else:
            raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")

        if pc==0x22E5:fraction=l
        if not START<=pc<STOP:
            raise ValueError("Original numerical stage escaped its fixed CPU range")
    raise ValueError("Original numerical stage instruction budget exceeded")


def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Original authenticated master ROM required")
    if len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Original authenticated X-ROM required")
    bank4=master[BANK4_BASE:BANK4_BASE+0x8000]
    if sha256(bank4[START-0x2000:STOP-0x2000]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original 22BA machine-code SHA changed")
    if not 0<=cases<=250000:raise ValueError("Invalid parity case budget")
    for high in range(256):
        for low in range(256):
            if xrom[0x20000+2*((high<<8)|low)] != xrom_rounded_u8(high,low):
                raise AssertionError("Original slot1 X-ROM low output does not match integer formula")

    rng=Random(0x22BA)
    paths=Counter();frac_paths=Counter()
    for i in range(cases):
        divider=2 if i&1 else 4
        e639=rng.choice((0,1,2,4,8,16,64,128,192,255,rng.randrange(256)))
        d=rng.choice((0,1,2,4,8,16,127,128,255,rng.randrange(256)))
        e=rng.randrange(256)
        car3a=rng.randrange(256)
        e623=rng.choice((0,0x50,0x80,0xFF,rng.randrange(256)))
        expected=independent(d,e,divider,e639,car3a,e623)
        observed=original_opcodes(master,xrom,d,e,divider,e639,car3a,e623)
        if expected!=observed:
            raise AssertionError(f"Original 22BA instruction-maths mismatch case {i}: {expected} != {observed}")
        paths[observed["path"]]+=1
        if observed["path"]=="computed":
            frac_paths["clamped" if observed["fraction"]==255 else "scaled"]+=1
    return {"source":"original 1991 arcade master bank4 22BA–2304",
            "cases":cases,"mismatches":0,"branch_cases":dict(paths),
            "fraction_cases":dict(frac_paths),"xrom_slot1_low_pairs_checked":65536,
            "scope":"bounded integer position-like metric only; full AI decisions/cars still OPEN"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("xrom",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    opts=parser.parse_args()
    print(json.dumps(verify(opts.master.read_bytes(),opts.xrom.read_bytes(),opts.cases),indent=2))
