#!/usr/bin/env python3
"""Original Indy Heat arcade B5AC..B5C8 payload/collision-side dispatcher.

E91B's high bit selects an IX/IY swap before response routine B5C9.
The low seven bits pass through A. B5C9 itself must be analysed separately.
Checks original bounded machine instructions, not inferred physics.
Private original arcade ROM data is never committed.
"""
from __future__ import annotations
import hashlib
import json
import argparse
from pathlib import Path

MASTER_HASH="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
START=0xB5AC
END=0xB5C9
STAGE_SHA="3552f451344d7dae946c15283eb955e738c63241f78c40d7f0ee7e008343261b"

def independent(value:int,ix:int,iy:int)->dict:
    if not 0<=value<=255:
        raise ValueError("Original contact byte must be 8-bit")
    if value&0x80:
        return {"arg":value&127,"handler_first":iy,"handler_second":ix,
                "entry":"B5C9","return_ix":ix,"return_iy":iy}
    return {"arg":value,"handler_first":ix,"handler_second":iy,
            "entry":"B5C9","return_ix":ix,"return_iy":iy}

def original(master:bytes,value:int,ix:int,iy:int)->dict:
    if len(master)!=0x90000 or not 0<=value<=255:
        raise ValueError("Original master ROM region and original contact byte required")
    pc=START
    a=0
    sign=False
    stack=[]
    callback=None
    for _ in range(30):
        op=master[pc]
        if op==0x3A:  # LD A,(E91B)
            if master[pc+1:pc+3]!=bytes.fromhex("1b e9"):
                raise ValueError("Unknown RAM input")
            a=value
            pc+=3
        elif op==0xB7:  # OR A
            sign=bool(a&128)
            pc+=1
        elif op==0xF2:  # JP P,B5C9
            target=int.from_bytes(master[pc+1:pc+3],"little")
            if target!=END:
                raise ValueError("Unexpected original jump")
            if not sign:
                return {"arg":a,"handler_first":ix,"handler_second":iy,
                        "entry":"B5C9","return_ix":ix,"return_iy":iy}
            pc+=3
        elif op==0xE6:  # AND 7F
            if master[pc+1]!=0x7F:
                raise ValueError("Wrong contact payload mask")
            a&=127
            pc+=2
        elif op in (0xDD,0xFD):
            ext=master[pc+1]
            if ext==0xE5:  # PUSH IX/IY
                stack.append(ix if op==0xDD else iy)
            elif ext==0xE1:  # POP IX/IY
                if not stack:raise ValueError("Unbalanced original pointer stack")
                if op==0xDD:ix=stack.pop()
                else:iy=stack.pop()
            else:raise ValueError("Unknown original pointer stack operation")
            pc+=2
        elif op==0xCD:  # CALL B5C9
            if master[pc+1:pc+3]!=bytes.fromhex("c9 b5"):
                raise ValueError("Unexpected contact response call")
            callback=(a,ix,iy)
            pc+=3
        elif op==0xC9:
            if stack or callback is None or pc!=END-1:
                raise ValueError("Unexpected original return state")
            return {"arg":callback[0],"handler_first":callback[1],
                    "handler_second":callback[2],"entry":"B5C9",
                    "return_ix":ix,"return_iy":iy}
        else:raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
    raise ValueError("Original contact dispatch instruction budget exceeded")

def verify(master:bytes)->dict:
    if hashlib.sha256(master).hexdigest()!=MASTER_HASH:
        raise ValueError("Private checksum-verified original arcade ROM required")
    digest=hashlib.sha256(master[START:END]).hexdigest()
    if digest!=STAGE_SHA:
        raise ValueError("Original contact dispatch opcode signature mismatch")
    n=0
    for value in range(256):
        for first,second in ((0xE080,0xE180),(0xE480,0xE580),(0xCAFE,0xBEEF)):
            got=original(master,value,first,second)
            expected=independent(value,first,second)
            if got!=expected:
                raise AssertionError(f"Original response dispatch mismatch {value:02X}")
            n+=1
    return {"instruction_window":"fixed Z80 B5AC..B5C8","sha256":digest,
            "cases":n,"mismatches":0,
            "incoming_arg":"E91B high bit chooses car swap; A passes lower seven bits to B5C9",
            "scope":"B5C9 response magnitude and physical effects remain unverified"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("master",type=Path)
    a=p.parse_args()
    print(json.dumps(verify(a.master.read_bytes()),indent=2))
