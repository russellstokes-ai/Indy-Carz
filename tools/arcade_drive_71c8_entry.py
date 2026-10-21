#!/usr/bin/env python3
"""Original arcade master Z80 drive entry: PC 71C8..71FE.

Unmodified 1991 Indy Heat rev1 original opcode execution is compared with
an independent input/byte model. It proves the C==0 or pedal>=16 branch
which can skip the entire later motion update. The derived displacement
at 71D9 is a genuine 8-bit rounded X-ROM product followed by signed
16-bit wrapping; no invented acceleration or physics timing is present.

Private user-owned original master/XROM are provided only for LOCAL tests.
Original binary, art, source assembly and lookup values stay out of GitHub.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from random import Random

MASTER_HASH="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_HASH="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
START,STOP,SHORT_CIRCUIT=0x71C8,0x71FF,0x726D
STAGE_SHA="08b32d7289ecdacab96816b7b42c44723bb2412923c0b28172b93e8e90ca9a53"

def valid(response:int,b:int,c:int,car_f5:int,e76c:int)->None:
    if any(not isinstance(v,int) or not 0<=v<256
           for v in (response,b,c,car_f5,e76c)):
        raise ValueError("Five original 8-bit Z80 drive fields required")

def independent(response:int,b:int,c:int,car_f5:int,e76c:int)->dict:
    valid(response,b,c,car_f5,e76c)
    if response>=16:
        if c==0:
            return {"exit":"skip_direct_726D","next_pc":SHORT_CIRCUIT,
                    "de":None,"source":"car_response_ge_16_C_zero"}
        return {"exit":"zero_contribution_71FF","next_pc":STOP,
                "de":0,"source":"car_response_ge_16_C_nonzero"}
    rounded=(b*car_f5+128)>>8
    amount=(((rounded<<1)&255)<<4)&65535
    if e76c&128:amount=(-amount)&65535
    if c==0:
        return {"exit":"skip_xrom_7225","next_pc":0x7225,
                "de":amount,"source":"original_71D9_displacement"}
    return {"exit":"original_xrom_71FF","next_pc":STOP,
            "de":amount,"source":"original_71D9_displacement"}

def original_z80(master:bytes,xrom:bytes,response:int,b:int,c:int,
                 car_f5:int,e76c:int)->dict:
    """Interpret actual original Z80 71C8-71FE; no unknown instructions."""
    valid(response,b,c,car_f5,e76c)
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Private authentic original ROM and XROM required")
    a=h=l=d=e=0
    carry=zero=sign=False
    pc=START;xr=0
    for _ in range(80):
        op=master[pc]
        if op==0xDD:
            sub,disp=master[pc+1:pc+3]
            if (sub,disp)==(0x7E,0x57):a=response
            elif (sub,disp)==(0x6E,0xF5):l=car_f5
            else:raise ValueError("Unexpected original IX input field")
            pc+=3
        elif op==0xFE:
            immediate=master[pc+1]
            if immediate!=16:raise ValueError("Original threshold changed")
            raw=a-immediate;carry=raw<0;zero=raw==0;sign=bool(raw&128);pc+=2
        elif op==0x38:
            rel=master[pc+1];rel=rel-256 if rel>=128 else rel
            pc+=2+(rel if carry else 0)
        elif op==0x79:a=c;pc+=1
        elif op==0xB7:carry=False;zero=a==0;sign=bool(a&128);pc+=1
        elif op==0xCA:
            target=master[pc+1]|master[pc+2]<<8
            if target not in (SHORT_CIRCUIT,0x7225):
                raise ValueError("Original conditional bypass changed")
            pc=target if zero else pc+3
        elif op==0x11:
            value=master[pc+1]|master[pc+2]<<8
            if pc!=0x71D4 or value!=0:raise ValueError("Unexpected DE override")
            d=e=0;pc+=3
        elif op==0x18:
            rel=master[pc+1];rel=rel-256 if rel>=128 else rel
            pc+=2+rel
        elif op==0x60:h=b;pc+=1
        elif op==0x22:
            address=master[pc+1]|master[pc+2]<<8
            if address!=0xFFFE:raise ValueError("Original XROM latch differs")
            xr=(h<<8)|l;pc+=3
        elif op==0x3A:
            address=master[pc+1]|master[pc+2]<<8
            if address==0xFFFE:a=xrom[0x20000+2*xr]
            elif address==0xE76C:a=e76c
            else:raise ValueError("Unknown original motion/XROM input")
            pc+=3
        elif op==0x87:
            value=a*2;carry=value>255;a=value&255
            sign=bool(a&128);zero=a==0;pc+=1
        elif op==0x26:h=master[pc+1];pc+=2
        elif op==0x6F:l=a;pc+=1
        elif op==0x29:
            value=((h<<8)|l)*2;carry=value>65535
            value&=65535;h,l=value>>8,value&255;pc+=1
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        elif op==0xF2:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0x71FA:raise ValueError("Unexpected signed motion skip")
            pc=target if not sign else pc+3
        elif op==0x21:
            if master[pc+1:pc+3]!=bytes((0,0)):
                raise ValueError("Expected original two's complement zero word")
            h=l=0;pc+=3
        elif op==0xED:
            if master[pc+1]!=0x52:raise ValueError("Unexpected SBC opcode")
            value=(((h<<8)|l)-((d<<8)|e)-int(carry))&65535
            h,l=value>>8,value&255;pc+=2
        else:raise ValueError(f"Unknown original Z80 opcode {op:02X} at {pc:04X}")
        if pc in (SHORT_CIRCUIT,STOP,0x7225):
            if pc==SHORT_CIRCUIT:
                return {"exit":"skip_direct_726D","next_pc":pc,
                        "de":None,"source":"car_response_ge_16_C_zero"}
            if pc==0x7225:
                return {"exit":"skip_xrom_7225","next_pc":pc,
                        "de":(d<<8)|e,"source":"original_71D9_displacement"}
            if response>=16:
                return {"exit":"zero_contribution_71FF","next_pc":pc,
                        "de":0,"source":"car_response_ge_16_C_nonzero"}
            return {"exit":"original_xrom_71FF","next_pc":pc,
                    "de":(d<<8)|e,"source":"original_71D9_displacement"}
        if not START<=pc<STOP:
            raise ValueError(f"Original entry left bounded CPU stage {pc:04X}")
    raise ValueError("Original drive-entry instruction budget exceeded")

def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_HASH:
        raise ValueError("Original authenticated master ROM required")
    if len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_HASH:
        raise ValueError("Original authenticated X-ROM required")
    if sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original 71C8-71FE bytecode fingerprint changed")
    if not 0<=cases<=250000:raise ValueError("Invalid bounded input budget")
    rng=Random(0x71C8);outcomes=Counter()
    for i in range(cases):
        response=rng.choice((0,1,15,16,17,127,128,255,rng.randrange(256)))
        b=rng.randrange(256)
        c=rng.choice((0,0,1,2,16,127,255,rng.randrange(256)))
        car_f5=rng.randrange(256)
        motion=rng.choice((0,1,127,128,129,255,rng.randrange(256)))
        args=(response,b,c,car_f5,motion)
        expected=independent(*args)
        actual=original_z80(master,xrom,*args)
        if expected!=actual:raise AssertionError(f"Original 71C8 mismatch #{i}")
        outcomes[expected["exit"]]+=1
    return {"source":"Original Indy Heat rev1 master Z80 71C8-71FE",
            "cases":cases,"mismatches":0,
            "branch_counts":dict(sorted(outcomes.items())),
            "scope":"Authentic original input threshold + motion contribution entry; upstream B/C selection still open"}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("xrom",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    args=parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.xrom.read_bytes(),args.cases),indent=2))
