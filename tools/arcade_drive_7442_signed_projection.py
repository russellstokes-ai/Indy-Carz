#!/usr/bin/env python3
"""Authentic 1991 Indy Heat arcade master Z80 7442–7462 steering projection.

Executes the original signed two-stage X-ROM math versus an independent
integer model with original 16-bit wrapping. The preceding 73F6 stage
delivers A=32..127 with H from IX+79. The 73CD stage has saved its
8-bit weighted steering byte on the original AF stack (restored at 7449).
The car IX+31 bit0 bypasses the limiter at 7463 and jumps to 748A.

No private ROM, sound, program listings or proprietary tables distributed.
This is not a full physics update: downstream 7463+ is separate.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from random import Random
from collections import Counter

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA="3fe322be85b52c2b9798fd836b7f1b200e3356bad34b774214f226643a913f30"
START,STOP,SKIP=0x7442,0x7463,0x748A

def signed8(v:int)->int:return v-256 if v>=128 else v

def product_word(a:int,b:int)->int:
    if not 0<=a<256 or not 0<=b<256:
        raise ValueError("Original signed X-ROM operands must be bytes")
    return max(-32768,min(32767,2*signed8(a)*signed8(b)))&65535

def _validate(control:int,car79:int,weighted:int,car_b1:int)->None:
    if not 32<=control<=127 or any(not 0<=v<256 for v in (car79,weighted,car_b1)):
        raise ValueError("Original control A=32..127 and IX+79/weighted/IX+31 bytes required")

def independent(control:int,car79:int,weighted:int,car_b1:int)->dict:
    _validate(control,car79,weighted,car_b1)
    first=product_word(car79,control)
    high=first>>8
    weighted_low=weighted
    if weighted&128:
        high=(high<<1)&255
        weighted_low=weighted>>1
    second=product_word(high,weighted_low)
    # SRA H; RR L is a signed 16-bit arithmetic shift with the
    # carry from H's low bit crossing to L's high bit.
    result=(signed8(second>>8)*256+(second&255))>>1
    next_pc=SKIP if car_b1&1 else STOP
    return {
        "correction":result&65535,
        "next_pc":next_pc,
        "skip_velocity_limiter":bool(car_b1&1),
        "first_xrom_address":(car79<<8)|control,
        "second_xrom_address":(high<<8)|weighted_low,
    }

def original_opcodes(master:bytes,xrom:bytes,control:int,car79:int,
                     weighted:int,car_b1:int)->dict:
    """Actual original Z80 instructions; strict 7442–7462 allowlist."""
    _validate(control,car79,weighted,car_b1)
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Private original master/X-ROM sizes required")
    a,h,l=control,car79,0
    carry=zero=sign=False
    pc=START;xr=0;addresses=[]
    for _ in range(42):
        op=master[pc]
        if op==0x6F:l=a;pc+=1
        elif op==0x22:
            if master[pc+1:pc+3]!=b"\xfc\xff":
                raise ValueError("Unknown original X-ROM latch")
            xr=(h<<8)|l;addresses.append(xr);pc+=3
        elif op==0x2A:
            if master[pc+1:pc+3]!=b"\xfc\xff":
                raise ValueError("Unknown original X-ROM read")
            h,l=xrom[2*xr+1],xrom[2*xr];pc+=3
        elif op==0xF1: # Original POP AF restores signed weighted input
            a=weighted;pc+=1
        elif op==0xB7:
            sign=bool(a&128);carry=False;zero=a==0;pc+=1
        elif op==0xF2:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0x7452:raise ValueError("Unknown original JP P target")
            pc=target if not sign else pc+3
        elif op==0xCB:
            ext=master[pc+1]
            if ext==0x3F:
                carry=bool(a&1);a>>=1;zero=a==0;sign=False
            elif ext==0x24:
                carry=bool(h&128);h=(h<<1)&255;zero=h==0;sign=bool(h&128)
            elif ext==0x2C:
                carry=bool(h&1);h=(h>>1)|(h&128);sign=bool(h&128)
            elif ext==0x1D:
                prev=l;l=(l>>1)|(int(carry)<<7);carry=bool(prev&1)
            else:raise ValueError("Unexpected original CB opcode")
            pc+=2
        elif op==0xDD:
            if master[pc+1:pc+4]!=bytes.fromhex("cb3146"):
                raise ValueError("Unexpected original indexed BIT")
            zero=not bool(car_b1&1);pc+=4
        elif op==0x20:
            displacement=master[pc+1]
            if displacement>=128:displacement-=256
            pc+=2+(displacement if not zero else 0)
        else:raise ValueError(f"Unknown original opcode {op:02X} at {pc:04X}")
        if pc in (STOP,SKIP):
            if len(addresses)!=2:
                raise ValueError("Original two-X-ROM stage incomplete")
            return {
                "correction":h<<8|l,
                "next_pc":pc,
                "skip_velocity_limiter":pc==SKIP,
                "first_xrom_address":addresses[0],
                "second_xrom_address":addresses[1],
            }
        if not START<=pc<STOP:
            raise ValueError(f"Original steering escaped bounded stage at {pc:04X}")
    raise ValueError("Original 7442 instruction budget exceeded")

def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authentic original private master required")
    if len(xrom)!=0x40000 or hashlib.sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Authentic original private signed X-ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original 7442 source opcode fingerprint changed")
    if not 0<=cases<=300000:
        raise ValueError("Invalid original stage test budget")
    rng=Random(0x7442);hist=Counter()
    for i in range(cases):
        control=rng.choice((32,64,127,rng.randrange(32,128)))
        car79=rng.randrange(256)
        weighted=rng.randrange(256)
        b1=rng.randrange(256)
        inputs=(control,car79,weighted,b1)
        model=independent(*inputs)
        actual=original_opcodes(master,xrom,*inputs)
        if model!=actual:
            raise AssertionError(f"Original 7442 signed X-ROM steering mismatch {i}")
        hist["skip_limiter" if b1&1 else "run_limiter"]+=1
    return {"source":"Original Indy Heat rev1 master Z80 7442–7462",
            "cases":cases,"mismatches":0,
            "original_xrom_lookups_per_case":2,
            "exits":dict(sorted(hist.items())),
            "limits":"Only first signed projection and original BIT0 branch; 7463+ limiter separate"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_master",type=Path)
    p.add_argument("private_xrom",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    opts=p.parse_args()
    print(json.dumps(verify(opts.private_master.read_bytes(),
                            opts.private_xrom.read_bytes(),opts.cases),indent=2))
