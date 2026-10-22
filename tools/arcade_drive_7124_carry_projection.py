#!/usr/bin/env python3
"""Original Indy Heat arcade Z80 7124–714D outgoing-carry motion projection.

Original source: authenticated, privately held 1991 arcade rev1 master/X-ROM.
Bounded genuine Z80 opcode interpretation vs an independent integer model
tests the E933 output AND incoming carry to the original 714E B/C selector.

Original signed-XROM/trig table data and any copyrighted source/graphics
are never distributed. This is an original driving subroutine, not a
complete frame scheduler, engine/traction law or player input handler.
"""
from __future__ import annotations
import argparse,json,math
from collections import Counter
from hashlib import sha256
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA="b1d188b9e42f64a0840ce9d2d1f80045960abce10e0dd6bd5b56ac529b6498a7"
START,STOP=0x7124,0x714E


def signed8(x:int)->int:return x-256 if x>=128 else x


def slot0(a:int,b:int)->int:
    if not(0<=a<256 and 0<=b<256):raise ValueError("8-bit X-ROM operands required")
    return min(32767,max(-32768,2*signed8(a)*signed8(b)))&65535


def cos8(angle:int)->int:
    if not 0<=angle<256:raise ValueError("8-bit heading required")
    return min(127,max(-128,round(128*math.cos(angle*math.tau/256))))&255


def independent(e768:int,e769:int,e76b:int)->dict:
    if not(0<=e768<256 and 0<=e769<65536 and 0<=e76b<65536):
        raise ValueError("Original heading byte and two 16-bit words required")
    angle=(e768-(e769>>8))&255
    cosine=cos8(angle)
    first=slot0(e76b>>8,cosine)
    second=slot0((e76b&255)>>1,cosine)
    doubled=((second>>8)*2)&255
    low_sum=doubled+(first&255)
    high=((first>>8)-int((second>>8)>=128)+int(low_sum>255))&255
    return {
        "e933":(high<<8)|(low_sum&255),
        "carry":int(low_sum>255),
        "cos":cosine,"angle":angle,
        "xrom":(((e76b>>8)<<8)|cosine,(((e76b&255)>>1)<<8)|cosine),
        "next_pc":STOP,
    }


def original_opcodes(master:bytes,xrom:bytes,e768:int,e769:int,e76b:int)->dict:
    """Execute real original 7124–714D Z80 instructions and FLAG C."""
    independent(e768,e769,e76b)
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Private original master and X-ROM sizes required")
    pc=START;a=h=l=c=0;carry=False
    xaddr=0;addresses=[];written=None;angle=None
    for _ in range(45):
        op=master[pc]
        if op==0x3A:
            src=master[pc+1]|master[pc+2]<<8
            if src==0xE768:a=e768
            elif src==0xFFFD:a=xrom[2*xaddr+1]
            else:raise ValueError("Unexpected original byte read")
            pc+=3
        elif op==0x2A:
            src=master[pc+1]|master[pc+2]<<8
            if src==0xE769:value=e769
            elif src==0xE76B:value=e76b
            elif src==0xFFFC:value=xrom[2*xaddr]|xrom[2*xaddr+1]<<8
            else:raise ValueError("Unexpected original word read")
            h,l=value>>8,value&255;pc+=3
        elif op==0x94:
            a=(a-h)&255;angle=a;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x26:h=master[pc+1];pc+=2
        elif op==0x4E:
            if h!=0xA2:raise ValueError("Original cosine table page changed")
            c=master[(h<<8)|l];pc+=1
        elif op==0x7D:a=l;pc+=1
        elif op==0x69:l=c;pc+=1
        elif op==0x22:
            dest=master[pc+1]|master[pc+2]<<8
            if dest==0xFFFC:
                xaddr=(h<<8)|l;addresses.append(xaddr)
            elif dest==0xE933:written=(h<<8)|l
            else:raise ValueError("Unexpected original word store")
            pc+=3
        elif op==0xCB:
            if master[pc+1]!=0x3F:raise ValueError("Unexpected original SRL")
            carry=bool(a&1);a>>=1;pc+=2
        elif op==0x32:
            if master[pc+1:pc+3]!=bytes((0xFD,0xFF)):
                raise ValueError("Original X-ROM upper address changed")
            xaddr=(a<<8)|(xaddr&255);addresses.append(xaddr);pc+=3
        elif op==0x87:
            raw=a*2;carry=raw>255;a=raw&255;pc+=1
        elif op==0x30:
            rel=master[pc+1];pc+=2+((rel-256 if rel>=128 else rel) if not carry else 0)
        elif op==0x25:h=(h-1)&255;pc+=1
        elif op==0x85:
            raw=a+l;carry=raw>255;a=raw&255;pc+=1
        elif op==0x24:h=(h+1)&255;pc+=1
        else:raise ValueError(f"Unexpected original Z80 {op:02X} at {pc:04X}")
        if pc==STOP:
            if written is None or angle is None or len(addresses)!=2:
                raise ValueError("Original stage incomplete")
            return {"e933":written,"carry":int(carry),"cos":c,
                    "angle":angle,"xrom":tuple(addresses),"next_pc":STOP}
        if not START<=pc<STOP:
            raise ValueError("Original Z80 left bounded 7124 motion source")
    raise ValueError("Original opcode budget exceeded")


def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated original master Z80 required")
    if len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Authenticated original signed X-ROM required")
    if sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original 7124 instruction fingerprint changed")
    for angle in range(256):
        if master[0xA200+angle]!=cos8(angle):
            raise ValueError("Original cosine/independent trigonometry differs")
    if not 0<=cases<=250000:raise ValueError("Invalid case budget")
    rng=Random(0x7124);hist=Counter()
    for i in range(cases):
        args=(
            rng.choice((0,1,64,127,128,192,255,rng.randrange(256))),
            rng.choice((0,1,255,32767,32768,65535,rng.randrange(65536))),
            rng.choice((0,1,255,32767,32768,65535,rng.randrange(65536))),
        )
        expected=independent(*args)
        actual=original_opcodes(master,xrom,*args)
        if expected!=actual:
            raise AssertionError(f"Original 7124 Z80 output/carry discrepancy case {i}")
        hist[str(actual["carry"])]+=1
    return {"source":"Original arcade fixed master Z80 7124–714D",
            "cases":cases,"mismatches":0,
            "carry_0":hist["0"],"carry_1":hist["1"],
            "derived_next_pc":"714E with inherited Z80 carry flag",
            "scope":"Genuine E933 projection and carry, not original per-race driving scheduler"}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_master",type=Path)
    p.add_argument("private_xrom",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    a=p.parse_args()
    print(json.dumps(verify(a.private_master.read_bytes(),
                            a.private_xrom.read_bytes(),a.cases),indent=2))
