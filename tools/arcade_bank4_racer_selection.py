#!/usr/bin/env python3
"""Original Indy Heat 1991 bank-4 20A8–213E racer-pointer selection.

The real master fixed 1190 performs two original far calls through wrapper
14C1: first bank4 20A8, then bank4 2000. Only the FIRST called routine's
entry/selection is reconstructed here, ending immediately before CALL 22BA.

Input five slot ordinals represent original values 0..4, not arbitrary
256-byte ordinals. Unverified 22BA/2000 effects, AI driving and actual
in-game race outcomes are not replaced with speculative logic.
All original ROM data stays PRIVATE.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
FARCALL_SHA = "c0bc62b47329effa72159a7d0fca5172856ef11649a59b84ad3d03ad1d1c60d7"
STAGE_SHA = "1e8ce09817dd2f71c1006670b9f7d389f84220ebb36dee7f0e6d4ab326535899"
START, STOP = 0x20A8, 0x213F
BANK4_BASE = 0x30000
CAR_POINTERS = (0xE080, 0xE180, 0xE280, 0xE380, 0xE480)


def _validate(e603:int,e677:int,e67d:int,e602:int,e63e:int,e674:int,
              status_7e:tuple[int,...],status_31:tuple[int,...],
              ordinals:tuple[int,...])->None:
    if (any(not 0<=n<256 for n in (e603,e677,e67d,e602,e63e,e674))
        or len(status_7e)!=5 or len(status_31)!=5 or len(ordinals)!=5
        or any(not 0<=n<256 for n in status_7e+status_31)
        or sorted(ordinals)!=[0,1,2,3,4]):
        raise ValueError("Six original global bytes, five car status pairs and original 0..4 ordinals required")


def independent(e603:int,e677:int,e67d:int,e602:int,e63e:int,e674:int,
                status_7e:tuple[int,...],status_31:tuple[int,...],
                ordinals:tuple[int,...])->dict:
    """Original global early returns, eligible car scan and JP M, not carry."""
    _validate(e603,e677,e67d,e602,e63e,e674,status_7e,status_31,ordinals)
    if e603: return {"exit":"ret_20AC","a":e603}
    if e677: return {"exit":"ret_20B2","a":e677}
    if e67d: return {"exit":"ret_20B7","a":e67d}

    if e602:
        iy = next((i for i in range(4,-1,-1) if status_7e[i]&64),0)
        b = ordinals[iy]
    else:
        # This original B=FF case is modelled with original car ordinals
        # 0..4, for which CP (IX+69) is always sign-negative.
        iy,b = 0,255

    a=e63e
    ix=0
    for i in range(4):
        ix=i
        if not status_31[i]&1:
            a=(a-1)&255
            if a&128:break
        ix=i+1

    # Original CP followed by JP M selects from sign flag of 8-bit
    # subtraction. It is *not* a carry comparison.
    swapped = not bool((b-ordinals[ix])&128)
    if swapped:
        ix=iy
        c=4
    else:
        c=e674
    return {"exit":"continue_213F","ix":ix,"iy":iy,
            "a":b,"b":b,"c":c,"swapped":swapped}


def original_opcodes(master:bytes,e603:int,e677:int,e67d:int,e602:int,
                     e63e:int,e674:int,status_7e:tuple[int,...],
                     status_31:tuple[int,...],ordinals:tuple[int,...])->dict:
    """Boundedly execute authentic bank4 Z80 instruction bytes until 213F."""
    _validate(e603,e677,e67d,e602,e63e,e674,status_7e,status_31,ordinals)
    if len(master)!=0x90000:raise ValueError("Authentic original master length required")
    memory=bytearray(master[:0xE000])
    memory[0x2000:0xA000]=master[BANK4_BASE:BANK4_BASE+0x8000]
    ix=iy=0;a=b=c=0;zero=sign=False;pc=START;stack=[];swapped=False
    ram={0xE603:e603,0xE677:e677,0xE67D:e67d,
         0xE602:e602,0xE63E:e63e,0xE674:e674}
    for i,p in enumerate(CAR_POINTERS):
        addr=0xE62C+i*2
        ram[addr],ram[addr+1]=p&255,p>>8
        ram[p+0x7E],ram[p+0x31],ram[p+0x69]=status_7e[i],status_31[i],ordinals[i]

    def read(addr:int)->int:
        if addr not in ram:
            raise ValueError(f"Unexpected original bank4 RAM read at {addr:04X}")
        return ram[addr]

    for _ in range(95):
        op=memory[pc]
        if op==0x3A:           # LD A,(nn)
            addr=memory[pc+1]|memory[pc+2]<<8
            if addr not in (0xE603,0xE677,0xE67D,0xE602,0xE63E,0xE674):
                raise ValueError("Unexpected original global read")
            a=read(addr);pc+=3
        elif op==0xB7:         # OR A
            zero=a==0;sign=bool(a&128);pc+=1
        elif op==0xC0:         # RET NZ
            if not zero:return {"exit":f"ret_{pc:04X}","a":a}
            pc+=1
        elif op==0xFE:         # CP immediate
            val=memory[pc+1]
            diff=(a-val)&255
            zero=diff==0;sign=bool(diff&128);pc+=2
        elif op==0x06:b=memory[pc+1];pc+=2
        elif op in (0x28,0x20): # JR Z,JR NZ
            off=memory[pc+1]
            if off>=128:off-=256
            pc+=2+(off if (zero if op==0x28 else not zero) else 0)
        elif op==0xFD:
            ext=memory[pc+1]
            if ext==0x2A:       # LD IY,(pointer)
                addr=memory[pc+2]|memory[pc+3]<<8
                if addr not in (0xE62C,0xE62E,0xE630,0xE632,0xE634):
                    raise ValueError("Unexpected original IY pointer source")
                ptr=read(addr)|read(addr+1)<<8
                if ptr not in CAR_POINTERS:raise ValueError("Original IY pointer unknown")
                iy=CAR_POINTERS.index(ptr);pc+=4
            elif ext==0xCB:      # BIT6,(IY+7E)
                if memory[pc+2:pc+4]!=bytes.fromhex("7e76"):
                    raise ValueError("Unexpected original IY status BIT")
                zero=not bool(read(CAR_POINTERS[iy]+0x7E)&64);pc+=4
            elif ext==0x46:      # LD B,(IY+69)
                if memory[pc+2]!=0x69:raise ValueError("Unexpected ordinal offset")
                b=read(CAR_POINTERS[iy]+0x69);pc+=3
            elif ext==0xE5:      # PUSH IY
                stack.append(iy);pc+=2
            else:raise ValueError(f"Unexpected original FD opcode at {pc:04X}")
        elif op==0xDD:
            ext=memory[pc+1]
            if ext==0x2A:       # LD IX,(pointer)
                addr=memory[pc+2]|memory[pc+3]<<8
                if addr not in (0xE62C,0xE62E,0xE630,0xE632,0xE634):
                    raise ValueError("Unexpected original IX pointer source")
                ptr=read(addr)|read(addr+1)<<8
                if ptr not in CAR_POINTERS:raise ValueError("Original IX pointer unknown")
                ix=CAR_POINTERS.index(ptr);pc+=4
            elif ext==0xCB:     # BIT0,(IX+31)
                if memory[pc+2:pc+4]!=bytes.fromhex("3146"):
                    raise ValueError("Unexpected original IX status BIT")
                zero=not bool(read(CAR_POINTERS[ix]+0x31)&1);pc+=4
            elif ext==0xBE:     # CP (IX+69)
                if memory[pc+2]!=0x69:raise ValueError("Unexpected ordinal compare")
                diff=(a-read(CAR_POINTERS[ix]+0x69))&255
                zero=diff==0;sign=bool(diff&128);pc+=3
            elif ext==0xE1:     # POP IX from prior PUSH IY
                if not stack:raise ValueError("Original IX pointer stack underflow")
                ix=stack.pop();swapped=True;pc+=2
            else:raise ValueError(f"Unexpected original DD opcode {ext:02X} at {pc:04X}")
        elif op==0x3D:         # DEC A, signed sign flag matters
            a=(a-1)&255;zero=a==0;sign=bool(a&128);pc+=1
        elif op==0xFA:         # JP M,nn
            dest=memory[pc+1]|memory[pc+2]<<8
            if dest not in (0x212E,0x213F):raise ValueError("Unexpected original JP M target")
            pc=dest if sign else pc+3
        elif op==0x4F:c=a;pc+=1
        elif op==0x78:a=b;pc+=1
        elif op==0x0E:c=memory[pc+1];pc+=2
        else:raise ValueError(f"Unexpected original bank4 opcode {op:02X} at {pc:04X}")

        if pc==STOP:
            if stack:raise ValueError("Original IY/IX pointer stack not balanced")
            return {"exit":"continue_213F","ix":ix,"iy":iy,
                    "a":a,"b":b,"c":c,"swapped":swapped}
        if not START<=pc<STOP:
            raise ValueError("Original bank4 selector escaped verified routine")
    raise ValueError("Original bank4 selector instruction budget exceeded")


def verify(master:bytes,cases:int=50000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated original 1991 arcade master required")
    if sha256(master[0x1190:0x119A]).hexdigest()!=FARCALL_SHA:
        raise ValueError("Original dual far-call wrapper sequence changed")
    # CALL bank4 trampoline, first inline target 20A8; second inline target 2000.
    if (master[0x1190:0x1193]!=master[0x1195:0x1198]
        or int.from_bytes(master[0x1193:0x1195],"little")!=0x20A8
        or int.from_bytes(master[0x1198:0x119A],"little")!=0x2000):
        raise ValueError("Original fixed two bank4 CALL destinations changed")
    bank4=master[BANK4_BASE:BANK4_BASE+0x8000]
    if sha256(bank4[START-0x2000:STOP-0x2000]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original bank4 selection opcode signature changed")
    if not 0<=cases<=250000:raise ValueError("Invalid original-code test budget")
    rng=Random(0x20A8);counts=Counter()
    for i in range(cases):
        e603=0 if i%17 else rng.randrange(1,256)
        e677=0 if i%19 else rng.randrange(1,256)
        e67d=0 if i%23 else rng.randrange(1,256)
        e602=0 if i%3==0 else 1+rng.randrange(255)
        e63e=rng.choice((0,1,2,3,4,5,127,128,255,rng.randrange(256)))
        e674=rng.randrange(256)
        ready=tuple(rng.randrange(256) for _ in range(5))
        status=tuple(rng.randrange(256) for _ in range(5))
        ordinal=tuple(rng.sample(range(5),5))
        args=(e603,e677,e67d,e602,e63e,e674,ready,status,ordinal)
        expected=independent(*args)
        observed=original_opcodes(master,*args)
        if expected!=observed:
            raise AssertionError(f"Original bank4 selection mismatch case {i}")
        counts[observed["exit"]]+=1
    return {"source":"authentic master fixed 1190 and bank4 20A8–213E",
            "cases":cases,"mismatches":0,"branch_counts":dict(counts),
            "constraints":"original 0..4 slot ordinals and five indexed racing records",
            "not_yet_recovered":"CALL 22BA, second far-called bank4 2000 and downstream AI/race effects"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("--cases",type=int,default=50000)
    args=parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.cases),indent=2))
