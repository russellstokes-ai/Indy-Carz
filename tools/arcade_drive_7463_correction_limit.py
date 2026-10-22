#!/usr/bin/env python3
"""Original 1991 arcade steering correction limiter: master Z80 7463–7498.

Takes the verified 7442 projection in HL and original E76B 16-bit motion.
When IX+31 bit0 is set, original JP bypasses limiter at 748A; otherwise
the original three SRA/RR arithmetic shifts preserve a carry bit that is
consumed by SBC HL,BC, then another original SBC HL,DE uses its borrow.
We preserve the original unsigned 16-bit wrap, XOR 8000 and final E767
heading update. Input/output exact original-ROM opcode parity checked.

Original program/ROM data remains private. This is a bounded steering
contribution, NOT reconstructed complete grip, collision or frame physics.
"""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="2e7852f69a6a26495b7e1b7c4bbae7e02426ddf085ed8156088554c93bda2675"
START,SKIP,STOP=0x7463,0x748A,0x7499


def independent(correction:int,motion_word:int,heading:int,car_b1:int)->dict:
    if any(not isinstance(v,int) for v in (correction,motion_word,heading,car_b1)):
        raise ValueError("Original correction, velocity, heading and status must be integers")
    if any(not 0<=v<65536 for v in (correction,motion_word,heading)) or not 0<=car_b1<256:
        raise ValueError("Three original 16-bit state words and one IX+31 byte required")
    chosen=correction
    limited=False
    if not car_b1&1:
        signed=motion_word-65536 if motion_word&32768 else motion_word
        shift3=(signed>>3)&65535
        # Carry from original third RR C (the source's original bit 2).
        shift_carry=bool(motion_word&4)
        intermediate=0x9600-shift3-int(shift_carry)
        first_borrow=intermediate<0
        inverted=correction^0x8000
        second=(intermediate&65535)-inverted-int(first_borrow)
        if second<0:
            reverted=((second&65535)+inverted)&65535
            chosen=reverted^0x8000
            limited=True
    return {"car4c4d":chosen,"heading_e767":(heading+chosen)&65535,
            "limited":limited,"limiter_bypassed":bool(car_b1&1),
            "next_pc":STOP}


def original_opcodes(master:bytes,correction:int,motion_word:int,heading:int,car_b1:int)->dict:
    independent(correction,motion_word,heading,car_b1)
    if len(master)!=0x90000:raise ValueError("Authentic private master 0x90000 image required")
    a=b=c=0
    h,l=correction>>8,correction&255
    d=e=0;carry=False
    ram={0xE76B:motion_word&255,0xE76C:motion_word>>8,
         0xE767:heading&255,0xE768:heading>>8,
         0xE0CC:0xA5,0xE0CD:0x5A}
    stack=[]
    pc=SKIP if car_b1&1 else START
    limited=False

    for _ in range(90):
        op=master[pc]
        if op==0xC5:
            stack.append((b<<8)|c);pc+=1
        elif op==0xC1:
            value=stack.pop();b,c=value>>8,value&255;pc+=1
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        elif op==0x7A:a=d;pc+=1
        elif op==0xEE:a^=master[pc+1];pc+=2
        elif op==0x57:d=a;pc+=1
        elif op==0xED:
            ext=master[pc+1]
            if ext==0x4B:
                addr=master[pc+2]|master[pc+3]<<8
                if addr!=0xE76B:raise ValueError("Unexpected velocity source")
                b,c=ram[addr+1],ram[addr];pc+=4
            elif ext in (0x42,0x52):
                operand=(b<<8)|c if ext==0x42 else (d<<8)|e
                raw=((h<<8)|l)-operand-int(carry)
                carry=raw<0
                value=raw&65535;h,l=value>>8,value&255;pc+=2
            else:raise ValueError(f"Unexpected original ED opcode {ext:02X}")
        elif op==0xCB:
            ext=master[pc+1]
            if ext==0x28:carry=bool(b&1);b=(b>>1)|(b&128)
            elif ext==0x19:
                prior=c;c=(c>>1)|(int(carry)<<7);carry=bool(prior&1)
            else:raise ValueError("Unexpected original shift")
            pc+=2
        elif op==0x21:
            l,h=master[pc+1:pc+3];pc+=3
        elif op==0x30:
            delta=master[pc+1]
            if delta>=128:delta-=256
            if pc==0x7480 and carry:limited=True
            pc+=2+(delta if not carry else 0)
        elif op==0x19:
            value=((h<<8)|l)+((d<<8)|e)
            carry=value>65535;value&=65535;h,l=value>>8,value&255;pc+=1
        elif op==0xDD:
            sub,disp=master[pc+1:pc+3]
            addr=0xE080+disp
            if addr not in (0xE0CC,0xE0CD) or sub not in (0x74,0x75):
                raise ValueError("Original indexed car field differs")
            ram[addr]=h if sub==0x74 else l;pc+=3
        elif op==0x2A:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0xE767:raise ValueError("Original heading source changed")
            h,l=ram[addr+1],ram[addr];pc+=3
        elif op==0x22:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0xE767:raise ValueError("Original heading destination changed")
            ram[addr],ram[addr+1]=l,h;pc+=3
        elif op==0x61:h=c;pc+=1
        else:raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
        if pc==STOP:
            if stack:raise ValueError("Original AF/BC stack not restored")
            return {"car4c4d":ram[0xE0CC]|ram[0xE0CD]<<8,
                    "heading_e767":ram[0xE767]|ram[0xE768]<<8,
                    "limited":limited,"limiter_bypassed":bool(car_b1&1),
                    "next_pc":STOP}
        if not START<=pc<STOP:
            raise ValueError(f"Original limiter escaped bounded stage at {pc:04X}")
    raise ValueError("Original 7463 instruction budget exceeded")


def verify(master:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Private checksum-verified original master required")
    if hashlib.sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original 7463 limiter opcode fingerprint changed")
    if not 0<=cases<=200000:raise ValueError("Invalid original limiter test budget")
    rng=Random(0x7463);outcomes=Counter()
    for i in range(cases):
        inputs=(rng.randrange(65536),
                rng.choice((0,1,32767,32768,65535,rng.randrange(65536))),
                rng.randrange(65536),
                rng.choice((0,1,2,255,rng.randrange(256))))
        model=independent(*inputs)
        observed=original_opcodes(master,*inputs)
        if model!=observed:
            raise AssertionError(f"Original 7463 limit mismatch case {i}")
        outcomes["bypassed" if model["limiter_bypassed"]
                 else "limited" if model["limited"] else "retained"]+=1
    return {"source":"Original arcade rev1 fixed master Z80 7463–7498",
            "cases":cases,"mismatches":0,"paths":dict(sorted(outcomes.items())),
            "unverified":"Control over earlier speed/steering and subsequent 7499–752F stages"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_master",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    args=p.parse_args()
    print(json.dumps(verify(args.private_master.read_bytes(),args.cases),indent=2))
