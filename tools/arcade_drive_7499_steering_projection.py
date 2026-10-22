#!/usr/bin/env python3
"""Original 1991 arcade Z80 steering 7499–74D7: two-stage XROM projection.

Original IX+00 and selected 7376 C byte feed unsigned rounded XROM slot1;
a heading difference from shared E767/E769 then feeds TWO original signed
slot0 multiplications. The result is doubled with signed 16-bit overflow
handled by the original RETURNING 0B6B saturation helper.

100,000 original ROM opcode comparisons vs independent integer model.
Original owner-supplied ROM and X-ROM stay PRIVATE; no artwork, original
assembly, executable binaries or derived tables in public GitHub.
This is one bounded steering calculation, not complete driving physics.
"""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA="1abf854de84979426efa4347de490e5044d54ae4f0354ae68d39aa9d3c5de139"
HELPER_SHA="7f31221af095b25769c55ed50fa14e568426cdb4a9b55869686aeaca53cfaf2b"
START,STOP=0x7499,0x74D8


def s8(v:int)->int:return v-256 if v>=128 else v
def s16(v:int)->int:return v-65536 if v>=32768 else v
def signed_xrom(a:int,b:int)->int:
    if not 0<=a<256 or not 0<=b<256:
        raise ValueError("Two unsigned-byte encoded signed operands required")
    return max(-32768,min(32767,2*s8(a)*s8(b)))&65535

def unsigned_round8(a:int,b:int)->int:
    if not 0<=a<256 or not 0<=b<256:
        raise ValueError("Original slot1 operands must be bytes")
    return (a*b+128)>>8

def _check(c:int,car00:int,heading:int,e769:int)->None:
    if (not isinstance(c,int) or not isinstance(car00,int) or
        not isinstance(heading,int) or not isinstance(e769,int) or
        not (0<=c<256 and 0<=car00<256 and 0<=heading<65536 and 0<=e769<65536)):
        raise ValueError("Original 8-bit C/IX+00 and E767/E769 words required")

def independent(c:int,car00:int,heading:int,e769:int)->dict:
    _check(c,car00,heading,e769)
    b=unsigned_round8(c,car00)
    difference=(heading-e769)&65535
    if b&128:
        b>>=1
        working=difference
    else:
        working=(s16(difference)>>1)&65535
    first=signed_xrom(working>>8,b)
    second_h=signed_xrom((working&255)>>1,b)>>8
    low=(second_h*2&255)+(first&255)
    high=((first>>8)-int(bool(second_h&128))+int(low>255))&255
    combined=(high<<8)|(low&255)
    doubled=(combined*2)&65535
    overflow=bool((combined^doubled)&32768)
    output=(0x7FFF if doubled&32768 else 0x8000) if overflow else doubled
    return {"de_projection":output,"factor_b":b,
            "overflow_saturated":overflow,
            "slot1_address":(c<<8)|car00,
            "first_slot0_address":((working>>8)<<8)|b,
            "second_slot0_address":(((working&255)>>1)<<8)|b,
            "next_pc":STOP}

def original_opcodes(master:bytes,xrom:bytes,c:int,car00:int,heading:int,e769:int)->dict:
    """Boundedly interpret authentic original 7499–74D7 + 0B6B helper."""
    _check(c,car00,heading,e769)
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Authentic owner ROM and XROM image sizes required")
    a=b=0
    h=l=0
    d,e=heading>>8,heading&255
    carry=zero=sign=overflow=False
    pc=START
    address=0;addresses=[];stack=[]
    ram={0xE769:e769&255,0xE76A:e769>>8}
    for _ in range(95):
        op=master[pc]
        if op==0x61:h=c;pc+=1
        elif op==0xDD:
            if master[pc+1:pc+3]!=bytes((0x6E,0x00)):
                raise ValueError("Unexpected original indexed car byte")
            l=car00;pc+=3
        elif op==0x22:
            target=master[pc+1]|(master[pc+2]<<8)
            if target not in (0xFFFC,0xFFFE):
                raise ValueError("Unexpected original XROM address")
            address=(h<<8)|l;addresses.append(address);pc+=3
        elif op==0x3A:
            target=master[pc+1]|(master[pc+2]<<8)
            if target==0xFFFE:a=xrom[0x20000+2*address]
            elif target==0xFFFD:a=xrom[2*address+1]
            else:raise ValueError("Unknown original XROM output")
            pc+=3
        elif op==0x47:b=a;pc+=1
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        elif op==0xED:
            ext=master[pc+1]
            if ext==0x5B:
                target=master[pc+2]|master[pc+3]<<8
                if target!=0xE769:raise ValueError("Unexpected original heading state")
                d,e=ram[target+1],ram[target];pc+=4
            elif ext==0x52:
                raw=(h<<8|l)-(d<<8|e)-int(carry)
                carry=raw<0;value=raw&65535
                h,l=value>>8,value&255;pc+=2
            elif ext==0x6A:
                before=h<<8|l
                raw=before*2+int(carry)
                carry=raw>65535;value=raw&65535
                h,l=value>>8,value&255
                sign=bool(value&32768)
                overflow=bool((before^value)&32768)
                pc+=2
            else:raise ValueError(f"Unrecognized original ED opcode {ext:02X}")
        elif op==0xB7:carry=False;zero=a==0;sign=bool(a&128);pc+=1
        elif op==0xCB:
            ext=master[pc+1]
            if ext==0x78:zero=not bool(b&128)
            elif ext==0x38:carry=bool(b&1);b>>=1
            elif ext==0x2C:carry=bool(h&1);h=(h>>1)|(h&128)
            elif ext==0x1D:
                before=l;l=(l>>1)|(int(carry)<<7);carry=bool(before&1)
            elif ext==0x3F:carry=bool(a&1);a>>=1
            else:raise ValueError(f"Unknown original signed shift {ext:02X}")
            pc+=2
        elif op==0x28:
            offset=master[pc+1]
            if offset>=128:offset-=256
            pc+=2+(offset if zero else 0)
        elif op==0x18:
            offset=master[pc+1]
            if offset>=128:offset-=256
            pc+=2+offset
        elif op==0x7D:a=l;pc+=1
        elif op==0x68:l=b;pc+=1
        elif op==0x2A:
            if master[pc+1:pc+3]!=bytes((0xFC,0xFF)):
                raise ValueError("Unexpected slot0 XROM word source")
            value=xrom[2*address]|xrom[2*address+1]<<8
            h,l=value>>8,value&255;pc+=3
        elif op==0x32:
            if master[pc+1:pc+3]!=bytes((0xFD,0xFF)):
                raise ValueError("Unexpected slot0 high input latch")
            address=(a<<8)|(address&255)
            addresses.append(address);pc+=3
        elif op==0x87:
            result=a*2;carry=result>255;a=result&255;pc+=1
        elif op==0x30:
            delta=master[pc+1]
            if delta>=128:delta-=256
            pc+=2+(delta if not carry else 0)
        elif op==0x25:h=(h-1)&255;pc+=1
        elif op==0x85:
            result=a+l;carry=result>255;a=result&255;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x24:h=(h+1)&255;pc+=1
        elif op==0xEC:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0x0B6B:raise ValueError("Unexpected signed overflow helper")
            if overflow:stack.append(pc+3);pc=target
            else:pc+=3
        elif op==0xF2:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0x0B72:raise ValueError("Unexpected signed helper branch")
            pc=target if not sign else pc+3
        elif op==0x21:
            value=master[pc+1]|master[pc+2]<<8
            h,l=value>>8,value&255;pc+=3
        elif op==0xC9:
            if not stack:raise ValueError("Original overflow helper missing return")
            pc=stack.pop()
        else:raise ValueError(f"Unknown original Z80 opcode {op:02X} at {pc:04X}")
        if pc==STOP:
            if len(addresses)!=3 or stack:
                raise ValueError("Original signed projection missing X-ROM lookup")
            return {"de_projection":(d<<8)|e,"factor_b":b,
                    "overflow_saturated":overflow,
                    "slot1_address":addresses[0],
                    "first_slot0_address":addresses[1],
                    "second_slot0_address":addresses[2],
                    "next_pc":STOP}
        if not (START<=pc<STOP or 0x0B6B<=pc<=0x0B75):
            raise ValueError(f"Original CPU left verified 7499 stage at {pc:04X}")
    raise ValueError("Original projection opcode budget exceeded")


def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated original private master ROM required")
    if len(xrom)!=0x40000 or hashlib.sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Authenticated original private XROM required")
    for first,last,digest in (
        (START,STOP,STAGE_SHA),(0x0B6B,0x0B76,HELPER_SHA)):
        if hashlib.sha256(master[first:last]).hexdigest()!=digest:
            raise ValueError(f"Original 7499 opcode signature mismatch {first:04X}")
    if not 0<=cases<=200000:raise ValueError("Invalid bounded test budget")
    rng=Random(0x7499);hist=Counter()
    for i in range(cases):
        inputs=(rng.randrange(256),rng.randrange(256),
                rng.randrange(65536),rng.randrange(65536))
        expected=independent(*inputs)
        actual=original_opcodes(master,xrom,*inputs)
        if actual!=expected:
            raise AssertionError(f"Original 7499 steering output mismatch {i}")
        hist["saturated" if expected["overflow_saturated"] else "normal"]+=1
    return {"source":"Authentic master Z80 7499–74D7, 0B6B helper",
            "cases":cases,"mismatches":0,
            "signed_slot0_lookups_per_case":2,
            "rounded_unsigned_slot1_lookups_per_case":1,
            "outcomes":dict(hist),
            "limitation":"Bounded XROM projection only; 74D8+ steering decay separate"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_master",type=Path)
    p.add_argument("private_xrom",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    opts=p.parse_args()
    print(json.dumps(verify(opts.private_master.read_bytes(),
                            opts.private_xrom.read_bytes(),opts.cases),indent=2))
