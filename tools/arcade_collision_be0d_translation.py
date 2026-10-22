#!/usr/bin/env python3
"""Original arcade master Z80 BE0D-BE67: exact two-axis collision translation.

Independent byte/word state model versus execution of actual authentic 1991
Indy Heat master Z80 instructions from a PRIVATE SHA-256-checked ROM.
The original game computes two wrapped position deltas, applies each delta
to four related shared geometry/position words, then jumps to original
BCA5 collision retry. No original ROM, art, track or instruction dump is
distributed. This bounded stage is NOT an entire collision force model.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="34dc15f002f171e4ded0ab435abfbbb1f9e13ea590da366802c8fa142c9a2da9"
START,STOP=0xBE0D,0xBE68
RAM_BASE,RAM_LENGTH=0xE000,0x2000
RETRY_PC=0xBCA5
X_AFFECTED=(0xE72D,0xE72F,0xE733,0xE72B)
Y_AFFECTED=(0xE737,0xE739,0xE73D,0xE735)

def _check(ram:bytes)->None:
    if len(ram)!=RAM_LENGTH:raise ValueError("Original E000-FFFF master RAM must be 8192 bytes")

def read16(ram:bytes,address:int)->int:
    if not RAM_BASE<=address<RAM_BASE+RAM_LENGTH-1:
        raise ValueError("Outside original 16-bit CPU RAM address range")
    at=address-RAM_BASE
    return ram[at]|(ram[at+1]<<8)

def write16(ram:bytearray,address:int,value:int)->None:
    if not RAM_BASE<=address<RAM_BASE+RAM_LENGTH-1:
        raise ValueError("Outside original 16-bit CPU RAM destination range")
    at=address-RAM_BASE
    ram[at],ram[at+1]=value&255,(value>>8)&255

def independent(ram:bytes)->dict:
    """Returns a NEW complete byte buffer, preserving unrelated original RAM."""
    _check(ram)
    state=bytearray(ram)
    previous_x=read16(state,0xE731)
    target_x=read16(state,0xE98D)
    delta_x=(target_x-previous_x)&0xFFFF
    write16(state,0xE731,target_x)
    if delta_x:
        for address in X_AFFECTED:
            write16(state,address,(read16(state,address)+delta_x)&0xFFFF)
    previous_y=read16(state,0xE73B)
    target_y=read16(state,0xE98F)
    delta_y=(target_y-previous_y)&0xFFFF
    write16(state,0xE73B,target_y)
    if delta_y:
        for address in Y_AFFECTED:
            write16(state,address,(read16(state,address)+delta_y)&0xFFFF)
    return {"ram":bytes(state),"delta_x":delta_x,"delta_y":delta_y,
            "x_branch":delta_x!=0,"y_branch":delta_y!=0,
            "next_pc":RETRY_PC}

def original_opcodes(master:bytes,ram:bytes)->dict:
    """Interpret actual 91 original Z80 instruction bytes; reject escape.

    No external calls or unknown instructions are permitted. The interpreter
    tracks the signed/zero flags of SBC HL,DE, original JR Z, EX DE,HL
    and wrapped 16-bit ADD HL,DE per the actual memory writes.
    """
    _check(ram)
    if len(master)!=0x90000:raise ValueError("Original master ROM size wrong")
    state=bytearray(ram)
    pc=START
    h=l=d=e=0
    carry=zero=False
    dx=dy=None
    steps=0
    while steps<45:
        steps+=1
        op=master[pc]
        if op==0x2A:  # LD HL,(nn)
            address=master[pc+1]|(master[pc+2]<<8)
            if address not in (0xE98D,0xE98F,*X_AFFECTED,*Y_AFFECTED):
                raise ValueError(f"Unknown original source {address:04X}")
            value=read16(state,address)
            h,l=value>>8,value&255
            pc+=3
        elif op==0xED:
            ext=master[pc+1]
            if ext==0x5B:  # LD DE,(nn)
                address=master[pc+2]|(master[pc+3]<<8)
                if address not in (0xE731,0xE73B):
                    raise ValueError("Unexpected original geometry-delta reference")
                value=read16(state,address)
                d,e=value>>8,value&255
                pc+=4
            elif ext==0x52:  # SBC HL,DE
                before=((h<<8)|l)-((d<<8)|e)-int(carry)
                carry=before<0
                value=before&0xFFFF
                h,l=value>>8,value&255
                zero=value==0
                if pc==0xBE18:dx=value
                elif pc==0xBE44:dy=value
                else:raise ValueError("Unexpected original subtraction site")
                pc+=2
            else:raise ValueError(f"Unknown original ED opcode {ext:02X}")
        elif op==0x22: # LD (nn),HL
            address=master[pc+1]|(master[pc+2]<<8)
            if address not in (0xE731,0xE73B,*X_AFFECTED,*Y_AFFECTED):
                raise ValueError("Unknown original destination")
            write16(state,address,(h<<8)|l)
            pc+=3
        elif op==0xB7: # OR A clears carry
            carry=False
            pc+=1
        elif op==0x28: # JR Z
            displacement=master[pc+1]
            if displacement>=128:displacement-=256
            pc+=2+(displacement if zero else 0)
        elif op==0xEB: # EX DE,HL
            h,l,d,e=d,e,h,l
            pc+=1
        elif op==0x19: # ADD HL,DE
            total=((h<<8)|l)+((d<<8)|e)
            carry=total>65535
            value=total&65535
            h,l=value>>8,value&255
            pc+=1
        elif op==0xC3: # original JP BCA5
            address=master[pc+1]|(master[pc+2]<<8)
            if pc!=0xBE65 or address!=RETRY_PC or dx is None or dy is None:
                raise ValueError("Unexpected original collision exit")
            return {"ram":bytes(state),"delta_x":dx,"delta_y":dy,
                    "x_branch":dx!=0,"y_branch":dy!=0,"next_pc":address}
        else:raise ValueError(f"Unexpected Z80 opcode {op:02X} at {pc:04X}")
        if not START<=pc<STOP:
            raise ValueError("Original collision translation escaped bounded stage")
    raise ValueError("Original translation exceeded instruction budget")

def verify(master:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Private checksum-verified original 1991 master ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original BE0D-BE67 ROM instruction fingerprint changed")
    if not 0<=cases<=200000:raise ValueError("Invalid bounded case budget")
    rng=Random(0xBE0D)
    branches=Counter()
    for i in range(cases):
        state=bytearray(rng.randbytes(RAM_LENGTH))
        old_x,old_y=read16(state,0xE731),read16(state,0xE73B)
        dx=0 if i%4 in (0,1) else rng.choice((1,65535,0x8000,rng.randrange(65536)))
        dy=0 if i%4 in (0,2) else rng.choice((1,65535,0x8000,rng.randrange(65536)))
        write16(state,0xE98D,(old_x+dx)&0xFFFF)
        write16(state,0xE98F,(old_y+dy)&0xFFFF)
        expected=independent(bytes(state))
        actual=original_opcodes(master,bytes(state))
        if expected!=actual:
            incorrect=next(k for k in expected if expected[k]!=actual.get(k))
            raise AssertionError(f"Original BE0D translation mismatch case {i}: {incorrect}")
        branches[f"x={int(actual['x_branch'])},y={int(actual['y_branch'])}"]+=1
    return {"source":"Original 1991 arcade master fixed BE0D-BE67",
            "original_stage_sha256":STAGE_SHA,"opcode_cases":cases,
            "mismatches":0,"original_exit_pc":f"{RETRY_PC:04X}",
            "original_x_translation_words":len(X_AFFECTED),
            "original_y_translation_words":len(Y_AFFECTED),
            "branches":dict(sorted(branches.items())),
            "limitations":"Exact collision geometry translation to retry; BCFA forces, wall surface and damage still incomplete"}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_master",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    opts=parser.parse_args()
    print(json.dumps(verify(opts.original_master.read_bytes(),opts.cases),indent=2))
