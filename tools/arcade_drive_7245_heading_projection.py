#!/usr/bin/env python3
"""Original 1991 arcade master Z80 7245-726C heading/motion projection.

Independent integer model checked against original ROM opcode interpretation.
This consumes the original updated DE motion word from 7225, and stores the
heading-relative X-ROM signed projected word at original master RAM E933.

This is one bounded driving/steering calculation, not an invented full
vehicle physics or complete original track interaction model.
All copyrighted ROM and trigonometric table data remain PRIVATE.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
from random import Random
import argparse
import json
import math

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
CODE_SHA="cd2e573ef24d0e7bc37710927b8f2655891cdea28df3215e2a2afee01c6f7918"
COS_SHA="af9538a5a2dd85b21c0d6147350d9147c282992cf9c0b4e80c12ee70bc851578"
START,STOP=0x7245,0x726D
COS_BASE=0xA200


def _inputs(e768:int,e769:int,de:int)->None:
    if not (0<=e768<=255 and 0<=e769<=65535 and 0<=de<=65535):
        raise ValueError("Original heading and two 16-bit state values required")


def signed8(value:int)->int:
    return value-256 if value>=128 else value


def slot0(a:int,b:int)->int:
    """Authentic 8x8 signed doubled X-ROM word, 16-bit saturated."""
    if not (0<=a<=255 and 0<=b<=255):
        raise ValueError("Original signed-XROM operands are unsigned bytes")
    return min(32767,max(-32768,2*signed8(a)*signed8(b)))&65535


def cos_byte(angle:int)->int:
    if not 0<=angle<=255:raise ValueError("Original heading must be a byte")
    return min(127,max(-128,round(128*math.cos(angle*math.tau/256))))&255


def independent(e768:int,e769:int,de:int)->dict:
    _inputs(e768,e769,de)
    angle=(e768-(e769>>8))&255
    cosine=cos_byte(angle)
    first_address=(de&0xFF00)|cosine
    second_address=(((de&255)>>1)<<8)|cosine
    first=slot0(de>>8,cosine)
    second_hi=slot0((de&255)>>1,cosine)>>8
    doubled=(2*second_hi)&255
    summed=doubled+(first&255)
    high=((first>>8)-int(bool(second_hi&128))+int(summed>255))&255
    return {
        "e933":(high<<8)|(summed&255),
        "angle":angle,"cosbyte":cosine,
        "first_xrom_address":first_address,
        "second_xrom_address":second_address,
        "next_pc":STOP,
    }


def original_z80(master:bytes,xrom:bytes,e768:int,e769:int,de:int)->dict:
    """Execute actual 7245..726C original opcodes, failing closed on escape."""
    _inputs(e768,e769,de)
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Original master/XROM lengths required")
    a=b=c=h=l=0
    d,e=de>>8,de&255
    carry=False
    pc=START;xrom_address=0;addresses=[];stored=None
    for _ in range(45):
        op=master[pc]
        if op==0x3A:
            source=master[pc+1]|master[pc+2]<<8
            if source==0xE768:a=e768
            elif source==0xFFFD:a=xrom[2*xrom_address+1]
            else:raise ValueError("Unrecognised original RAM/XROM read")
            pc+=3
        elif op==0x2A:
            source=master[pc+1]|master[pc+2]<<8
            if source==0xE769:word=e769
            elif source==0xFFFC:word=xrom[2*xrom_address]|xrom[2*xrom_address+1]<<8
            else:raise ValueError("Unrecognised original 16-bit read")
            h,l=word>>8,word&255;pc+=3
        elif op==0x94:a=(a-h)&255;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x26:h=master[pc+1];pc+=2
        elif op==0x4E:
            source=h<<8|l
            if not COS_BASE<=source<COS_BASE+256:
                raise ValueError("Original lookup left authenticated cosine page")
            c=master[source];pc+=1
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        elif op==0x7D:a=l;pc+=1
        elif op==0x69:l=c;pc+=1
        elif op==0x22:
            destination=master[pc+1]|master[pc+2]<<8
            if destination==0xFFFC:
                xrom_address=(h<<8)|l
                addresses.append(xrom_address)
            elif destination==0xE933:
                stored=(h<<8)|l
            else:raise ValueError("Unexpected original Z80 store")
            pc+=3
        elif op==0xCB:
            if master[pc+1]!=0x3F:raise ValueError("Unknown original rotation")
            carry=bool(a&1);a>>=1;pc+=2
        elif op==0x32:
            if master[pc+1:pc+3]!=bytes.fromhex("fd ff"):
                raise ValueError("Unknown original XROM address latch")
            xrom_address=(a<<8)|(xrom_address&255)
            addresses.append(xrom_address);pc+=3
        elif op==0x87:
            intermediate=a*2
            carry=intermediate>255;a=intermediate&255;pc+=1
        elif op==0x30:
            delta=master[pc+1]
            if delta>=128:delta-=256
            pc+=2+(delta if not carry else 0)
        elif op==0x25:h=(h-1)&255;pc+=1
        elif op==0x85:
            intermediate=a+l
            carry=intermediate>255;a=intermediate&255;pc+=1
        elif op==0x24:h=(h+1)&255;pc+=1
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")
        if pc==STOP:
            if stored is None or len(addresses)!=2:
                raise ValueError("Incomplete original motion projection")
            angle=(e768-(e769>>8))&255
            return {"e933":stored,"angle":angle,"cosbyte":c,
                    "first_xrom_address":addresses[0],
                    "second_xrom_address":addresses[1],"next_pc":STOP}
        if not START<=pc<STOP:raise ValueError("Original Z80 exited checked segment")
    raise ValueError("Original motion-projection instruction budget exceeded")


def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Checksum-verified privately owned master ROM required")
    if len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Checksum-verified privately owned XROM required")
    if sha256(master[START:STOP]).hexdigest()!=CODE_SHA:
        raise ValueError("Original motion-projection Z80 instructions changed")
    if sha256(master[COS_BASE:COS_BASE+256]).hexdigest()!=COS_SHA:
        raise ValueError("Original cosine table signature changed")
    for angle in range(256):
        if master[COS_BASE+angle]!=cos_byte(angle):
            raise AssertionError("Original cosine byte differs from independent trig math")
    if not 0<=cases<=300000:raise ValueError("Invalid test budget")
    rng=Random(0x7245)
    observed=Counter()
    for i in range(cases):
        heading=rng.choice((0,1,64,127,128,192,255,rng.randrange(256)))
        angular_word=rng.choice((0,255,65535,32767,32768,rng.randrange(65536)))
        motion=rng.choice((0,1,255,32767,32768,65535,rng.randrange(65536)))
        model=independent(heading,angular_word,motion)
        machine=original_z80(master,xrom,heading,angular_word,motion)
        if model!=machine:
            raise AssertionError(f"Original projection discrepancy {i}: model={model} machine={machine}")
        observed["zero_projection" if model["e933"]==0 else "nonzero_projection"]+=1
    return {"source":"Original 1991 arcade fixed master 7245-726C",
            "cases":cases,"mismatches":0,"cosine_samples_checked":256,
            "exit_pc":f"{STOP:04X}","outcomes":dict(observed),
            "scope":"Authentic signed heading-aligned projection into E933; complete car motion/steering still open"}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_master",type=Path)
    p.add_argument("private_xrom",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    a=p.parse_args()
    print(json.dumps(verify(a.private_master.read_bytes(),
                            a.private_xrom.read_bytes(),a.cases),indent=2))
