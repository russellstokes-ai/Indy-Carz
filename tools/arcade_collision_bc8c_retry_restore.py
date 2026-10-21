#!/usr/bin/env python3
"""Original Indy Heat 1991 collision retry/rollback: fixed master BC8C–BCF9.

Recover and compare independently modelled RAM/port results against actual
bounded Z80 instructions, including nested original reset C468–C486.
The routine after BCFA is NOT modelled. No original ROM, artwork, decoded
instructions, or original game data are included; replay uses a PRIVATE
checksum-verified master ROM supplied by the owner.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from random import Random

MASTER_HASH="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
ENTRY_START,ENTRY_STOP=0xBC8C,0xBCFA
RETRY_START=0xBCA5
HELPER_START,HELPER_STOP=0xC468,0xC487
ENTRY_SHA="da5ea219ed1028b79bb20e5fd3e555b65ea587488144811c7fee56178dac126c"
RETRY_SHA="df3914391b7da52fa5305b22d91ac47764385e8c9e0620eb7efa9b1763da6679"
HELPER_SHA="a89f8afc4f414b5967f5763533c5afef01a44e7a4105a1b430c1568851ab52e2"
RAM_BASE,RAM_LEN=0xE000,0x2000
CAR_IX=tuple(0xE080+i*0x100 for i in range(5))
# These are original CPU RAM ADDRESS PAIRS, not proprietary data values:
RESTORE_PAIRS=((0xE749,0xE72B),(0xE753,0xE735),
               (0xE74B,0xE72D),(0xE74D,0xE72F),
               (0xE74F,0xE731),(0xE751,0xE733),
               (0xE755,0xE737),(0xE757,0xE739),
               (0xE759,0xE73B),(0xE75B,0xE73D),
               (0xE747,0xE767))


def checked(ram:bytes,ix:int)->None:
    if len(ram)!=RAM_LEN or ix not in CAR_IX:
        raise ValueError("Exact 8192-byte original E000-FFFF RAM and one of five original IX pointers required")

def get8(ram:bytes,addr:int)->int:return ram[addr-RAM_BASE]
def get16(ram:bytes,addr:int)->int:return get8(ram,addr)|(get8(ram,addr+1)<<8)
def put8(ram:bytearray,addr:int,val:int)->None:
    if not RAM_BASE<=addr<RAM_BASE+RAM_LEN:
        raise ValueError("Original RAM destination outside E000-FFFF")
    ram[addr-RAM_BASE]=val&255
def put16(ram:bytearray,addr:int,val:int)->None:
    put8(ram,addr,val)
    put8(ram,addr+1,val>>8)

def entry_model(source:bytes,ix:int)->dict:
    """BC8C entry: original bank select, bit7 clear, fresh counters."""
    checked(source,ix)
    ram=bytearray(source)
    bank=(get8(ram,0xE608)&0xF0)|(get8(ram,0xE976))
    put8(ram,0xE608,bank)
    put8(ram,ix+0x31,get8(ram,ix+0x31)&0x7F)
    put8(ram,0xE92E,1)
    put8(ram,0xE92C,0)
    return {"ram":bytes(ram),"port_f4":(bank,),"next_pc":0xBCFA,
            "a":1,"hl":get16(source,0xE976),
            "counter":1,"restored_words":0}

def retry_model(source:bytes,ix:int)->dict:
    """BCA5: next counter, C468 reset and 11 saved words only on fallback."""
    checked(source,ix)
    ram=bytearray(source)
    count=(get8(ram,0xE92E)+1)&255
    put8(ram,0xE92E,count)
    fall_back=count>=18
    if fall_back:
        put8(ram,ix+0x41,0)
        put8(ram,0xE76A,get8(ram,0xE768))
        put16(ram,0xE76B,0xCC00)
        put16(ram,0xE765,0)
        put8(ram,ix+0x4D,0)
        put8(ram,ix+0x4C,0)
        for src,dest in RESTORE_PAIRS:
            put16(ram,dest,get16(ram,src))
    return {"ram":bytes(ram),"port_f4":(),
            "next_pc":0xBC9E if fall_back else 0xBCFA,
            "a":get8(source,0xE768) if fall_back else count,
            "hl":get16(ram,0xE747) if fall_back else None,
            "counter":count,
            "restored_words":len(RESTORE_PAIRS) if fall_back else 0}

def original_opcodes(master:bytes,source:bytes,ix:int,stage:str)->dict:
    """Interpret the exact ORIGINAL Z80 instructions in bounded regions.

    Independent from entry_model/retry_model. No mocked C468 effects:
    original helper opcodes and their 16-bit stores are executed here.
    """
    checked(source,ix)
    if len(master)!=0x90000 or stage not in ("entry","retry"):
        raise ValueError("Private original master ROM and bounded stage required")
    ram=bytearray(source)
    pc=ENTRY_START if stage=="entry" else RETRY_START
    a=h=l=0
    carry=False
    stack:list[int]=[]
    ports=[];copied=[];counter=None;helper_calls=0
    for _ in range(120):
        op=master[pc]
        if op==0x2A:  # LD HL,(nn)
            addr=master[pc+1]|master[pc+2]<<8
            if addr not in (0xE976,*(x for x,_ in RESTORE_PAIRS)):
                raise ValueError(f"Unexpected original ROM state-load source {addr:04X}")
            value=get16(ram,addr);h,l=value>>8,value&255
            pc+=3
        elif op==0x3A:  # LD A,(nn)
            addr=master[pc+1]|master[pc+2]<<8
            if addr not in (0xE608,0xE92E,0xE768):
                raise ValueError(f"Unexpected original RAM source {addr:04X}")
            a=get8(ram,addr);pc+=3
        elif op==0xE6:a &=master[pc+1];carry=False;pc+=2
        elif op==0xB5:a |=l;carry=False;pc+=1
        elif op==0x32:
            addr=master[pc+1]|master[pc+2]<<8
            if addr not in (0xE608,0xE92E,0xE92C,0xE76A):
                raise ValueError("Unexpected original RAM byte destination")
            put8(ram,addr,a)
            if addr==0xE92E:counter=a
            pc+=3
        elif op==0xD3:
            if master[pc+1]!=0xF4:raise ValueError("Unexpected original hardware port")
            ports.append(a);pc+=2
        elif op==0xDD:
            ext=master[pc+1]
            if ext==0xCB and master[pc+2:pc+4]==bytes.fromhex("31be"):
                put8(ram,ix+0x31,get8(ram,ix+0x31)&0x7F);pc+=4
            elif ext==0x36:
                disp,value=master[pc+2:pc+4]
                if (disp,value) not in ((0x41,0),(0x4D,0),(0x4C,0)):
                    raise ValueError("Unexpected original car flag reset")
                put8(ram,ix+disp,value);pc+=4
            else:raise ValueError(f"Unverified original IX opcode at {pc:04X}")
        elif op==0xAF:a=0;carry=False;pc+=1
        elif op==0x3C:a=(a+1)&255;pc+=1
        elif op==0xFE:
            if master[pc+1]!=0x12:raise ValueError("Unexpected original retry threshold")
            carry=a<18;pc+=2
        elif op==0xDA:
            dst=master[pc+1]|master[pc+2]<<8
            if dst!=0xBCFA:raise ValueError("Unexpected original retry exit target")
            pc=dst if carry else pc+3
        elif op==0x00:pc+=1
        elif op==0xCD:
            dst=master[pc+1]|master[pc+2]<<8
            if dst!=HELPER_START:raise ValueError("Unexpected original reset callback")
            stack.append(pc+3);helper_calls+=1;pc=dst
        elif op==0x21:
            value=master[pc+1]|master[pc+2]<<8
            h,l=value>>8,value&255;pc+=3
        elif op==0x22:
            addr=master[pc+1]|master[pc+2]<<8
            if addr not in (0xE76B,0xE765,*(dst for _,dst in RESTORE_PAIRS)):
                raise ValueError("Unexpected original state/geometry word store")
            if addr in (dst for _,dst in RESTORE_PAIRS):copied.append(addr)
            put16(ram,addr,(h<<8)|l);pc+=3
        elif op==0xC9:
            if pc!=HELPER_STOP-1 or not stack:
                raise ValueError("Original reset subroutine returned incorrectly")
            pc=stack.pop()
        elif op==0xC3:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0xBC9E:raise ValueError("Original retry restart changed")
            pc=target
        else:raise ValueError(f"Unverified original Z80 opcode at {pc:04X}")
        if pc==0xBCFA or (stage=="retry" and pc==0xBC9E):
            if stack or (stage=="entry" and pc!=0xBCFA):
                raise ValueError("Unbalanced call/invalid original bounded stage")
            expected=[] if pc==0xBCFA else [dst for _,dst in RESTORE_PAIRS]
            if copied!=expected or helper_calls!=int(pc==0xBC9E):
                raise ValueError("Original eleven-word rollback incomplete")
            return {"ram":bytes(ram),"port_f4":tuple(ports),"next_pc":pc,
                    "a":a,"hl":(h<<8)|l if pc==0xBC9E or stage=="entry" else None,
                    "counter":counter,"restored_words":len(copied)}
        if not (ENTRY_START<=pc<ENTRY_STOP or HELPER_START<=pc<HELPER_STOP):
            raise ValueError(f"Original execution escaped bounded stage at {pc:04X}")
    raise ValueError("Original BC8C stage exceeded instruction budget")

def verify(master:bytes,entry_cases:int=65536,retry_cases:int=30000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_HASH:
        raise ValueError("Original checksum-verified arcade master required")
    for start,stop,digest in (
        (ENTRY_START,0xBCB2,ENTRY_SHA),(RETRY_START,ENTRY_STOP,RETRY_SHA),
        (HELPER_START,HELPER_STOP,HELPER_SHA)):
        if hashlib.sha256(master[start:stop]).hexdigest()!=digest:
            raise ValueError(f"Original opcode fingerprint changed at {start:04X}")
    if not (0<=entry_cases<=65536 and 0<=retry_cases<=100000):
        raise ValueError("Original test budget invalid")
    rng=Random(0xBC8C);hits=Counter()
    for i in range(entry_cases):
        state=bytearray(rng.randbytes(RAM_LEN))
        ix=CAR_IX[i%5]
        put8(state,0xE608,i&255);put8(state,0xE976,(i>>8)&255)
        wanted=entry_model(bytes(state),ix)
        observed=original_opcodes(master,bytes(state),ix,"entry")
        if wanted!=observed:
            field=next(k for k in wanted if wanted[k]!=observed.get(k))
            raise AssertionError(f"Original BC8C entry case {i} differs at {field}")
        hits["first_collision_check"]+=1
    for i in range(retry_cases):
        state=bytearray(rng.randbytes(RAM_LEN))
        ix=CAR_IX[i%5];put8(state,0xE92E,i%256)
        wanted=retry_model(bytes(state),ix)
        observed=original_opcodes(master,bytes(state),ix,"retry")
        if wanted!=observed:
            field=next(k for k in wanted if wanted[k]!=observed.get(k))
            raise AssertionError(f"Original BC8C retry case {i} differs at {field}")
        hits["fallback_reset_and_restore" if wanted["restored_words"] else
             "continue_collision_processing"]+=1
    return {"source":"original 1991 arcade fixed master BC8C–BCF9/C468–C486",
            "cases":entry_cases+retry_cases,"mismatches":0,
            "retry_threshold":18,"geometry_and_heading_words_restored":11,
            "exit_histogram":dict(hits),
            "scope":"bank selection, counter retry, original C468 reset and "
                    "eleven original geometry/heading words; collision maths BCFA onward unresolved"}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_master",type=Path)
    parser.add_argument("--entry-cases",type=int,default=65536)
    parser.add_argument("--retry-cases",type=int,default=30000)
    args=parser.parse_args()
    print(json.dumps(verify(args.original_master.read_bytes(),args.entry_cases,
                            args.retry_cases),indent=2))
