#!/usr/bin/env python3
"""Authentic 1991 arcade master Z80 72D3-7314 angular-motion adjustment.

Privately verified via 100,000 executions of REAL original instructions,
including the 0B7D signed-overflow helper and both non-returning 1689
branches. Two original X-ROM signed multiplications use a factor loaded
at master bank0 (0x2000 + (-car[IX+3C] & 255)).

No proprietary table bytes, sound, original code or circuit art ship here.
This is a bounded original motion stage, not complete vehicle steering,
collision/terrain interaction, car dynamics or a playable engine.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA="3f8df07d5bcb2e8f59fbfcc657ca6d57397d9533e2999d1613740cebbabb05ec"
HELPER_SHA="e5a3ac71e4a6fe4079ace0eae3c80c95ec968e2a7626cb0eb1870eafd69297ef"
FACTOR_SHA="6d8077392ba7a0519ab14ab4e14549bc970d0a37f027de20ac5f79586798a590"
START,STOP,EXTERNAL=0x72D3,0x7315,0x1689

def signed8(v:int)->int:return v-256 if v&128 else v
def signed16(v:int)->int:return v-65536 if v&32768 else v
def slot0_word(a:int,b:int)->int:
    if not 0<=a<256 or not 0<=b<256:
        raise ValueError("Authentic slot0 signed X-ROM operands require 8-bit values")
    return max(-32768,min(32767,2*signed8(a)*signed8(b)))&65535

def _check(master:bytes,car_plus3c:int,change_de:int,e765:int)->None:
    if len(master)!=0x90000 or not (0<=car_plus3c<256 and
        0<=change_de<65536 and 0<=e765<65536):
        raise ValueError("Private original master, car 8-bit factor index and two 16-bit words required")

def independent(master:bytes,car_plus3c:int,change_de:int,e765:int)->dict:
    _check(master,car_plus3c,change_de,e765)
    factor=master[0x2000+((-car_plus3c)&255)]
    first=slot0_word(change_de>>8,factor)
    second_hi=slot0_word((change_de&255)>>1,factor)>>8
    low=(second_hi*2&255)+(first&255)
    projected=((((first>>8)-int(bool(second_hi&128))+int(low>255))&255)<<8)|(low&255)
    doubled1=(projected*2)&65535
    overflow1=bool((~(projected^projected)&(projected^doubled1))&32768)
    if overflow1:
        return {"exit":"external_1689_first_double","next_pc":EXTERNAL,
                "e765":e765,"factor":factor,"projection":projected,
                "delta":None,"overflow_sub":None}
    doubled2=(doubled1*2)&65535
    overflow2=bool((~(doubled1^doubled1)&(doubled1^doubled2))&32768)
    if overflow2:
        return {"exit":"external_1689_second_double","next_pc":EXTERNAL,
                "e765":e765,"factor":factor,"projection":projected,
                "delta":None,"overflow_sub":None}
    difference=(e765-doubled2)&65535
    overflow_sub=bool(((e765^doubled2)&(e765^difference))&32768)
    if overflow_sub:difference=0x7FFF if difference&32768 else 0x8000
    resulting=difference if difference<32768 else 0
    return {"exit":"normal_7315","next_pc":STOP,"e765":resulting,
            "factor":factor,"projection":projected,"delta":doubled2,
            "overflow_sub":overflow_sub}

def original_z80(master:bytes,xrom:bytes,car_plus3c:int,
                 change_de:int,e765:int)->dict:
    """Interpret original 72D3-7314 and REAL 0B7D-0B97 helper opcodes."""
    _check(master,car_plus3c,change_de,e765)
    if len(xrom)!=0x40000:raise ValueError("Private original XROM length required")
    pc=START;a=b=c=h=l=0;d,e=change_de>>8,change_de&255
    carry=zero=sign=overflow=False
    xr=0;stack=[];bc_stack=[]
    projected=None;delta=None;overflow_sub=None
    original_e765=e765
    for _ in range(120):
        op=master[pc]
        if op==0xDD:
            if master[pc+1:pc+3]!=bytes((0x7E,0x3C)):
                raise ValueError("Unexpected original IX input")
            a=car_plus3c;pc+=3
        elif op==0xED:
            ext=master[pc+1]
            if ext==0x44:
                old=a;a=(-a)&255;carry=old!=0;zero=a==0;sign=bool(a&128);pc+=2
            elif ext in (0x6A,0x52,0x4A):
                original=h<<8|l
                other=original if ext==0x6A else (d<<8|e) if ext==0x52 else (b<<8|c)
                raw=original-other-int(carry) if ext==0x52 else original+other+int(carry)
                result=raw&65535
                overflow=(bool((original^other)&(original^result)&32768)
                          if ext==0x52 else
                          bool((~(original^other)&(original^result))&32768))
                carry=raw<0 if ext==0x52 else raw>65535
                h,l=result>>8,result&255
                zero=result==0;sign=bool(result&32768);pc+=2
                if pc==0x7309:overflow_sub=overflow
            else:raise ValueError("Unknown original ED opcode")
        elif op==0x6F:l=a;pc+=1
        elif op==0x26:h=master[pc+1];pc+=2
        elif op==0x46:
            if h!=0x20:raise ValueError("Factor table bank differs")
            b=master[(h<<8)|l];pc+=1
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        elif op==0x7D:a=l;pc+=1
        elif op==0x68:l=b;pc+=1
        elif op==0x22:
            dest=master[pc+1]|master[pc+2]<<8
            if dest==0xFFFC:xr=h<<8|l
            elif dest==0xE765:original_e765=h<<8|l
            else:raise ValueError("Unknown original memory write")
            pc+=3
        elif op==0x2A:
            source=master[pc+1]|master[pc+2]<<8
            if source==0xFFFC:value=xrom[2*xr]|xrom[2*xr+1]<<8
            elif source==0xE765:value=original_e765
            else:raise ValueError("Unexpected original word read")
            h,l=value>>8,value&255;pc+=3
        elif op==0xCB:
            if master[pc+1]!=0x3F:raise ValueError("Unexpected CB prefix")
            carry=bool(a&1);a>>=1
            sign=bool(a&128);zero=a==0;pc+=2
        elif op==0x32:
            if master[pc+1:pc+3]!=bytes((0xFD,0xFF)):
                raise ValueError("Original X-ROM address high latch changed")
            xr=(a<<8)|(xr&255);pc+=3
        elif op==0x3A:
            if master[pc+1:pc+3]!=bytes((0xFD,0xFF)):
                raise ValueError("Original X-ROM upper result changed")
            a=xrom[2*xr+1];pc+=3
        elif op==0x87:
            val=a*2;carry=val>255;a=val&255
            sign=bool(a&128);zero=a==0;pc+=1
        elif op==0x30:
            offset=master[pc+1];offset=offset-256 if offset>=128 else offset
            pc+=2+(offset if not carry else 0)
        elif op==0x25:h=(h-1)&255;pc+=1
        elif op==0x85:
            val=a+l;carry=val>255;a=val&255
            sign=bool(a&128);zero=a==0;pc+=1
        elif op==0x24:h=(h+1)&255;pc+=1
        elif op==0xB7:
            carry=False;zero=a==0;sign=bool(a&128);overflow=False;pc+=1
        elif op==0xEC:
            address=master[pc+1]|master[pc+2]<<8
            if address==EXTERNAL and overflow:
                return {"exit":"external_1689_first_double" if pc==0x72F9
                        else "external_1689_second_double",
                        "next_pc":EXTERNAL,"e765":original_e765,
                        "factor":b,"projection":projected,
                        "delta":None,"overflow_sub":None}
            if address==0x0B7D and overflow:stack.append(pc+3);pc=address
            elif address not in (EXTERNAL,0x0B7D):
                raise ValueError("Unexpected original overflow handler")
            else:pc+=3
        elif op==0xF2:
            address=master[pc+1]|master[pc+2]<<8
            if address not in (0x0B8C,0x7312):
                raise ValueError("Original JP P target differs")
            pc=address if not sign else pc+3
        elif op==0x21:
            value=master[pc+1]|master[pc+2]<<8
            h,l=value>>8,value&255;pc+=3
        elif op==0xC5:bc_stack.append((b,c));pc+=1
        elif op==0x01:
            value=master[pc+1]|master[pc+2]<<8
            b,c=value>>8,value&255;pc+=3
        elif op==0xC1:
            if not bc_stack:raise ValueError("Missing original BC stack")
            b,c=bc_stack.pop();pc+=1
        elif op==0xC9:
            if not stack:raise ValueError("Unexpected original helper RET")
            pc=stack.pop()
        else:raise ValueError(f"Unknown Z80 opcode {op:02X} at {pc:04X}")
        if pc==0x72F6:projected=h<<8|l
        if pc==0x7302:delta=h<<8|l
        if pc==STOP:
            if projected is None or delta is None or stack or bc_stack:
                raise ValueError("Original angular stage incomplete")
            return {"exit":"normal_7315","next_pc":STOP,
                    "e765":original_e765,"factor":b,
                    "projection":projected,"delta":delta,
                    "overflow_sub":overflow_sub}
        if not (START<=pc<STOP or 0x0B7D<=pc<0x0B98):
            raise ValueError(f"Original angular stage escaped at {pc:04X}")
    raise ValueError("Original angular stage instruction budget exceeded")

def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated original private master required")
    if len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Authenticated original private XROM required")
    for start,end,wanted in ((START,STOP,STAGE_SHA),
                            (0x0B7D,0x0B98,HELPER_SHA),
                            (0x2000,0x2100,FACTOR_SHA)):
        if sha256(master[start:end]).hexdigest()!=wanted:
            raise ValueError(f"Original angular-source fingerprint mismatch at {start:04X}")
    if not 0<=cases<=250000:raise ValueError("Invalid test budget")
    rng=Random(0x72D3);hist=Counter()
    for i in range(cases):
        inputs=(rng.randrange(256),
                rng.choice((0,1,65535,32768,32767,rng.randrange(65536))),
                rng.choice((0,1,65535,32768,32767,rng.randrange(65536))))
        expected=independent(master,*inputs)
        actual=original_z80(master,xrom,*inputs)
        if expected!=actual:
            mismatches={key:(expected[key],actual.get(key)) for key in expected
                        if expected[key]!=actual.get(key)}
            raise AssertionError(f"Original 72D3 case {i}: {mismatches}")
        hist[actual["exit"]]+=1
    return {"source":"Original 1991 arcade master Z80 72D3-7314 and 0B7D",
            "cases":cases,"mismatches":0,
            "original_branches":dict(sorted(hist.items())),
            "scope":"Bounded second angular-motion projection and clamps only; all 7315+ steering still OPEN"}
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("master",type=Path)
    p.add_argument("xrom",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    args=p.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.xrom.read_bytes(),args.cases),indent=2))
