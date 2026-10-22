#!/usr/bin/env python3
"""Original 1991 arcade Z80 021A-028C: two fixed-ROM position lookups.

Reproduces saturating wrapped coordinate-byte deltas and compare branching
with bounded ORIGINAL Z80 opcode execution, versus independent arithmetic.
The original 512-byte lookup table is read from a PRIVATE user-owned ROM
only; no table data, graphics, sound or original program bytes distributed.
Follow-on 028D/02C3/05DC actions remain unresolved, not invented.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from random import Random
import argparse,json

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="7a5897e75f952791d7f17f8d020654745f62eece09c7f300319944ae753ba892"
TABLE_SHA="60959ac9359a5c5aa9da0b39e9fc18c4be48e08e2e7a9d588c6f019c7db12f93"
START,STOP=0x021A,0x028D
TABLE_BASE=0xA000

def validate(master:bytes,slot:bytes)->None:
    if len(master)!=0x90000 or len(slot)!=256:
        raise ValueError("Original 0x90000 master and 256-byte car required")

def magnitude(value:int,base:int)->int:
    if any(not 0<=x<256 for x in (value,base)):raise ValueError("Unsigned byte inputs only")
    delta=(value-base)&255
    return min(15,((-delta)&255) if delta&128 else delta)

def independent(master:bytes,slot:bytes)->dict:
    validate(master,slot)
    if slot[0xB3]&4:return {"exit":"external_05DC"}
    x,y=slot[0x01],slot[0x0B]
    p,q=slot[0xC6],slot[0xC7]
    u,v=slot[0xC8],slot[0xC9]
    index1=(magnitude(q,y)<<4)|magnitude(p,x)
    index2=(magnitude(v,y)<<4)|magnitude(u,x)
    first=master[TABLE_BASE+2*index1+1]
    second=master[TABLE_BASE+2*index2+1]
    return {"exit":"continue_028D" if second<first else "branch_02C3",
            "first":first,"second":second,"carry":second<first,"zero":second==first,
            "b":(u-x)&255,"c":(v-y)&255,"d":magnitude(u,x),
            "e":first,"hl":TABLE_BASE+2*index2+1}

def opcode(master:bytes,slot:bytes)->dict:
    """Interpret actual instruction sequence (no external branch effects)."""
    validate(master,slot)
    a=b=c=d=e=h=l=0;z=carry=sign=False;pc=START
    for _ in range(120):
        op=master[pc]
        if op==0xDD:
            ext=master[pc+1]
            if ext==0xCB:
                if master[pc+2:pc+4]!=bytes.fromhex("3356"):
                    raise ValueError("Unexpected original AI event flag")
                z=not bool(slot[0xB3]&4);pc+=4
            elif ext==0x7E:
                disp=master[pc+2]
                sources={0x46:0xC6,0x47:0xC7,0x48:0xC8,0x49:0xC9,0x41:0xC1}
                if disp not in sources:raise ValueError("Unexpected original IX source")
                a=slot[sources[disp]];pc+=3
            elif ext==0x96:
                disp=master[pc+2]
                sources={0x81:0x01,0x8B:0x0B}
                if disp not in sources:raise ValueError("Unexpected subtraction source")
                raw=a-slot[sources[disp]]
                a=raw&255;carry=raw<0;z=a==0;sign=bool(a&128);pc+=3
            else:raise ValueError(f"Unexpected indexed opcode {ext:02X}")
        elif op==0xC2:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0x05DC:raise ValueError("Unexpected external gate")
            pc=target if not z else pc+3
        elif op==0xF2:
            target=master[pc+1]|master[pc+2]<<8
            pc=target if not sign else pc+3
        elif op==0xED:
            if master[pc+1]!=0x44:raise ValueError("Unexpected original NEG instruction")
            before=a;a=(-a)&255;carry=before!=0;z=a==0;sign=bool(a&128);pc+=2
        elif op==0xFE:
            imm=master[pc+1];difference=a-imm
            carry=difference<0;z=difference==0;sign=bool(difference&128);pc+=2
        elif op==0xDA:
            target=master[pc+1]|master[pc+2]<<8
            pc=target if carry else pc+3
        elif op==0x3E:a=master[pc+1];pc+=2
        elif op==0x4F:c=a;pc+=1
        elif op==0x47:b=a;pc+=1
        elif op==0x57:d=a;pc+=1
        elif op==0x5F:e=a;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x67:h=a;pc+=1
        elif op in (0x81,0x82,0x87):
            raw=a+c if op==0x81 else a+d if op==0x82 else a*2
            carry=raw>255;a=raw&255;z=a==0;sign=bool(a&128);pc+=1
        elif op==0xCE:
            imm=master[pc+1];raw=a+imm+int(carry)
            carry=raw>255;a=raw&255;z=a==0;sign=bool(a&128);pc+=2
        elif op==0x2C:l=(l+1)&255;z=l==0;sign=bool(l&128);pc+=1
        elif op==0x5E:
            address=(h<<8)|l
            if not TABLE_BASE<=address<TABLE_BASE+512:raise ValueError("Original first lookup outside table")
            e=master[address];pc+=1
        elif op==0x7E:
            address=(h<<8)|l
            if not TABLE_BASE<=address<TABLE_BASE+512:raise ValueError("Original second lookup outside table")
            a=master[address];pc+=1
        elif op==0xBB:z=a==e;carry=a<e;pc+=1
        elif op==0xD2:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0x02C3:raise ValueError("Unexpected candidate comparison")
            pc=target if not carry else pc+3
        else:raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
        if pc==0x05DC:return {"exit":"external_05DC"}
        if pc in (STOP,0x02C3):
            return {"exit":"continue_028D" if pc==STOP else "branch_02C3",
                    "first":e,"second":a,"carry":carry,"zero":z,
                    "b":b,"c":c,"d":d,"e":e,"hl":(h<<8)|l}
        if not START<=pc<STOP:raise ValueError(f"Original lookup left verified range {pc:04X}")
    raise ValueError("Original lookup instruction budget exceeded")

def verify(master:bytes,cases:int=100000)->dict:
    if (len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA
            or sha256(master[START:STOP]).hexdigest()!=STAGE_SHA
            or sha256(master[TABLE_BASE:TABLE_BASE+512]).hexdigest()!=TABLE_SHA):
        raise ValueError("Private checksum-matched original program/table required")
    if not 0<=cases<=250000:raise ValueError("Invalid verification budget")
    rng=Random(0x021A);hist={}
    for i in range(cases):
        car=bytearray(rng.randbytes(256))
        car[0xB3]=(car[0xB3]&~4)|(4 if i%17==0 else 0)
        car[0x01],car[0x0B]=rng.randrange(256),rng.randrange(256)
        for offset,base in ((0xC6,0x01),(0xC7,0x0B),(0xC8,0x01),(0xC9,0x0B)):
            delta=rng.choice((0,1,15,16,127,128,129,255,rng.randrange(256)))
            car[offset]=(car[base]+delta)&255
        expected=independent(master,bytes(car))
        original=opcode(master,bytes(car))
        if expected!=original:
            diff={k:(expected.get(k),original.get(k)) for k in set(expected)|set(original)
                  if expected.get(k)!=original.get(k)}
            raise AssertionError(f"Original arcade 021A metrics mismatch case {i}: {diff}")
        hist[original["exit"]]=hist.get(original["exit"],0)+1
    return {"source":"Original 1991 arcade fixed master 021A-028C",
            "stage_sha256":STAGE_SHA,"cases":cases,"mismatches":0,
            "branch_cases":hist,"private_lookup_table_bytes":512,
            "limitation":"Original candidate score comparison, not downstream steering/impact decision"}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    args=parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.cases),indent=2))
