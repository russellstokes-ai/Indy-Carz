#!/usr/bin/env python3
"""Original Indy Heat arcade Z80 71FA–7224 signed X-ROM motion accumulator.

Reconstruct a bounded original driving stage with independent integer maths,
compared against actual original Z80 opcodes and privately authenticated
signed X-ROM. The original 1689 overflow callback is a NONLOCAL external
path. Its state changes are not invented: the verifier stops at that call.
No original ROM, track data or proprietary lookup table ships publicly.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA="123f749f4c0212daa646d4993015bb76ad45c17c1a94026f3b7d75d69112fe58"
START,STOP,EXTERNAL=0x71FA,0x7225,0x1689

def _inputs(c:int,e933:int,de:int)->None:
    if any(not isinstance(v,int) or not 0<=v<(256 if index==0 else 65536)
           for index,v in enumerate((c,e933,de))):
        raise ValueError("Original C, E933 and DE require byte/word inputs")

def signed8(n:int)->int:return n-256 if n>=128 else n
def signed16(n:int)->int:return n-65536 if n>=32768 else n

def signed_xrom_word(a:int,b:int)->int:
    """Exact original X-ROM slot 0 16-bit double-signed product."""
    if not (0<=a<256 and 0<=b<256):raise ValueError("X-ROM operands must be bytes")
    return max(-32768,min(32767,signed8(a)*signed8(b)*2)) & 65535

def independent(c:int,e933:int,de:int)->dict:
    _inputs(c,e933,de)
    if c==0:
        return {"exit":"skip_C_zero","next_pc":STOP,"de":de,"xr_addresses":()}
    first_addr=((e933>>8)<<8)|c
    second_addr=(((e933&255)>>1)<<8)|c
    first=signed_xrom_word(e933>>8,c)
    second=signed_xrom_word((e933&255)>>1,c)
    first_low,first_high=first&255,first>>8
    second_high=second>>8
    a=(second_high*2)&255
    accumulated=a+first_low
    high=(first_high-int(bool(second_high&128))+int(accumulated>255))&255
    low=accumulated&255
    mixed=(high<<8)|low
    # Original SRA H; RR L, then ADC HL,DE with RR's carry bit.
    shifted=(signed16(mixed)>>1)&65535
    total=(shifted+de+(mixed&1))&65535
    overflow=bool((~(shifted^de)&(shifted^total))&32768)
    return {"exit":"external_1689" if overflow else "normal_7225",
            "next_pc":EXTERNAL if overflow else STOP,
            "de":None if overflow else total,
            "xr_addresses":(first_addr,second_addr)}

def original_opcodes(master:bytes,xrom:bytes,c:int,e933:int,de:int)->dict:
    """Interpret real checksum-checked original Z80 instructions to exit.

    Original X-ROM address latch FF FC/FD uses ORIGINAL raw privately
    supplied data. No invented handling after CALL PE 1689 is performed.
    """
    _inputs(c,e933,de)
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Original master and X-ROM size required")
    pc=START
    a=b=h=l=0
    d,e=de>>8,de&255
    carry=zero=sign=overflow=False
    xaddr=0
    xaddrs=[]
    for _ in range(45):
        op=master[pc]
        if op==0x79:a=c;pc+=1
        elif op==0xB7:
            carry=False;zero=a==0;sign=bool(a&128);overflow=False;pc+=1
        elif op==0xCA:
            target=master[pc+1]|master[pc+2]<<8
            if target!=STOP:raise ValueError("Original zero-C branch changed")
            pc=target if zero else pc+3
        elif op==0x2A:
            address=master[pc+1]|master[pc+2]<<8
            if address==0xE933:value=e933
            elif address==0xFFFC:value=xrom[2*xaddr]|xrom[2*xaddr+1]<<8
            else:raise ValueError("Unexpected original memory read")
            h,l=value>>8,value&255;pc+=3
        elif op==0x7D:a=l;pc+=1
        elif op==0x69:l=c;pc+=1
        elif op==0x22:
            if master[pc+1:pc+3]!=bytes.fromhex("fc ff"):
                raise ValueError("Original X-ROM latch changed")
            xaddr=(h<<8)|l;xaddrs.append(xaddr);pc+=3
        elif op==0xCB:
            cmd=master[pc+1]
            if cmd==0x3F:
                carry=bool(a&1);a>>=1;zero=a==0
            elif cmd==0x2C:
                carry=bool(h&1);h=(h>>1)|(h&128)
            elif cmd==0x1D:
                before=l;l=(l>>1)|(int(carry)<<7);carry=bool(before&1)
            else:raise ValueError("Unexpected original CB shift")
            pc+=2
        elif op==0x32:
            if master[pc+1:pc+3]!=bytes.fromhex("fd ff"):
                raise ValueError("Original X-ROM high latch changed")
            xaddr=(a<<8)|(xaddr&255)
            xaddrs.append(xaddr);pc+=3
        elif op==0x3A:
            if master[pc+1:pc+3]!=bytes.fromhex("fd ff"):
                raise ValueError("Unexpected original X-ROM upper result")
            a=xrom[2*xaddr+1];pc+=3
        elif op==0x87:
            value=a*2;carry=value>255;a=value&255;pc+=1
        elif op==0x30:
            displacement=master[pc+1]
            if displacement>=128:displacement-=256
            pc+=2+(displacement if not carry else 0)
        elif op==0x25:h=(h-1)&255;pc+=1
        elif op==0x85:
            value=a+l;carry=value>255;a=value&255;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x24:h=(h+1)&255;pc+=1
        elif op==0xED:
            if master[pc+1]!=0x5A:raise ValueError("Unexpected original ADC")
            original=(h<<8)|l
            right=(d<<8)|e
            value=(original+right+int(carry))&65535
            overflow=bool((~(original^right)&(original^value))&32768)
            h,l=value>>8,value&255
            pc+=2
        elif op==0xEC:
            if master[pc+1]|master[pc+2]<<8!=EXTERNAL:
                raise ValueError("Unexpected original overflow handler")
            if overflow:
                return {"exit":"external_1689","next_pc":EXTERNAL,
                        "de":None,"xr_addresses":tuple(xaddrs)}
            pc+=3
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        else:raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")
        if pc==STOP:
            return {"exit":"skip_C_zero" if c==0 else "normal_7225",
                    "next_pc":STOP,"de":(d<<8)|e,"xr_addresses":tuple(xaddrs)}
        if not START<=pc<STOP:raise ValueError("Original X-ROM stage escaped verified region")
    raise ValueError("Original X-ROM accumulator exceeded instruction budget")

def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authentic original master checksum required")
    if len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Authentic original X-ROM checksum required")
    if sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original 71FA-7224 instruction fingerprint changed")
    if not 0<=cases<=200000:raise ValueError("Invalid verification count")
    for a in range(256):
        for b in range(256):
            original=xrom[2*((a<<8)|b)]|xrom[2*((a<<8)|b)+1]<<8
            if signed_xrom_word(a,b)!=original:
                raise AssertionError("Original slot0 signed product differs")
    rng=Random(0x71FA);branches=Counter()
    for i in range(cases):
        c=rng.choice((0,0,1,2,0x7F,0x80,0xFF,rng.randrange(256)))
        e933=rng.choice((0,1,0xFF,0x7FFF,0x8000,0xFFFF,rng.randrange(65536)))
        de=rng.choice((0,1,0xFFFF,0x7FFF,0x8000,rng.randrange(65536)))
        expected=independent(c,e933,de)
        actual=original_opcodes(master,xrom,c,e933,de)
        if expected!=actual:
            raise AssertionError(f"Original 71FA X-ROM parity mismatch case {i}")
        branches[actual["exit"]]+=1
    return {"source":"Original 1991 arcade master Z80 71FA-7224",
            "cases":cases,"mismatches":0,
            "original_slot0_product_pairs_verified":65536,
            "exit_branches":dict(sorted(branches.items())),
            "known_external_handler":"1689 overflow, stop rather than invent its state effects"}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_master",type=Path)
    parser.add_argument("original_xrom",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    args=parser.parse_args()
    print(json.dumps(verify(args.original_master.read_bytes(),
                            args.original_xrom.read_bytes(),args.cases),indent=2))
