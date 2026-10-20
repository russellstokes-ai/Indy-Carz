#!/usr/bin/env python3
"""Authentic Indy Heat 1991 AI pending-event generator, fixed 230B-2360.

Separately modelled integer thresholds and original Z80 instruction parity.
Field offsets are verified, but do not assign unproven pit/turbo semantics.
External pointer helper 1783 is independently verified elsewhere; its
linked IY+20 byte is a controlled input here, not a runtime observation.
No original copyrighted ROM, graphics, trackmaps or assembly is included.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from random import Random
import argparse,json

MASTER_HASH="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_HASH="3004d9af3f82f4071d953cd57dded3798946219021a3152c2857434556d2901b"
START,END=0x230B,0x2361
STATUS_31=0xB1
STATUS_32=0xB2
PEDAL_RESPONSE=0xD7
COMPARE_BYTE=0x3B
PENDING_EVENTS=0x77
LINK_GATE=0xFE

def independent(slot:bytes,linked_20:int)->tuple[str,bytes]:
    if len(slot)!=256 or not 0<=linked_20<256:
        raise ValueError("Expected original 256-byte car slot and linked-state byte")
    record=bytearray(slot)
    restricted=bool(record[STATUS_31]&16 or record[STATUS_32]&128)
    b,c=(0x18,0x09) if restricted else (0x50,0x32)
    if not restricted and record[PEDAL_RESPONSE]<0x44:
        b=0x80
        if record[PEDAL_RESPONSE]<0x3C:c=0x48
    observed=record[COMPARE_BYTE]
    if observed<b:
        if observed>=c:return "threshold_no_event",bytes(record)
        record[PENDING_EVENTS]|=2
        return "event_bit1",bytes(record)
    if (record[LINK_GATE]&16 and linked_20==2 and
            not(record[STATUS_31]&16) and not(record[STATUS_32]&128)):
        return "linked_gate_suppressed",bytes(record)
    record[PENDING_EVENTS]|=4
    return "event_bit2",bytes(record)

def opcode(master:bytes,slot:bytes,linked_20:int)->tuple[str,bytes]:
    if len(master)!=0x90000 or len(slot)!=256 or not 0<=linked_20<256:
        raise ValueError("Original master 0x90000, car 256 bytes, linked-state byte required")
    record=bytearray(slot)
    a=b=c=0;zero=carry=False;pc=START;iy_stack=[]
    for _ in range(64):
        op=master[pc]
        if op==0x06:b=master[pc+1];pc+=2
        elif op==0x0E:c=master[pc+1];pc+=2
        elif op==0xDD:
            ext=master[pc+1]
            if ext==0xCB:
                disp,code=master[pc+2:pc+4]
                if disp==0x31 and code==0x66:
                    zero=not bool(record[STATUS_31]&16)
                elif disp==0x32 and code==0x7E:
                    zero=not bool(record[STATUS_32]&128)
                elif disp==0x7E and code==0x66:
                    zero=not bool(record[LINK_GATE]&16)
                elif disp==0xF7 and code==0xCE:
                    record[PENDING_EVENTS]|=2
                elif disp==0xF7 and code==0xD6:
                    record[PENDING_EVENTS]|=4
                else:raise ValueError(f"Unexpected indexed bit opcode {code:02X} at {pc:04X}")
                pc+=4
            elif ext==0x7E:
                disp=master[pc+2]
                if disp==0x57:a=record[PEDAL_RESPONSE]
                elif disp==0xBB:a=record[COMPARE_BYTE]
                else:raise ValueError("Unexpected indexed source")
                pc+=3
            else:raise ValueError(f"Unknown original indexed opcode {ext:02X}")
        elif op in (0x20,0x28,0x30):
            displacement=master[pc+1]
            if displacement>=128:displacement-=256
            follow=(not zero if op==0x20 else zero if op==0x28 else not carry)
            pc+=2+(displacement if follow else 0)
        elif op==0xFE:
            n=master[pc+1];carry=a<n;zero=a==n;pc+=2
        elif op==0xB8:carry=a<b;zero=a==b;pc+=1
        elif op==0xB9:carry=a<c;zero=a==c;pc+=1
        elif op==0xFD:
            ext=master[pc+1]
            if ext==0xE5:iy_stack.append(1);pc+=2
            elif ext==0xE1:
                if not iy_stack:raise ValueError("Original IY pop underflow")
                iy_stack.pop();pc+=2
            elif ext==0x7E:
                if master[pc+2]!=0x20:raise ValueError("Unknown original linked-state source")
                a=linked_20;pc+=3
            else:raise ValueError(f"Unexpected IY opcode {ext:02X}")
        elif op==0xCD:
            target=master[pc+1]|(master[pc+2]<<8)
            if target!=0x1783 or len(iy_stack)!=1:
                raise ValueError("Unexpected original linked-state helper")
            pc+=3
        elif op==0xD0: # RET NC at 2335 only
            if pc!=0x2335:raise ValueError("Original RET NC outside verified site")
            if not carry:
                if iy_stack:raise ValueError("Original early return with live IY save")
                return "threshold_no_event",bytes(record)
            pc+=1
        elif op==0xC9:
            if iy_stack:raise ValueError("Original RET with IY saved")
            if pc not in (0x233A,0x235B,0x2360):
                raise ValueError(f"Unknown original return {pc:04X}")
            return ("event_bit1" if pc==0x233A else
                    "linked_gate_suppressed" if pc==0x235B else "event_bit2"),bytes(record)
        else:raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")
        if not START<=pc<END:raise ValueError("Original AI stage escaped its verified bounds")
    raise ValueError("Original instruction budget exceeded")

def verify(master:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_HASH:
        raise ValueError("Private checksum-verified original master required")
    if sha256(master[START:END]).hexdigest()!=STAGE_HASH:
        raise ValueError("Original 230B-2360 opcode fingerprint differs")
    if not 0<=cases<=250000:raise ValueError("Invalid bounded case budget")
    rng=Random(0x230B);hist={}
    for i in range(cases):
        record=bytearray(rng.randbytes(256))
        record[STATUS_31]=(record[STATUS_31]&~16)|(16 if i&1 else 0)
        record[STATUS_32]=(record[STATUS_32]&~128)|(128 if i&2 else 0)
        record[LINK_GATE]=(record[LINK_GATE]&~16)|(16 if i&4 else 0)
        record[PEDAL_RESPONSE]=rng.choice((0,0x3B,0x3C,0x43,0x44,0x7E,255,rng.randrange(256)))
        record[COMPARE_BYTE]=rng.choice((0,8,9,23,24,49,50,71,72,79,80,127,128,255,rng.randrange(256)))
        linked=2 if i%3==0 else rng.randrange(256)
        model=independent(bytes(record),linked)
        original=opcode(master,bytes(record),linked)
        if model!=original:
            raise AssertionError(f"Original AI pending-event mismatch case {i}: {model[0]} vs {original[0]}")
        hist[original[0]]=hist.get(original[0],0)+1
    return {"source":"Original 1991 arcade fixed master 230B-2360",
            "source_sha256":STAGE_HASH,"cases":cases,"mismatches":0,
            "event_or_skip_branch_cases":hist,
            "limit":"Verified original bit1/bit2 pending-event branch, not full AI strategy"}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    args=parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.cases),indent=2))
