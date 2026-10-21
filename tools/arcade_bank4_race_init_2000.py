#!/usr/bin/env python3
"""Original 1991 arcade master bank4 2000-208B second far-call initializer.

The original fixed 1190 calls bank4 20A8 then bank4 2000. This verifier
reconstructs the second original bank4 stage, including five physical car
slot status updates, linked first-three-record checks, signed byte state
arithmetic, and two 14-course original ROM table lookups.

The independent state models are compared to strictly bounded authentic
Z80 bytecode. No original ROM/program bytes, sprites, audio or circuit
data are committed. Field names do NOT presume AI/physics/race meanings.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
BANK4_BASE = 0x30000
CAR_POINTERS = (0xE080,0xE180,0xE280,0xE380,0xE480)
SOURCE_SIGNATURES = (
    (0x2000,0x2031,"d3cfa9257ffd913a2f1d66273b831a6b9d022e501208ed79c980c1b96806853d"),
    (0x2031,0x208C,"ecc98dfa1aac7d86bbdb29e3d7d49a43abf2b877a64ac2d802355d80fb662680"),
    (0x208C,0x20A8,"78207228bc66fef91a7301b5a1b2d0cbcc231bcc57d8bb636532d9c6cd769ec5"),
    (0x2305,0x2321,"25faf2fcb6289d908ff6cd87dd0efa5e3937861f4039f1db762a043435f70486"),
)
FIXED_HELPERS = (
    (0x1783,0x178D,"8870020766664bfcd4f50d3ec074b7efdfe67570af6de15f5ca389121d686418"),
    (0x1744,0x174E,"c5218e1d10bb716a371c07bc517eaa01315525226aa06b65592d4e1a54d0e6cb"),
)


def _states(flags_7e:tuple[int,...],flags_31:tuple[int,...],
            linked_3b:tuple[int,...])->None:
    if (len(flags_7e)!=5 or len(flags_31)!=3 or len(linked_3b)!=3
        or any(not 0<=x<256 for x in flags_7e+flags_31+linked_3b)):
        raise ValueError("Five original car status bytes and three car/linked status pairs required")


def independent_flags(flags_7e:tuple[int,...],flags_31:tuple[int,...],
                      linked_3b:tuple[int,...])->dict:
    """Reset five +7E bit6 flags, optionally set first-three eligibility."""
    _states(flags_7e,flags_31,linked_3b)
    result=[value & ~64 for value in flags_7e]
    e602=0
    for i in range(3):
        if not flags_31[i]&1 and not linked_3b[i]&3:
            result[i] |= 64
            e602=1
    return {"status_7e":result,"e602":e602,"e61c":0}


def original_flags(master:bytes,flags_7e:tuple[int,...],flags_31:tuple[int,...],
                   linked_3b:tuple[int,...])->dict:
    """Interpret authentic bank4 2000-2030, 208C helper and fixed 1783."""
    _states(flags_7e,flags_31,linked_3b)
    if len(master)!=0x90000:raise ValueError("Original master executable required")
    code=bytearray(master[:0xE000])
    code[0x2000:0xA000]=master[BANK4_BASE:BANK4_BASE+0x8000]
    linked=(0xE700,0xE780,0xE800)
    ram={0xE61C:123,0xE61D:77,0xE602:9}
    for i,p in enumerate(CAR_POINTERS):
        ram[p+0x7E]=flags_7e[i]
        if i<3:
            ram[p+0x31]=flags_31[i]
            ram[p+0x7C],ram[p+0x7D]=linked[i]&255,linked[i]>>8
            ram[linked[i]+0x3B]=linked_3b[i]
    ix=iy=hl=a=0
    z=False;stack=[];pc=0x2000
    for _ in range(125):
        op=code[pc]
        if op==0x21:
            hl=code[pc+1]|code[pc+2]<<8;pc+=3
        elif op==0x22:
            addr=code[pc+1]|code[pc+2]<<8
            if addr!=0xE61C:raise ValueError("Unexpected original HL destination")
            ram[addr],ram[addr+1]=hl&255,hl>>8;pc+=3
        elif op==0xAF:a=0;z=True;pc+=1
        elif op==0x06:
            if code[pc+1]!=0:raise ValueError("Unexpected original B value")
            pc+=2
        elif op==0x32:
            addr=code[pc+1]|code[pc+2]<<8
            if addr!=0xE602:raise ValueError("Unexpected original status destination")
            ram[addr]=a;pc+=3
        elif op==0xDD:
            ext=code[pc+1]
            if ext==0x21:
                ptr=code[pc+2]|code[pc+3]<<8
                if ptr not in CAR_POINTERS:raise ValueError("Unexpected original IX car pointer")
                ix=ptr;pc+=4
            elif ext==0xCB:
                disp,code_byte=code[pc+2:pc+4]
                addr=ix+disp
                if (disp,code_byte)==(0x7E,0xB6):ram[addr] &=~64
                elif (disp,code_byte)==(0x7E,0xF6):ram[addr] |=64
                elif (disp,code_byte)==(0x31,0x46):z=not bool(ram[addr]&1)
                else:raise ValueError("Unexpected original indexed status bit opcode")
                pc+=4
            elif ext==0x66:
                if code[pc+2]!=0x7D:raise ValueError("Original IY high pointer changed")
                hl=(ram[ix+0x7D]<<8)|(hl&255);pc+=3
            elif ext==0x6E:
                if code[pc+2]!=0x7C:raise ValueError("Original IY low pointer changed")
                hl=(hl&0xFF00)|ram[ix+0x7C];pc+=3
            else:raise ValueError(f"Unknown indexed DD opcode {ext:02X}")
        elif op==0xFD:
            ext=code[pc+1]
            if ext==0xE1:
                tag,iy=stack.pop()
                if tag!="hl":raise ValueError("Original IY pointer stack imbalance")
                pc+=2
            elif ext==0x7E:
                if code[pc+2]!=0x3B:raise ValueError("Unknown original linked-status offset")
                a=ram[iy+0x3B];pc+=3
            else:raise ValueError(f"Unknown original FD opcode {ext:02X}")
        elif op==0xCD:
            dest=code[pc+1]|code[pc+2]<<8
            if dest not in (0x208C,0x1783):
                raise ValueError("Unknown original nested car/pointer call")
            stack.append(("ret",pc+3));pc=dest
        elif op==0xE5:stack.append(("hl",hl));pc+=1
        elif op==0xE6:
            if code[pc+1]!=3:raise ValueError("Original linked status mask changed")
            a &=3;z=a==0;pc+=2
        elif op==0xC0:  # RET NZ inside 208C
            if not z:
                tag,pc=stack.pop()
                if tag!="ret":raise ValueError("Original nested RET imbalance")
            else:pc+=1
        elif op==0x3E:a=code[pc+1];pc+=2
        elif op==0xC9:
            tag,pc=stack.pop()
            if tag!="ret":raise ValueError("Original 208C/helper return imbalance")
        else:raise ValueError(f"Unexpected original bank4 opcode {op:02X} at {pc:04X}")
        if pc==0x2031:
            if stack:raise ValueError("Original car-initializer stack not empty")
            return {"status_7e":[ram[p+0x7E] for p in CAR_POINTERS],
                    "e602":ram[0xE602],"e61c":ram[0xE61C]|ram[0xE61D]<<8}
        if not (0x2000<=pc<0x2031 or 0x208C<=pc<0x20A8 or 0x1783<=pc<0x178D):
            raise ValueError(f"Original bank4 initializer escaped at {pc:04X}")
    raise ValueError("Original car initializer exceeded instruction budget")


def independent_globals(e676:int,e641_low:int,course:int)->dict:
    """Z80 sign-sensitive global-state and course-indexed parameter rules."""
    if not (0<=e676<256 and 0<=e641_low<256 and 0<=course<14):
        raise ValueError("Original E676 and E641 bytes and 14-course index required")
    b=c=0
    a=e676
    # CP FF; JP M uses the SIGN of the wrapped subtraction, not
    # the unsigned carry flag. For 127..254 it skips the adjustment.
    if not ((a-255)&128):
        c=1
        if a!=255:
            c=2
            if a!=0:
                if e641_low==1:
                    c+=1
                    if a!=1:c+=1
                elif e641_low==2:
                    b+=1
                    if a!=1:
                        c+=1
                        if a!=2:c+=1
                else:
                    b+=1
                    if a!=1:
                        b+=1
                        if a!=2:
                            c+=1
                            if a!=3:c+=1
    # Exact bounded course indices are verified against original two
    # fourteen-entry tables, not artwork or unrecovered circuit data.
    return {"e63e":b,"e674":c,"e623":0x50,
            "e638":4 if course in (1,8,11,13) else 2}


def original_globals(master:bytes,e676:int,e641_low:int,course:int)->dict:
    """Execute original bank4 2031-208B + original fixed 1744 lookup."""
    independent_globals(e676,e641_low,course)
    if len(master)!=0x90000:raise ValueError("Original master executable required")
    code=bytearray(master[:0xE000])
    code[0x2000:0xA000]=master[BANK4_BASE:BANK4_BASE+0x8000]
    ram={0xE676:e676,0xE641:e641_low,0xE642:0x34,0xE699:course,
         0xE63E:0,0xE674:0,0xE623:0,0xE638:0}
    a=b=c=h=l=0;zero=sign=carry=False;pc=0x2031;stack=[]
    def read(addr:int)->int:
        if addr<0xE000:return code[addr]
        if addr not in ram:raise ValueError(f"Unexpected original RAM read {addr:04X}")
        return ram[addr]
    for _ in range(130):
        op=code[pc]
        if op==0x06:b=code[pc+1];pc+=2
        elif op==0x0E:c=code[pc+1];pc+=2
        elif op==0x3A:
            addr=code[pc+1]|code[pc+2]<<8
            if addr not in (0xE676,0xE699):raise ValueError("Unexpected original global read")
            a=read(addr);pc+=3
        elif op==0xFE:
            imm=code[pc+1];difference=(a-imm)&255
            zero=difference==0;sign=bool(difference&128);carry=a<imm;pc+=2
        elif op==0xFA:
            dest=code[pc+1]|code[pc+2]<<8
            if dest!=0x2071:raise ValueError("Original JP M destination changed")
            pc=dest if sign else pc+3
        elif op==0x28:
            delta=code[pc+1]
            if delta>=128:delta-=256
            pc+=2+(delta if zero else 0)
        elif op==0x18:
            delta=code[pc+1]
            if delta>=128:delta-=256
            pc+=2+delta
        elif op==0x0C:
            c=(c+1)&255;zero=c==0;sign=bool(c&128);pc+=1
        elif op==0x04:
            b=(b+1)&255;zero=b==0;sign=bool(b&128);pc+=1
        elif op==0xB7:
            zero=a==0;sign=bool(a&128);carry=False;pc+=1
        elif op==0x2A:
            addr=code[pc+1]|code[pc+2]<<8
            if addr!=0xE641:raise ValueError("Unknown original 16-bit source")
            l,h=read(addr),read(addr+1);pc+=3
        elif op==0x2D:
            l=(l-1)&255;zero=l==0;sign=bool(l&128);pc+=1
        elif op==0x78:a=b;pc+=1
        elif op==0x79:a=c;pc+=1
        elif op==0x32:
            addr=code[pc+1]|code[pc+2]<<8
            if addr not in (0xE63E,0xE674,0xE623,0xE638):
                raise ValueError("Unexpected original global store")
            ram[addr]=a;pc+=3
        elif op==0x21:
            l,h=code[pc+1:pc+3];pc+=3
        elif op==0xCD:
            dest=code[pc+1]|code[pc+2]<<8
            if dest!=0x1744:raise ValueError("Unexpected original course lookup helper")
            stack.append(pc+3);pc=dest
        elif op==0x85:
            total=a+l;carry=total>255;a=total&255;zero=a==0;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x30:
            delta=code[pc+1]
            if delta>=128:delta-=256
            pc+=2+(delta if not carry else 0)
        elif op==0x24:h=(h+1)&255;pc+=1
        elif op==0x7E:a=read((h<<8)|l);pc+=1
        elif op==0xC9:
            if stack:pc=stack.pop()
            elif pc==0x208B:
                return {key:ram[addr] for key,addr in
                        (("e63e",0xE63E),("e674",0xE674),
                         ("e623",0xE623),("e638",0xE638))}
            else:raise ValueError("Unexpected original return PC")
        else:raise ValueError(f"Unknown original Z80 opcode {op:02X} at {pc:04X}")
        if not (0x2031<=pc<0x208C or 0x1744<=pc<0x174E):
            raise ValueError(f"Original bank4 globals escaped at {pc:04X}")
    raise ValueError("Original bank4 global initializer instruction budget exceeded")


def verify(master:bytes,flag_cases:int=30000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated original 1991 arcade master required")
    if not 0<=flag_cases<=200000:raise ValueError("Invalid opcode test count")
    for start,stop,expected in SOURCE_SIGNATURES:
        b=master[BANK4_BASE+start-0x2000:BANK4_BASE+stop-0x2000]
        if sha256(b).hexdigest()!=expected:
            raise ValueError(f"Original bank4 source/checksum changed at {start:04X}")
    for start,stop,expected in FIXED_HELPERS:
        if sha256(master[start:stop]).hexdigest()!=expected:
            raise ValueError(f"Original fixed helper checksum changed at {start:04X}")

    rng=Random(0x2000);branches=Counter()
    for i in range(flag_cases):
        states=tuple(rng.randrange(256) for _ in range(5))
        status=tuple(rng.randrange(256) for _ in range(3))
        linked=tuple(rng.randrange(256) for _ in range(3))
        result=independent_flags(states,status,linked)
        observed=original_flags(master,states,status,linked)
        if result!=observed:raise AssertionError(f"Original first-three eligibility mismatch #{i}")
        branches[f"E602={observed['e602']}"]+=1

    checked=0
    for e676 in range(256):
        for e641 in range(256):
            course=(e676+e641)%14
            expected=independent_globals(e676,e641,course)
            actual=original_globals(master,e676,e641,course)
            if expected!=actual:
                raise AssertionError(f"Original bank4 global/table mismatch {e676},{e641}")
            checked+=1
    return {
        "source":"original 1991 arcade master bank4 2000–208B, helper 208C + fixed 1783/1744",
        "status_cases":flag_cases,"global_course_cases":checked,
        "total_cases":flag_cases+checked,"mismatches":0,
        "E602_path_histogram":dict(branches),
        "open":"Later 1190 caller effects, metric 22BA, real runtime car status/AI meaning and QRAM circuit logic",
    }


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("--flag-cases",type=int,default=30000)
    args=parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.flag_cases),indent=2))
