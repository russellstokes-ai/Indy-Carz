#!/usr/bin/env python3
"""Exact original arcade collision fallback state restoration BABB..BB6B.

Copies ten 16-bit previous positions over current positions, restores an
angular state word, conditionally reduces another 16-bit state word, and
sets bits 0,1,6 in car status. Its physical meaning and invocation timing
are not fully proven. Bounded original Z80 interpreter; no guessed physics.
"""
from __future__ import annotations
from pathlib import Path
from random import Random
import hashlib
import json
import argparse
from collections import Counter

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="0efa5d058d79150862699ceec57e29ad4fda40a0104005dab63f43543fc8091d"
START=0xBABB
END=0xBB6C

def word(mem:bytes|bytearray,idx:int)->int:
    return mem[idx]|mem[idx+1]<<8

def signed(value:int)->int:
    return value-65536 if value&0x8000 else value

def model(slot:bytes)->tuple[bytes,bool]:
    if len(slot)!=256:raise ValueError("Original car slot must contain 256 bytes")
    state=bytearray(slot)
    for i in range(10):
        state[2*i:2*i+2]=slot[0x1E+2*i:0x20+2*i]
    state[0x3C:0x3E]=slot[0x1C:0x1E]
    current=word(slot,0x40)
    h=current>>8
    damping=((h+128)&255)>=0xA0
    if damping:
        de=signed(current)>>3
        state[0x40:0x42]=((current-de)&65535).to_bytes(2,"little")
    state[0x7C]|=0x43
    return bytes(state),damping

def original(master:bytes,slot:bytes)->tuple[bytes,bool,int]:
    if len(master)!=0x90000 or len(slot)!=256:
        raise ValueError("Original Z80 executable / car slot size mismatch")
    state=bytearray(slot)
    pc=START
    a=d=e=h=l=0
    carry=False
    damped=False
    for step in range(200):
        op=master[pc]
        if op==0xDD:
            ext,disp=master[pc+1:pc+3]
            idx=(disp-0x80)&255
            if ext==0x66:h=state[idx]
            elif ext==0x6E:l=state[idx]
            elif ext==0x74:state[idx]=h
            elif ext==0x75:state[idx]=l
            elif ext==0x7E:a=state[idx]
            elif ext==0x77:state[idx]=a
            else:raise ValueError(f"Unknown original indexed opcode {ext:02X} at {pc:04X}")
            pc+=3
        elif op==0x7C:a=h;pc+=1
        elif op==0xC6:
            a=(a+master[pc+1])&255
            pc+=2
        elif op==0xFE:
            carry=a<master[pc+1];pc+=2
        elif op==0x38:
            delta=master[pc+1]
            delta=delta-256 if delta>=128 else delta
            pc+=2+(delta if carry else 0)
        elif op==0x54:d=h;pc+=1
        elif op==0x5D:e=l;pc+=1
        elif op==0xCB:
            nxt=master[pc+1]
            if nxt==0x2A: # SRA D
                carry=bool(d&1);d=(d>>1)|(d&128)
            elif nxt==0x1B: # RR E
                prior=e;e=(e>>1)|(int(carry)<<7);carry=bool(prior&1)
            else:raise ValueError(f"Unexpected shift instruction {nxt:02X} at {pc:04X}")
            pc+=2
        elif op==0xB7:
            carry=False;pc+=1
        elif op==0xED:
            if master[pc+1]!=0x52:raise ValueError("Unexpected ED opcode")
            raw=((h<<8)|l)-((d<<8)|e)-int(carry)
            carry=raw<0
            raw&=65535
            h,l=raw>>8,raw&255
            damped=True
            pc+=2
        elif op==0xF6:
            a|=master[pc+1]
            carry=False
            pc+=2
        elif op==0xC9:
            if pc!=END-1:raise ValueError("Unexpected original return")
            return bytes(state),damped,step+1
        else:
            raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
        if not START<=pc<END:
            raise ValueError(f"Original BABB branch escaped bounded stage {pc:04X}")
    raise ValueError("Original fallback instruction budget exceeded")

def verify(master:bytes,cases:int=18000)->dict:
    if hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Private checksum-verified original arcade master ROM required")
    digest=hashlib.sha256(master[START:END]).hexdigest()
    if digest!=STAGE_SHA:
        raise ValueError("Original fallback stage signature differs")
    if not 0<=cases<=100000:
        raise ValueError("Invalid case budget")
    rng=Random(0xBABB)
    counts=Counter()
    for i in range(cases):
        buf=bytearray(rng.randbytes(256))
        buf[0x41]=i%256 # all high-byte boundaries, positive and negative
        expected=model(bytes(buf))
        actual=original(master,bytes(buf))
        if actual[:2]!=expected:
            raise AssertionError(f"Original fallback record mismatch #{i}")
        counts["damped" if expected[1] else "unchanged_state_word"]+=1
    return {"source":"original 1991 arcade fixed master BABB..BB6B",
            "stage_sha256":digest,"cases":cases,"mismatches":0,"branches":dict(counts),
            "position_state":"copy ten 16-bit words from +1E..+30 to +00..+12",
            "angular_state":"copy word +1C to +3C",
            "conditional_high_word":"((high_byte(+40)+128)&255)>=160",
            "conditional_reduction":"word(+40)-arithmetic_signed_right_shift(word(+40),3)",
            "car_status":"slot+7C OR 0x43",
            "unknowns":"Physical meaning of +40, full damage/events, exact runtime timing and total arcade parity"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("master",type=Path)
    p.add_argument("--cases",type=int,default=18000)
    a=p.parse_args()
    print(json.dumps(verify(a.master.read_bytes(),a.cases),indent=2))
