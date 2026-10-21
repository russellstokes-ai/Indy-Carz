#!/usr/bin/env python3
"""Original 1991 Indy Heat arcade steering stage: master Z80 7315-7375.

Models genuine carried-borrow steering clamp, original X-ROM signed
multiplication and 16-bit heading update. The CPU interpreter separately
executes original Z80 opcodes using only a user-supplied PRIVATE master
ROM and X-ROM; no original program, music, graphics or lookup bytes
are distributed or committed to public GitHub.

Original E771 < 0x0100 branches to unverified downstream 7376;
original E773 < 0x0100 branches to unverified downstream 7381.
These paths are preserved as explicit boundaries, NOT simulated as
completed steering updates.
"""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA="76388ecea7010cac4167a8220533566fc7390caf5d5e6f9aa7b022ddf6cb2b73"
START,STOP,NORMAL=0x7315,0x7376,0x7530


def s8(value:int)->int:
    return value-256 if value>=128 else value


def slot0(a:int,b:int)->int:
    """Original signed-8 times signed-8 doubled, saturating to signed-16."""
    return max(-32768,min(32767,2*s8(a)*s8(b)))&65535


def _valid(e771:int,e773:int,car4c4d:int,e767:int,car71:int)->None:
    if any(not isinstance(x,int) or not 0<=x<65536
           for x in (e771,e773,car4c4d,e767)) or not 0<=car71<256:
        raise ValueError("Four original 16-bit state words and one car byte required")


def independent(e771:int,e773:int,car4c4d:int,e767:int,car71:int)->dict:
    _valid(e771,e773,car4c4d,e767,car71)
    if e771<0x100:
        return {"branch":"low_E771_to_7376","next_pc":0x7376,
                "e767":e767,"car4c4d":car4c4d,"addresses":()}
    if e773<0x100:
        return {"branch":"low_E773_to_7381","next_pc":0x7381,
                "e767":e767,"car4c4d":car4c4d,"addresses":(),"a":car71}
    selected=car4c4d
    # Original 7335 SBC HL,DE leaves CARRY, which the later original
    # 733C SBC HL,DE consumes. Thus 0xFBFE itself is PASSTHROUGH,
    # not the negative-clamp bound of a naive two-comparison port.
    if 0x0402<selected<0xFBFE:
        selected=0xFC00 if selected&0x8000 else 0x0400
        branch="negative_clamp" if car4c4d&0x8000 else "positive_clamp"
    else:
        branch="passthrough"
    first=slot0(selected>>8,0x70)
    second=slot0((selected&255)>>1,0x70)
    first_h,first_l=first>>8,first&255
    second_h=second>>8
    doubled=second_h*2
    high=(first_h-int(doubled>255))&255
    result=doubled&255
    result+=first_l
    high=(high+int(result>255))&255
    new=(high<<8)|(result&255)
    return {"branch":branch,"next_pc":NORMAL,
            "e767":(e767+new)&65535,"car4c4d":new,
            "addresses":(((selected>>8)<<8)|0x70,
                         (((selected&255)>>1)<<8)|0x70)}


def original_z80(master:bytes,xrom:bytes,e771:int,e773:int,
                 car4c4d:int,e767:int,car71:int)->dict:
    """Interpret original CPU bytes with strict instruction/memory allowlists."""
    _valid(e771,e773,car4c4d,e767,car71)
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Original private master and X-ROM image lengths required")
    ram={0xE771:e771&255,0xE772:e771>>8,
         0xE773:e773&255,0xE774:e773>>8,
         0xE767:e767&255,0xE768:e767>>8,
         0xE0CC:car4c4d&255,0xE0CD:car4c4d>>8,0xE0F1:car71}
    h=l=d=e=a=0
    carry=zero=False
    pc=START;xr=0
    addresses=[]

    def word(address:int)->int:
        return ram[address]|ram[address+1]<<8

    for _ in range(90):
        op=master[pc]
        if op==0x11:d,e=master[pc+2],master[pc+1];pc+=3
        elif op==0x21:h,l=master[pc+2],master[pc+1];pc+=3
        elif op==0x2A:
            source=master[pc+1]|master[pc+2]<<8
            if source==0xFFFC:value=xrom[2*xr]|xrom[2*xr+1]<<8
            elif source in (0xE771,0xE773,0xE767):value=word(source)
            else:raise ValueError("Unrecognized original 16-bit source")
            h,l=value>>8,value&255;pc+=3
        elif op==0x22:
            destination=master[pc+1]|master[pc+2]<<8
            value=(h<<8)|l
            if destination==0xFFFC:
                xr=value;addresses.append(xr)
            elif destination==0xE767:
                ram[destination],ram[destination+1]=value&255,value>>8
            else:raise ValueError("Unrecognized original 16-bit destination")
            pc+=3
        elif op==0xB7:carry=False;zero=a==0;pc+=1
        elif op==0xED:
            if master[pc+1]!=0x52:raise ValueError("Unexpected original SBC opcode")
            difference=(h<<8|l)-(d<<8|e)-int(carry)
            carry=difference<0;value=difference&65535
            h,l=value>>8,value&255;zero=value==0;pc+=2
        elif op==0xDA:
            target=master[pc+1]|master[pc+2]<<8
            pc=target if carry else pc+3
        elif op in (0x30,0x38,0x28):
            offset=master[pc+1]
            offset=offset-256 if offset>=128 else offset
            conditional=(not carry if op==0x30 else
                         carry if op==0x38 else zero)
            pc+=2+(offset if conditional else 0)
        elif op==0x18:
            offset=master[pc+1]
            pc+=2+(offset-256 if offset>=128 else offset)
        elif op==0xDD:
            ext=master[pc+1]
            offset=master[pc+2]
            offset=offset-256 if offset>=128 else offset
            address=0xE080+offset
            if ext in (0x7E,0x56,0x5E):
                if address not in (0xE0F1,0xE0CD,0xE0CC):
                    raise ValueError("Unexpected indexed car source")
                value=ram[address]
                if ext==0x7E:a=value
                elif ext==0x56:d=value
                else:e=value
                pc+=3
            elif ext in (0x74,0x75):
                if address not in (0xE0CD,0xE0CC):
                    raise ValueError("Unexpected indexed car destination")
                ram[address]=h if ext==0x74 else l
                pc+=3
            else:raise ValueError("Unexpected original indexed opcode")
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        elif op==0xCB:
            ext=master[pc+1]
            if ext==0x7A:zero=not bool(d&128)
            elif ext==0x3F:
                carry=bool(a&1);a>>=1;zero=a==0
            else:raise ValueError("Unrecognized original rotate/BIT opcode")
            pc+=2
        elif op==0x7D:a=l;pc+=1
        elif op==0x2E:l=master[pc+1];pc+=2
        elif op==0x32:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0xFFFD:raise ValueError("Unexpected original X-ROM address")
            xr=(a<<8)|(xr&255);addresses.append(xr);pc+=3
        elif op==0x3A:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0xFFFD:raise ValueError("Unexpected original X-ROM result")
            a=xrom[2*xr+1];pc+=3
        elif op==0x87:
            raw=a*2;a=raw&255;carry=raw>255;zero=a==0;pc+=1
        elif op==0x25:h=(h-1)&255;zero=h==0;pc+=1
        elif op==0x85:
            raw=a+l;a=raw&255;carry=raw>255;zero=a==0;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x24:h=(h+1)&255;zero=h==0;pc+=1
        elif op==0x19:
            result=(h<<8|l)+(d<<8|e)
            carry=result>65535;result&=65535
            h,l=result>>8,result&255;pc+=1
        elif op==0xC3:pc=master[pc+1]|master[pc+2]<<8
        else:raise ValueError(f"Unverified original Z80 instruction {op:02X} at {pc:04X}")

        if pc==0x7376:
            return {"branch":"low_E771_to_7376","next_pc":pc,
                    "e767":word(0xE767),"car4c4d":word(0xE0CC),"addresses":()}
        if pc==0x7381:
            return {"branch":"low_E773_to_7381","next_pc":pc,
                    "e767":word(0xE767),"car4c4d":word(0xE0CC),
                    "addresses":(),"a":a}
        if pc==NORMAL:
            branch=independent(e771,e773,car4c4d,e767,car71)["branch"]
            return {"branch":branch,"next_pc":pc,
                    "e767":word(0xE767),"car4c4d":word(0xE0CC),
                    "addresses":tuple(addresses)}
        if not START<=pc<STOP:
            raise ValueError(f"Original steering escaped bounded stage at {pc:04X}")
    raise ValueError("Original steering stage exceeded CPU instruction budget")


def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Private checksum-verified original master required")
    if len(xrom)!=0x40000 or hashlib.sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Private checksum-verified original X-ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original steering machine-instruction signature changed")
    if not 0<=cases<=200000:raise ValueError("Invalid steering verification budget")
    rng=Random(0x7315);outcomes=Counter()
    for i in range(cases):
        e771=rng.randrange(256) if i%7==0 else rng.randrange(256,65536)
        e773=rng.randrange(256) if i%7==1 else rng.randrange(256,65536)
        car=rng.choice((0,1,0x0402,0x0403,0x7FFF,0x8000,
                        0xFBFD,0xFBFE,0xFBFF,0xFFFF,rng.randrange(65536)))
        inputs=(e771,e773,car,rng.randrange(65536),rng.randrange(256))
        expected=independent(*inputs)
        observed=original_z80(master,xrom,*inputs)
        if expected!=observed:
            raise AssertionError(f"Original steering 7315 parity mismatch at input {i}")
        outcomes[expected["branch"]]+=1
    for value in range(65536):
        inputs=(0x100,0x200,value,0xEFAB,0x7F)
        if independent(*inputs)!=original_z80(master,xrom,*inputs):
            raise AssertionError(f"Original exhaustive steering clamp mismatch word {value:04X}")
    return {"original_cpu":"Master Z80 7315-7375, continuation 7376/7381/7530",
            "randomized_opcode_cases":cases,"exhaustive_car_word_cases":65536,
            "total_cases":cases+65536,"mismatches":0,
            "branches":dict(sorted(outcomes.items())),
            "critical_original_boundary":"FBFE passes unclamped because borrow carries into second SBC",
            "scope":"Bounded steering angular-input conversion only; 7376/7381 and full handling remain open"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_original_master",type=Path)
    parser.add_argument("private_original_xrom",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    args=parser.parse_args()
    print(json.dumps(verify(args.private_original_master.read_bytes(),
                            args.private_original_xrom.read_bytes(),
                            args.cases),indent=2))
