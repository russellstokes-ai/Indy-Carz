#!/usr/bin/env python3
"""Original 1991 arcade master Z80 7376–73CC two-index steering lookup.

Authentic original CPU machine opcodes are interpreted from the user's
PRIVATE checksum-verified master ROM. Synthetic 256-byte data stand in for
the original runtime pointer E96D; no proprietary table bytes are
distributed to public GitHub or Godot.

Key original quirks confirmed against real instructions:
 - Entering at 7376 preserves the borrow from original 731B, so original
   E773=0x0100 takes the blended path, NOT the halved branch.
 - Z80 ADD A,A truncates 2*index to an EIGHT-BIT byte before adding
   the table base. Index 128 aliases index 0, 255 aliases 127.
 - Original RRA with carry averages two separate pair bytes precisely:
   (byte1+byte2)//2, including sums of 256–510.
Four exits all converge at original CPU PC 73CD. These are steering
control bytes, not the complete downstream physical car response.
"""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="1ff84b3562c1d2d254f3d1ce653ed21619de1c527aefd748d0aa08dd4f681f22"
START,STOP=0x7376,0x73CD
SYNTHETIC_BASE=0xED00

def _inputs(entry:int,e773:int,car70:int,car71:int,table:bytes)->None:
    if (entry not in (0x7376,0x7381,0x7394) or not 0<=e773<65536
            or not 0<=car70<256 or not 0<=car71<256
            or len(table)!=256):
        raise ValueError("Original three entry PCs, E773, car bytes and a 256-byte table required")

def _index(index:int)->int:
    """Original ADD A,A: the extra ninth bit is discarded."""
    return (index*2)&255

def independent(entry:int,e773:int,car70:int,car71:int,table:bytes)->dict:
    _inputs(entry,e773,car70,car71,table)
    if entry==0x7381 or (entry==0x7376 and e773>0x0100):
        selected=car71 if entry==0x7381 else car70
        pos=_index(selected)
        return {"b":table[pos]>>1,"c":table[pos+1]>>1,
                "branch":"halved_car71" if entry==0x7381 else "halved_car70",
                "next_pc":STOP}
    if car70==car71:
        pos=_index(car70)
        return {"b":table[pos],"c":table[pos+1],
                "branch":"same_index_full","next_pc":STOP}
    pos0,pos1=_index(car70),_index(car71)
    return {"b":(table[pos0]+table[pos1])>>1,
            "c":(table[pos0+1]+table[pos1+1])>>1,
            "branch":"blended_indices","next_pc":STOP}

def original_z80(master:bytes,entry:int,e773:int,car70:int,
                 car71:int,table:bytes)->dict:
    """Bounded interpretation of REAL original Z80 instructions.

    Original 7376 entry has DE=0x0100 and carry=1 from original 731B.
    Original direct 7381 entry has A=IX+71 from the 7327 path.
    Original 7394 entry begins after the 7376 early comparison.
    The synthetic pointer is E96D=ED00 with table bytes ED00..EDFF.
    Every other opcode, memory source and branch fails closed.
    """
    _inputs(entry,e773,car70,car71,table)
    if len(master)!=0x90000:
        raise ValueError("Authentic original master length must be 0x90000")
    ram={0xE773:e773&255,0xE774:e773>>8,
         0xE96D:SYNTHETIC_BASE&255,0xE96E:SYNTHETIC_BASE>>8,
         0xE0F0:car70,0xE0F1:car71}
    ram.update({SYNTHETIC_BASE+i:v for i,v in enumerate(table)})
    a=b=c=d=e=h=l=0
    carry=(entry==0x7376)
    zero=False
    pc=entry
    if entry==0x7376:
        d,e=0x01,0x00
    if entry==0x7381:
        a=car71

    def read(addr:int)->int:
        if addr not in ram:raise ValueError(f"Unexpected original steering RAM {addr:04X}")
        return ram[addr]

    for _ in range(75):
        op=master[pc]
        if op==0x2A:
            addr=master[pc+1]|master[pc+2]<<8
            if addr not in (0xE773,0xE96D):raise ValueError("Unknown original HL source")
            v=read(addr)|read(addr+1)<<8
            h,l=v>>8,v&255;pc+=3
        elif op==0xED:
            ext=master[pc+1]
            if ext==0x52:
                result=(h<<8|l)-(d<<8|e)-int(carry)
                carry=result<0
                value=result&65535;h,l=value>>8,value&255
                zero=value==0;pc+=2
            elif ext==0x5B:
                addr=master[pc+2]|master[pc+3]<<8
                if addr!=0xE96D:raise ValueError("Unknown original DE source")
                v=read(addr)|read(addr+1)<<8
                d,e=v>>8,v&255;pc+=4
            else:raise ValueError("Unknown original ED-prefixed instruction")
        elif op in (0xDA,0xD2):
            destination=master[pc+1]|master[pc+2]<<8
            jump=carry if op==0xDA else not carry
            pc=destination if jump else pc+3
        elif op==0xDD:
            ext=master[pc+1]
            displacement=master[pc+2]
            if displacement>=128:displacement-=256
            addr=0xE080+displacement
            if addr not in (0xE0F0,0xE0F1):
                raise ValueError("Unknown original indexed car field")
            if ext==0x7E:a=read(addr)
            elif ext==0x6E:l=read(addr)
            else:raise ValueError("Unknown original DD-prefixed instruction")
            pc+=3
        elif op==0x18:
            delta=master[pc+1]
            pc+=2+(delta-256 if delta>=128 else delta)
        elif op in (0x87,0x85,0x83):
            operand=a if op==0x87 else l if op==0x85 else e
            result=a+operand
            carry=result>255;a=result&255;zero=a==0;pc+=1
        elif op==0x5F:e=a;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x30:
            delta=master[pc+1]
            pc+=2+((delta-256 if delta>=128 else delta) if not carry else 0)
        elif op==0x24:h=(h+1)&255;pc+=1
        elif op==0x14:d=(d+1)&255;pc+=1
        elif op==0x46:b=read((h<<8)|l);pc+=1
        elif op==0x4E:c=read((h<<8)|l);pc+=1
        elif op==0x23:
            value=((h<<8)|l)+1
            value&=65535;h,l=value>>8,value&255;pc+=1
        elif op==0x13:
            value=((d<<8)|e)+1
            value&=65535;d,e=value>>8,value&255;pc+=1
        elif op==0xCB:
            ext=master[pc+1]
            if ext==0x38:carry=bool(b&1);b>>=1
            elif ext==0x39:carry=bool(c&1);c>>=1
            else:raise ValueError("Unknown original SRL instruction")
            pc+=2
        elif op==0x7D:a=l;pc+=1
        elif op==0xBD:
            diff=a-l;carry=diff<0;zero=diff==0;pc+=1
        elif op==0xCA:
            destination=master[pc+1]|master[pc+2]<<8
            pc=destination if zero else pc+3
        elif op==0x1A:a=read((d<<8)|e);pc+=1
        elif op==0x86:
            result=a+read((h<<8)|l)
            carry=result>255;a=result&255;zero=a==0;pc+=1
        elif op==0x1F:
            old=a;a=(a>>1)|(int(carry)<<7)
            carry=bool(old&1);pc+=1
        elif op==0x47:b=a;pc+=1
        elif op==0x4F:c=a;pc+=1
        else:raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
        if pc==STOP:
            model=independent(entry,e773,car70,car71,table)
            return {"b":b,"c":c,"branch":model["branch"],"next_pc":pc}
        if not START<=pc<STOP:
            raise ValueError(f"Original steering selector jumped outside checked stage at {pc:04X}")
    raise ValueError("Original steering lookup exceeded instruction budget")

def verify(master:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Checksum-verified owner master ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original steering selector code changed")
    if not 0<=cases<=200000:raise ValueError("Invalid steering lookup test budget")
    rng=Random(0x7376);classes=Counter()
    for i in range(cases):
        entry=(0x7376,0x7381,0x7394)[i%3]
        e773=rng.choice((0,1,0xFF,0x100,0x101,0x102,0xFFFF,rng.randrange(65536)))
        car70=rng.randrange(256)
        car71=car70 if i%7==0 else rng.randrange(256)
        table=rng.randbytes(256)
        reference=independent(entry,e773,car70,car71,table)
        actual=original_z80(master,entry,e773,car70,car71,table)
        if reference!=actual:
            raise AssertionError(f"Original steering selector differs at synthetic input {i}")
        classes[reference["branch"]]+=1
    table=bytes((i*57+113)&255 for i in range(256))
    for car70 in range(256):
        for car71 in range(256):
            expected=independent(0x7394,0,car70,car71,table)
            actual=original_z80(master,0x7394,0,car70,car71,table)
            if expected!=actual:
                raise AssertionError(f"Original exhaustive steering index mismatch {car70},{car71}")
    return {"source":"Original 1991 arcade fixed master Z80 7376-73CC",
            "randomized_opcode_cases":cases,
            "exhaustive_two_index_cases":65536,
            "total_cases":cases+65536,"mismatches":0,
            "branch_histogram":dict(sorted(classes.items())),
            "car_index_domain":"Z80 doubled byte wraps modulo 256: indices 128..255 alias 0..127",
            "comparison_E773_boundary":"Original 0x100 takes blend path due to earlier carry",
            "scope":"Exact original lookup byte selection; table contents and downstream 73CD+ steering still open"}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_original_master",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    args=parser.parse_args()
    print(json.dumps(verify(args.private_original_master.read_bytes(),args.cases),indent=2))
