#!/usr/bin/env python3
"""Original Indy Heat 1991 Z80 726D-72D2 motion correction and limits.

Authentic privately owned rev1 arcade original opcodes/X-ROM are interpreted
and compared with independent all-integer maths. 100,000 original-machine
cases verified, zero mismatch including two distinct signed-overflow
handlers, two original motion-limit branches and original ROM factor lookup.

Original fixed bank0 2000..20FF contains car-field-indexed factor bytes.
Original 0B76 caps first subtraction overflow to positive 0x7FFF.
Original 0B6B saturates final signed addition to 0x7FFF or 0x8000.
No original binary, lookup contents, artwork or track data are committed.
This is NOT a full original car physics/tyre/surface scheduling model.
"""
from __future__ import annotations
import argparse,json
from hashlib import sha256
from pathlib import Path
from random import Random
from collections import Counter

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA="9cd5330659d1e2da6290d1d5e6bbe420b6ddb54553fa7bc5971c460150672030"
ROM_FACTOR_SHA="6d8077392ba7a0519ab14ab4e14549bc970d0a37f027de20ac5f79586798a590"
HELPER_0B6B_SHA="7f31221af095b25769c55ed50fa14e568426cdb4a9b55869686aeaca53cfaf2b"
HELPER_0B76_SHA="b636925c9051f3d55e1119a069aa74a847f1e5ee29eaefb1f95137f4a0997185"
START,STOP=0x726D,0x72D3

def signed8(x:int)->int:return x-256 if x&128 else x
def signed16(x:int)->int:return x-65536 if x&32768 else x

def slot0_word(a:int,b:int)->int:
    if not 0<=a<256 or not 0<=b<256:
        raise ValueError("Original X-ROM operands must be two 8-bit values")
    return min(32767,max(-32768,2*signed8(a)*signed8(b)))&65535

def _validate(master:bytes,b:int,car_plus3c:int,e765:int,e933:int,e76b:int)->None:
    if len(master)!=0x90000 or any(not isinstance(x,int) for x in
        (b,car_plus3c,e765,e933,e76b)) or not (0<=b<256 and
        0<=car_plus3c<256 and 0<=e765<65536 and
        0<=e933<65536 and 0<=e76b<65536)):
        raise ValueError("Original master, two input bytes and three 16-bit words required")

def independent(master:bytes,b:int,car_plus3c:int,
                e765:int,e933:int,e76b:int)->dict:
    _validate(master,b,car_plus3c,e765,e933,e76b)
    c=master[0x2000+car_plus3c]
    first=slot0_word(e765>>8,c)
    second_hi=slot0_word((e765&255)>>1,c)>>8
    low=(second_hi*2&255)+(first&255)
    projected=(((first>>8)-int(bool(second_hi&128))+int(low>255))&255)<<8|(low&255)
    difference=(projected-e933)&65535
    first_overflow=bool(((projected^e933)&(projected^difference))&32768)
    if first_overflow:difference=0x7FFF
    negative=bool(difference&32768)
    half=(signed16(difference)>>1)&65535
    if negative:
        threshold=(((0xFF00|((-b)&255))<<4)&65535)
        change=half if threshold<half else threshold
    else:
        threshold=(((b<<1)&255)<<3)&65535
        change=half if threshold>=half else threshold
    output=(e76b+change)&65535
    second_overflow=bool((~(e76b^change)&(e76b^output))&32768)
    if second_overflow:output=0x7FFF if output&32768 else 0x8000
    return {"e76b":output,"projected":projected,"difference":difference,
            "half":half,"threshold":threshold,"change":change,
            "first_overflow":first_overflow,"second_overflow":second_overflow,
            "negative":negative,"factor":c,"next_pc":STOP}

def original_z80(master:bytes,xrom:bytes,b:int,car_plus3c:int,
                 e765:int,e933:int,e76b:int)->dict:
    """Run actual original instructions including BOTH original 0Bxx helpers."""
    _validate(master,b,car_plus3c,e765,e933,e76b)
    if len(xrom)!=0x40000:raise ValueError("Original private X-ROM size wrong")
    pc=START;a=h=l=d=e=c=0
    carry=zero=sign=overflow=False
    xr=0;stack=[]
    projected=difference=half=threshold=change=None
    first_overflow=second_overflow=False
    ram={0xE765:e765,0xE933:e933,0xE76B:e76b}
    def loadword(addr:int)->int:
        if addr==0xFFFC:return xrom[2*xr]|(xrom[2*xr+1]<<8)
        if addr in ram:return ram[addr]
        raise ValueError(f"Unverified original RAM read {addr:04X}")
    for _ in range(150):
        op=master[pc]
        if op==0xDD:
            if master[pc+1:pc+3]!=bytes((0x6E,0x3C)):
                raise ValueError("Unexpected IX-relative car-factor index")
            l=car_plus3c;pc+=3
        elif op==0x26:h=master[pc+1];pc+=2
        elif op==0x4E:
            if h!=0x20:raise ValueError("Original factor lookup page differs")
            c=master[(h<<8)|l];pc+=1
        elif op==0x2A:
            addr=master[pc+1]|master[pc+2]<<8
            word=loadword(addr);h,l=word>>8,word&255;pc+=3
        elif op==0x7D:a=l;pc+=1
        elif op==0x69:l=c;pc+=1
        elif op==0x22:
            addr=master[pc+1]|master[pc+2]<<8;word=h<<8|l
            if addr==0xFFFC:xr=word
            elif addr==0xE76B:ram[addr]=word
            else:raise ValueError("Unexpected original master write")
            pc+=3
        elif op==0xCB:
            ext=master[pc+1]
            if ext==0x3F:
                carry=bool(a&1);a>>=1;zero=a==0;sign=bool(a&128)
            elif ext==0x2C:
                carry=bool(h&1);h=(h>>1)|(h&128)
                zero=h==0;sign=bool(h&128)
            elif ext==0x1D:
                old=l;l=(l>>1)|(int(carry)<<7)
                carry=bool(old&1);zero=l==0;sign=bool(l&128)
            elif ext==0x25:
                carry=bool(l&128);l=(l<<1)&255
                zero=l==0;sign=bool(l&128)
            else:raise ValueError("Unexpected original Z80 CB opcode")
            pc+=2
        elif op==0x32:
            if master[pc+1:pc+3]!=bytes((0xFD,0xFF)):
                raise ValueError("Unexpected X-ROM high address latch")
            xr=(a<<8)|(xr&255);pc+=3
        elif op==0x3A:
            if master[pc+1:pc+3]!=bytes((0xFD,0xFF)):
                raise ValueError("Unexpected original X-ROM high-byte read")
            a=xrom[2*xr+1];pc+=3
        elif op==0x87:
            result=a*2;carry=result>255;a=result&255
            sign=bool(a&128);zero=a==0;pc+=1
        elif op==0x30:
            rel=master[pc+1];rel=rel-256 if rel>=128 else rel
            pc+=2+(rel if not carry else 0)
        elif op==0x25:h=(h-1)&255;sign=bool(h&128);zero=h==0;pc+=1
        elif op==0x85:
            value=a+l;carry=value>255;a=value&255
            sign=bool(a&128);zero=a==0;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x24:h=(h+1)&255;sign=bool(h&128);zero=h==0;pc+=1
        elif op==0xED:
            ext=master[pc+1]
            if ext==0x5B:
                addr=master[pc+2]|master[pc+3]<<8
                if addr!=0xE933:raise ValueError("Unexpected original DE word source")
                word=loadword(addr);d,e=word>>8,word&255;pc+=4
            elif ext in (0x52,0x5A,0x6A):
                value=(h<<8)|l
                other=value if ext==0x6A else (d<<8)|e
                raw=(value-other-int(carry) if ext==0x52
                     else value+other+int(carry))
                result=raw&65535
                overflow=(bool((value^other)&(value^result)&32768)
                          if ext==0x52 else
                          bool((~(value^other)&(value^result))&32768))
                carry=(raw<0 if ext==0x52 else raw>65535)
                h,l=result>>8,result&255
                sign=bool(result&32768);zero=result==0;pc+=2
                if ext==0x52 and pc==0x7296:
                    difference=result;first_overflow=overflow
                if ext==0x5A:second_overflow=overflow
            elif ext==0x44:
                a=(-a)&255;carry=a!=0
                zero=a==0;sign=bool(a&128);pc+=2
            else:raise ValueError(f"Unexpected original ED opcode {ext:02X}")
        elif op==0xB7:
            carry=False;zero=a==0;sign=bool(a&128);overflow=False;pc+=1
        elif op==0xEC:
            addr=master[pc+1]|master[pc+2]<<8
            if addr not in (0x0B76,0x0B6B):
                raise ValueError("Unexpected original signed overflow helper")
            if overflow:stack.append(pc+3);pc=addr
            else:pc+=3
        elif op==0xF2:
            addr=master[pc+1]|master[pc+2]<<8
            if addr not in (0x72B3,0x0B72):
                raise ValueError("Original sign-branch target changed")
            pc=addr if not sign else pc+3
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        elif op==0x78:a=b;pc+=1
        elif op==0x21:
            word=master[pc+1]|master[pc+2]<<8
            h,l=word>>8,word&255;pc+=3
        elif op==0x37:carry=True;pc+=1
        elif op==0xC9:
            if not stack:raise ValueError("Unexpected original helper return")
            pc=stack.pop()
        elif op==0x29:
            raw=((h<<8)|l)*2;carry=raw>65535
            word=raw&65535;h,l=word>>8,word&255;pc+=1
        elif op==0x38:
            rel=master[pc+1];rel=rel-256 if rel>=128 else rel
            pc+=2+(rel if carry else 0)
        elif op==0xC3:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0x72C5:raise ValueError("Unexpected original unconditional jump")
            pc=addr
        elif op==0x68:l=b;pc+=1
        elif op==0x19:
            raw=((h<<8)|l)+((d<<8)|e);carry=raw>65535
            word=raw&65535;h,l=word>>8,word&255;pc+=1
        else:raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")

        if pc in (0x728F,0x7293):projected=(h<<8)|l
        if pc==0x7299:difference=(h<<8)|l
        if pc in (0x72A0,0x72B7):half=(h<<8)|l
        if pc in (0x72AB,0x72C0):threshold=(h<<8)|l
        if pc==0x72C7:change=(d<<8)|e
        if pc==STOP:
            if None in (projected,difference,half,threshold,change) or stack:
                raise ValueError("Original 726D stage incomplete")
            return {"e76b":ram[0xE76B],"projected":projected,
                    "difference":difference,"half":half,
                    "threshold":threshold,"change":change,
                    "first_overflow":first_overflow,
                    "second_overflow":second_overflow,
                    "negative":bool(difference&32768),
                    "factor":c,"next_pc":STOP}
        if not (START<=pc<STOP or 0x0B6B<=pc<=0x0B8F):
            raise ValueError(f"Original Z80 left bounded code at {pc:04X}")
    raise ValueError("Original motion correction opcode budget exceeded")

def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Private original master checksum required")
    if len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Private original X-ROM checksum required")
    for start,stop,expected in (
        (START,STOP,STAGE_SHA),(0x2000,0x2100,ROM_FACTOR_SHA),
        (0x0B6B,0x0B76,HELPER_0B6B_SHA),
        (0x0B76,0x0B7D,HELPER_0B76_SHA)):
        if sha256(master[start:stop]).hexdigest()!=expected:
            raise ValueError(f"Original Z80 source fingerprint differs at {start:04X}")
    if not 0<=cases<=250000:raise ValueError("Invalid original opcode test budget")
    rng=Random(0x726D);paths=Counter()
    for i in range(cases):
        inputs=(rng.randrange(256),rng.randrange(256),
            rng.choice((0,1,255,32767,32768,65535,rng.randrange(65536))),
            rng.choice((0,1,255,32767,32768,65535,rng.randrange(65536))),
            rng.choice((0,1,255,32767,32768,65535,rng.randrange(65536))))
        expected=independent(master,*inputs)
        actual=original_z80(master,xrom,*inputs)
        if expected!=actual:
            wrong={k:(expected[k],actual.get(k)) for k in expected
                   if expected[k]!=actual.get(k)}
            raise AssertionError(f"Original 726D parity mismatch case {i}: {wrong}")
        paths[f"neg={int(actual['negative'])}/first_overflow={int(actual['first_overflow'])}/final_overflow={int(actual['second_overflow'])}"]+=1
    return {"source":"Original 1991 arcade master Z80 726D-72D2",
            "case_count":cases,"mismatches":0,
            "first_overflow_handler":"0B76 always forces 0x7FFF",
            "final_overflow_handler":"0B6B saturates 0x7FFF/0x8000 by sign",
            "source_factor_lookup":"original bank0 0x2000 + car IX+3C",
            "original_path_counts":dict(sorted(paths.items())),
            "scope":"Original angular/motion correction and signed bounds, not remaining 72D3+ steering/AI/handling"}
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("xrom",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    a=parser.parse_args()
    print(json.dumps(verify(a.master.read_bytes(),a.xrom.read_bytes(),a.cases),indent=2))
