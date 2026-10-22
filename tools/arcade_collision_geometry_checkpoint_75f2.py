#!/usr/bin/env python3
"""Original 1991 arcade Z80 75F2-7634 eleven-word geometry checkpoint.

The save order below is the genuine original opcode order, distinct from
the later C468 collision rollback order. Authentic ROM stays PRIVATE.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from random import Random
MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="842c80299b22563023fc4d5879ce2831546683915b0a0ffd76f02d4c4bebb460"
START,RET=0x75F2,0x7634
PAIRS=((0xE72B,0xE749),(0xE735,0xE753),
       (0xE72D,0xE74B),(0xE737,0xE755),
       (0xE72F,0xE74D),(0xE739,0xE757),
       (0xE731,0xE74F),(0xE73B,0xE759),
       (0xE733,0xE751),(0xE73D,0xE75B),
       (0xE767,0xE747))
def word(buf,addr):
    if not 0xE000<=addr<0xFFFE:raise ValueError("Invalid original word")
    i=addr-0xE000
    return buf[i]|buf[i+1]<<8
def put(buf,addr,value):
    if not 0xE000<=addr<0xFFFE:raise ValueError("Invalid destination")
    i=addr-0xE000
    buf[i],buf[i+1]=value&255,value>>8
def independent(ram):
    if len(ram)!=8192:raise ValueError("Original 8192-byte master RAM required")
    out=bytearray(ram);writes=[]
    for src,dst in PAIRS:
        value=word(out,src);put(out,dst,value);writes.append((dst,value))
    return {"ram":bytes(out),"writes":writes,"return_pc":RET}
def original_opcodes(master,ram):
    if len(master)!=0x90000 or len(ram)!=8192:raise ValueError("Original RAM/ROM required")
    state=bytearray(ram);pc=START;hl=0;writes=[]
    for _ in range(24):
        op=master[pc]
        if op==0x2A:
            address=master[pc+1]|master[pc+2]<<8
            if address not in (a for a,b in PAIRS):raise ValueError("Unexpected Z80 source")
            hl=word(state,address);pc+=3
        elif op==0x22:
            address=master[pc+1]|master[pc+2]<<8
            if address not in (b for a,b in PAIRS):raise ValueError("Unexpected Z80 destination")
            put(state,address,hl);writes.append((address,hl));pc+=3
        elif op==0xC9:
            if pc!=RET or len(writes)!=11:raise ValueError("Incomplete original RET")
            return {"ram":bytes(state),"writes":writes,"return_pc":pc}
        else:raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
        if not START<=pc<=RET:raise ValueError("Original Z80 escaped stage")
    raise ValueError("Original backup did not return")
def verify(master,cases=50000):
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated private original arcade master required")
    if hashlib.sha256(master[START:RET+1]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original Z80 geometry-save signature differs")
    rng=Random(0x75F2)
    for i in range(cases):
        ram=rng.randbytes(8192)
        if independent(ram)!=original_opcodes(master,ram):
            raise AssertionError(f"Original 75F2 opcode mismatch at {i}")
    return {"cases":cases,"mismatches":0,"saved_words":11,"saved_bytes":22,
            "scope":"original checkpoint only, not full collision response"}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("master",type=Path)
    p.add_argument("--cases",type=int,default=50000)
    a=p.parse_args()
    print(json.dumps(verify(a.master.read_bytes(),a.cases),indent=2))
