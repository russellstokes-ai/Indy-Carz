#!/usr/bin/env python3
"""Original Indy Heat 1991 master Z80 7225-7244 signed motion sign gate.

Reconstruct original 16-bit motion-state update and sign-crossing clamp.
Verify an independent 16-bit integer model by interpreting original
Z80 instruction bytes from an authenticated PRIVATE rev1 master ROM.
No original program bytes, track art or soundtrack are distributed.
This is a bounded driving subroutine, not the entire acceleration/grip engine.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="50b80e7b8e2dc40be44f80205f465e9b15450092e42ffff3db9714b0d6fe529f"
START,STOP=0x7225,0x7245


def independent(old_word:int,delta_de:int)->dict:
    if any(not isinstance(v,int) or not 0<=v<65536 for v in (old_word,delta_de)):
        raise ValueError("Original Z80 motion and signed change must be 16-bit words")
    difference=(old_word-delta_de)&65535
    sign_same=bool(old_word&0x8000)==bool(difference&0x8000)
    output=difference if sign_same else 0
    branch=("negative" if old_word&0x8000 else "positive") + (
        "_keep" if sign_same else "_clamp")
    return {"stored_e76b":output,"de_after":output,
            "hl_after":delta_de,"branch":branch,"next_pc":STOP}


def original_opcodes(master:bytes,old_word:int,delta_de:int)->dict:
    """Execute exact original master instruction forms through EX DE,HL.

    Both signed cases explicitly OR A to clear carry before SBC HL,DE.
    Branch decision is original JP M/P on the wrapped 16-bit sign flag,
    NOT a normal signed comparison on unlimited host integers.
    """
    independent(old_word,delta_de)
    if len(master)!=0x90000:raise ValueError("Authentic private arcade master length required")
    pc=START
    h=l=0
    d,e=delta_de>>8,delta_de&255
    a=0
    carry=False;zero=False;sign=False
    output=old_word
    for _ in range(25):
        op=master[pc]
        if op==0x2A: # LD HL,(E76B)
            if master[pc+1:pc+3]!=bytes.fromhex("6b e7"):
                raise ValueError("Unexpected original motion input location")
            h,l=old_word>>8,old_word&255;pc+=3
        elif op==0xCB: # BIT7,H
            if master[pc+1]!=0x7C:raise ValueError("Unexpected original BIT")
            zero=not bool(h&128);pc+=2
        elif op==0xCA: # JP Z,7238
            target=master[pc+1]|(master[pc+2]<<8)
            if target!=0x7238:raise ValueError("Unexpected original sign branch")
            pc=target if zero else pc+3
        elif op==0xB7: # OR A clears carry
            carry=False;pc+=1
        elif op==0xED: # SBC HL,DE
            if master[pc+1]!=0x52:raise ValueError("Unexpected original 16-bit arithmetic")
            full=((h<<8)|l)-((d<<8)|e)-int(carry)
            carry=full<0
            value=full&65535
            h,l=value>>8,value&255
            sign=bool(value&32768)
            zero=value==0
            pc+=2
        elif op in (0xF2,0xFA): # JP P or JP M
            target=master[pc+1]|(master[pc+2]<<8)
            if target!=0x7241:raise ValueError("Unexpected original clamp branch")
            pc=target if (not sign if op==0xF2 else sign) else pc+3
        elif op==0x21:
            if master[pc+1:pc+3]!=bytes.fromhex("00 00"):
                raise ValueError("Unexpected original clamp destination")
            h=l=0;pc+=3
        elif op==0x18:
            displacement=master[pc+1]
            if displacement>=128:displacement-=256
            pc+=2+displacement
        elif op==0x22:
            if master[pc+1:pc+3]!=bytes.fromhex("6b e7"):
                raise ValueError("Original motion store changed")
            output=(h<<8)|l;pc+=3
        elif op==0xEB:
            h,l,d,e=d,e,h,l
            pc+=1
        else:raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")

        if pc==STOP:
            candidate=(old_word-delta_de)&65535
            same=bool(old_word&32768)==bool(candidate&32768)
            branch=("negative" if old_word&32768 else "positive") + (
                "_keep" if same else "_clamp")
            return {"stored_e76b":output,"de_after":(d<<8)|e,
                    "hl_after":(h<<8)|l,"branch":branch,"next_pc":pc}
        if not START<=pc<STOP:
            raise ValueError("Original motion gate escaped checksum-verified region")
    raise ValueError("Original Z80 motion gate instruction budget exceeded")


def verify(master:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated private original 1991 master required")
    if sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original motion stage machine-code checksum changed")
    if not 0<=cases<=250000:raise ValueError("Invalid original verification budget")
    rng=Random(0x7225);branches=Counter()
    for i in range(cases):
        old=rng.choice((0,1,2,0x7FFF,0x8000,0xFFFF,rng.randrange(65536)))
        delta=rng.choice((0,1,2,0x7FFF,0x8000,0xFFFF,rng.randrange(65536)))
        if i%6==0:delta=(old+1)&65535
        if i%6==1:delta=(old-1)&65535
        if i%6==2:delta=old
        model=independent(old,delta)
        observed=original_opcodes(master,old,delta)
        if model!=observed:
            raise AssertionError(f"Original 7225 motion gate mismatch case {i}: {model}!={observed}")
        branches[observed["branch"]]+=1
    return {"source":"Original 1991 arcade master Z80 7225-7244",
            "source_sha256":STAGE_SHA,"cases":cases,"mismatches":0,
            "original_exits":dict(sorted(branches.items())),
            "limit":"Exact 16-bit sign-crossing gate only; DE production, acceleration and terrain still incomplete"}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_master",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    args=p.parse_args()
    print(json.dumps(verify(args.original_master.read_bytes(),args.cases),indent=2))
