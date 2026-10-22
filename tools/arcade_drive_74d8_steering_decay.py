#!/usr/bin/env python3
"""Original 1991 arcade steering limit/decay, fixed Z80 74D8–752F.

Original E76B speed limits the signed 7499 projection unless IX+31 bit0
bypasses it. IX+41 decrement takes the original signed 8-bit JP M branch:
for input 1..128 it saves the decreased counter, adds half correction to
E769 and subtracts a doubled half from E767; otherwise it leaves IX+41
unchanged, adds full correction to E769 and subtracts quarter correction
from E767. Original 16-bit signed shifts, carry and wrap are preserved.

An original-ROM-gated bounded opcode interpreter independently challenges
this model. Original copyrighted machine bytes, QRAM and track sprites
remain PRIVATE. This closes arithmetic to CPU 7530, not full physics.
"""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="80e7eede1f94ab0ee0021967a01829eb9e6dbe2d4093cd2728c0d2d04546bd4b"
START,STOP=0x74D8,0x7530

def s16(v:int)->int:return v-65536 if v>=32768 else v

def _validate(projection:int,motion:int,e769:int,e767:int,car41:int,car_b1:int)->None:
    if any(not isinstance(x,int) for x in
           (projection,motion,e769,e767,car41,car_b1)) or any(
            not 0<=v<65536 for v in (projection,motion,e769,e767)) or any(
            not 0<=v<256 for v in (car41,car_b1)):
        raise ValueError("Four original 16-bit and two indexed 8-bit CPU fields required")

def independent(projection:int,motion:int,e769:int,e767:int,car41:int,car_b1:int)->dict:
    _validate(projection,motion,e769,e767,car41,car_b1)
    selected=projection
    limited=False
    if not car_b1&1:
        shifted=(s16(motion)>>3)&65535
        carried=bool(motion&4) # actual third RR C outgoing carry
        first=0x9600-shifted-int(carried)
        borrow=first<0
        inverted=projection^0x8000
        second=(first&65535)-inverted-int(borrow)
        if second<0:
            selected=((((second&65535)+inverted)&65535)^0x8000)
            limited=True
    count=(car41-1)&255
    decremented=not bool(count&128)
    if decremented:
        half=(s16(selected)>>1)&65535
        final_de=(half*2)&65535
        new_e769=(e769+half)&65535
        new_car41=count
    else:
        final_de=(s16(selected)>>2)&65535
        new_e769=(e769+selected)&65535
        new_car41=car41
    return {
        "selected_projection":selected,
        "final_de":final_de,
        "e769":new_e769,
        "e767":(e767-final_de)&65535,
        "car41":new_car41,
        "limited":limited,
        "counter_decremented":decremented,
        "next_pc":STOP
    }

def original_opcodes(master:bytes,projection:int,motion:int,e769:int,e767:int,
                     car41:int,car_b1:int)->dict:
    """Strictly execute original 74D8–752F opcodes with 16-bit CPU flags."""
    _validate(projection,motion,e769,e767,car41,car_b1)
    if len(master)!=0x90000:raise ValueError("Authentic private original master image required")
    a=b=c=0
    h,l=e769>>8,e769&255
    d,e=projection>>8,projection&255
    carry=zero=sign=False
    pc=START;stack=[];limited=False;selected=None
    ram={0xE76B:motion&255,0xE76C:motion>>8,
         0xE769:e769&255,0xE76A:e769>>8,
         0xE767:e767&255,0xE768:e767>>8,
         0xE0C1:car41}
    for _ in range(140):
        op=master[pc]
        if op==0xDD:
            ext=master[pc+1]
            if ext==0xCB:
                if master[pc+2:pc+4]!=bytes.fromhex("3146"):
                    raise ValueError("Unexpected original indexed BIT")
                zero=not bool(car_b1&1);pc+=4
            elif ext==0x7E:
                if master[pc+2]!=0x41:
                    raise ValueError("Unexpected original counter read")
                a=ram[0xE0C1];pc+=3
            elif ext==0x77:
                if master[pc+2]!=0x41:
                    raise ValueError("Unexpected original counter write")
                ram[0xE0C1]=a;pc+=3
            else:raise ValueError(f"Unexpected original IX opcode {ext:02X}")
        elif op==0x20:
            delta=master[pc+1]
            if delta>=128:delta-=256
            pc+=2+(delta if not zero else 0)
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        elif op==0xE5:stack.append((h<<8)|l);pc+=1
        elif op==0xE1:
            if not stack:raise ValueError("Original HL restore underflow")
            value=stack.pop();h,l=value>>8,value&255;pc+=1
        elif op==0x7A:a=d;pc+=1
        elif op==0xEE:a^=master[pc+1];pc+=2
        elif op==0x57:d=a;pc+=1
        elif op==0xED:
            ext=master[pc+1]
            if ext==0x4B:
                address=master[pc+2]|master[pc+3]<<8
                if address!=0xE76B:raise ValueError("Unexpected original motion input")
                b,c=ram[address+1],ram[address];pc+=4
            elif ext in (0x42,0x52):
                other=(b<<8)|c if ext==0x42 else (d<<8)|e
                raw=((h<<8)|l)-other-int(carry)
                carry=raw<0;value=raw&65535;h,l=value>>8,value&255
                pc+=2
            else:raise ValueError(f"Unknown original ED opcode {ext:02X}")
        elif op==0xCB:
            ext=master[pc+1]
            if ext==0x28:carry=bool(b&1);b=(b>>1)|(b&128)
            elif ext==0x19:
                prev=c;c=(c>>1)|(int(carry)<<7);carry=bool(prev&1)
            elif ext==0x2A:carry=bool(d&1);d=(d>>1)|(d&128)
            elif ext==0x1B:
                prev=e;e=(e>>1)|(int(carry)<<7);carry=bool(prev&1)
            elif ext==0x23:carry=bool(e&128);e=(e<<1)&255
            elif ext==0x12:
                prev=d;d=((d<<1)|int(carry))&255;carry=bool(prev&128)
            else:raise ValueError("Unexpected original CB opcode")
            pc+=2
        elif op==0x21:
            l,h=master[pc+1:pc+3];pc+=3
        elif op==0x30:
            delta=master[pc+1]
            if delta>=128:delta-=256
            if pc==0x74FA and carry:limited=True
            pc+=2+(delta if not carry else 0)
        elif op==0x19:
            raw=((h<<8)|l)+((d<<8)|e)
            carry=raw>65535;value=raw&65535;h,l=value>>8,value&255
            pc+=1
        elif op==0x3D:
            a=(a-1)&255;zero=a==0;sign=bool(a&128);pc+=1
        elif op==0xFA:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0x751B:raise ValueError("Unexpected original JP M")
            pc=target if sign else pc+3
        elif op==0x22:
            addr=master[pc+1]|master[pc+2]<<8
            if addr not in (0xE769,0xE767):
                raise ValueError("Unexpected original angular destination")
            ram[addr],ram[addr+1]=l,h;pc+=3
        elif op==0x18:
            delta=master[pc+1]
            if delta>=128:delta-=256
            pc+=2+delta
        elif op==0x2A:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0xE767:raise ValueError("Unexpected original heading input")
            h,l=ram[addr+1],ram[addr];pc+=3
        elif op==0xB7:
            carry=False;zero=a==0;sign=bool(a&128);pc+=1
        else:raise ValueError(f"Unknown Z80 opcode {op:02X} at {pc:04X}")
        if pc==0x7503:selected=(d<<8)|e
        if pc==STOP:
            if stack or selected is None:
                raise ValueError("Original steering stage exited without completed stack")
            return {
                "selected_projection":selected,
                "final_de":(d<<8)|e,
                "e769":ram[0xE769]|ram[0xE76A]<<8,
                "e767":ram[0xE767]|ram[0xE768]<<8,
                "car41":ram[0xE0C1],
                "limited":limited,
                "counter_decremented":not bool(((car41-1)&255)&128),
                "next_pc":STOP
            }
        if not START<=pc<STOP:
            raise ValueError("Original 74D8 stage escaped bounded code")
    raise ValueError("Original 74D8 instruction budget exceeded")


def verify(master:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated private original master ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original 74D8 instruction fingerprint changed")
    if not 0<=cases<=200000:raise ValueError("Invalid stage input budget")
    rng=Random(0x74D8);paths=Counter()
    for i in range(cases):
        sources=(rng.randrange(65536),
                 rng.choice((0,1,0xFFFF,0x8000,0x7FFF,rng.randrange(65536))),
                 rng.randrange(65536),rng.randrange(65536),
                 rng.randrange(256),rng.choice((0,1,2,255,rng.randrange(256))))
        expected=independent(*sources)
        observed=original_opcodes(master,*sources)
        if expected!=observed:
            raise AssertionError(f"Original 74D8 steering state mismatch case {i}")
        paths[("limited" if expected["limited"] else "unlimited",
               "decrement" if expected["counter_decremented"] else "hold")]+=1
    return {"source":"Original 1991 arcade Z80 74D8–752F",
            "cases":cases,"mismatches":0,
            "original_control_counter_increment":"DEC A signed JP M at 7507",
            "next_pc":"7530",
            "paths":{str(key):count for key,count in sorted(paths.items())},
            "limits":"Steering state/heading and decay arithmetic; full runtime scheduling/terrain/AI remains OPEN"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_master",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    opts=p.parse_args()
    print(json.dumps(verify(opts.private_master.read_bytes(),opts.cases),indent=2))
