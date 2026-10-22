#!/usr/bin/env python3
"""Verify original Indy Heat 1991 arcade paired collision geometry translation.

Master Z80 fixed ROM B985..BA1F and BA20..BABA. Each routine adds BC to
five 16-bit car-slot words and DE to the following five and marks status +7C
bit 6. If the high byte of either supplied offset is outside [-5,4], the
original code conditionally calls $1689, a separate nonlocal escape routine;
we report that path but do NOT guess its gameplay effect or emulate it.

This is a local original-ROM verifier, not full game collision physics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STARTS={"IX":0xB985, "IY":0xBA20}
ENDS={"IX":0xBA20, "IY":0xBABB}
STAGE_SHA={
    "IX":"400755ca6f3478bda5e4e765c420032c4fd59d94da55b0d5ebe52836eb008fb8",
    "IY":"d6aed40a17b98f3d5d3fdd14c76f4137f13b927b3fa0d68c1e44893de8c205cf",
}

def u16(mem:bytes|bytearray,offset:int)->int:
    return mem[offset] | (mem[offset+1]<<8)

def valid_high(b:int)->bool:
    return (0<=b<=4) or (251<=b<=255)

def model(slot:bytes,bc:int,de:int)->tuple[str,bytes]:
    if len(slot)!=256 or not 0<=bc<65536 or not 0<=de<65536:
        raise ValueError("Original arcade slot must have 256 bytes, 16-bit inputs")
    if not valid_high(bc>>8):
        return "escape_on_B",slot
    if not valid_high(de>>8):
        return "escape_on_D",slot
    out=bytearray(slot)
    for i in range(10):
        at=i*2
        value=(u16(out,at)+(bc if i<5 else de))&0xFFFF
        out[at:at+2]=value.to_bytes(2,"little")
    out[0x7c]|=0x40
    return "applied",bytes(out)

def emulate(master:bytes,slot:bytes,bc:int,de:int,which:str)->tuple[str,bytes,int]:
    if len(master)!=0x90000 or which not in STARTS:
        raise ValueError("Expected original MAME-rotated master image and IX/IY endpoint")
    if len(slot)!=256 or not 0<=bc<65536 or not 0<=de<65536:
        raise ValueError("Expected original slot and BC/DE input words")
    pc=STARTS[which];end=ENDS[which]
    index=0xDD if which=="IX" else 0xFD
    out=bytearray(slot)
    a=h=l=0
    carry=False
    for step in range(130):
        op=master[pc]
        if op==0x78:  # LD A,B
            a=bc>>8;pc+=1
        elif op==0x7A:  # LD A,D
            a=de>>8;pc+=1
        elif op==0xFE: # CP imm
            carry=a<master[pc+1];pc+=2
        elif op==0x38: # JR C, signed
            d=master[pc+1]; d=d-256 if d>=128 else d
            pc+=2+(d if carry else 0)
        elif op==0xDC: # CALL C,1689h (nonlocal abnormal path)
            target=u16(master,pc+1)
            if target!=0x1689:raise ValueError(f"Unexpected CALL C at {pc:04X}")
            if carry:
                return ("escape_on_B" if pc<STARTS[which]+11 else "escape_on_D"),bytes(out),step+1
            pc+=3
        elif op==index:
            ext=master[pc+1]
            if ext==0xCB:
                displacement,bop=master[pc+2:pc+4]
                if (displacement,bop)!=(0xFC,0xF6):
                    raise ValueError(f"Unexpected indexed bit operation at {pc:04X}")
                out[0x7C]|=0x40
                pc+=4
            else:
                displacement=master[pc+2]
                offset=(displacement-128)&0xFF # IX base == slot + 0x80
                if not 0<=offset<256:
                    raise ValueError("Invalid original car record offset")
                if ext==0x66:h=out[offset]
                elif ext==0x6E:l=out[offset]
                elif ext==0x74:out[offset]=h
                elif ext==0x75:out[offset]=l
                else:raise ValueError(f"Unexpected indexed opcode {ext:02X} at {pc:04X}")
                pc+=3
        elif op in (0x09,0x19): # ADD HL,BC/DE
            value=(((h<<8)|l)+(bc if op==0x09 else de))&65535
            h,l=value>>8,value&255
            pc+=1
        elif op==0xC9:
            if pc!=end-1:
                raise ValueError(f"Unexpected early return at {pc:04X}")
            return "applied",bytes(out),step+1
        else:
            raise ValueError(f"Unsupported original response opcode {op:02X} at {pc:04X}")
        if not STARTS[which]<=pc<end:
            raise ValueError(f"Original branch escaped routine bounds at {pc:04X}")
    raise ValueError("Original response instruction budget exceeded")

def verify(master:bytes,samples:int=2500)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Private verified original 1991 arcade master ROM is required")
    if not 0<=samples<=100000:raise ValueError("Invalid sample count")
    source={name:hashlib.sha256(master[STARTS[name]:ENDS[name]]).hexdigest() for name in STARTS}
    if source!=STAGE_SHA:
        raise ValueError("Original collision geometry routine signatures differ")
    rng=Random(0xB9852026)
    counts=Counter()
    for which in STARTS:
        for n in range(samples):
            raw=bytearray(rng.randbytes(256))
            bh=rng.choice((0,1,2,3,4,5,127,128,250,251,252,253,254,255))
            dh=rng.choice((0,1,2,3,4,5,127,128,250,251,252,253,254,255))
            bc=(bh<<8)|rng.randrange(256);de=(dh<<8)|rng.randrange(256)
            expected=model(bytes(raw),bc,de)
            result,updated,steps=emulate(master,bytes(raw),bc,de,which)
            if (result,updated)!=expected:
                raise AssertionError(f"Original response mismatch {which} B={bh:02X},D={dh:02X}")
            counts[which+":"+result]+=1
    return {"source":"1991 arcade master fixed ROM, original instruction parity",
            "routines":{name:{"start":f"{STARTS[name]:04X}","end_exclusive":f"{ENDS[name]:04X}","sha256":source[name]} for name in STARTS},
            "cases":samples*2,"mismatches":0,"branches":dict(counts),
            "five_word_delta_BC":"Car working state +0,+2,+4,+6,+8 (16-bit little endian)",
            "five_word_delta_DE":"Car working state +0A,+0C,+0E,+10,+12",
            "status_write":"SET bit6 at slot+7C",
            "overflow_escape":"CALL C,1689 if unsigned high(BC or DE) in [5,250]; gameplay semantics UNVERIFIED",
            "limitation":"One collision response subroutine; incoming correction calculation and full original damage/terrain still OPEN"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("master",type=Path)
    p.add_argument("--cases-per-endpoint",type=int,default=2500)
    p.add_argument("--out",type=Path,default=Path("local/engine-extraction/collision_geometry_translation.json"))
    args=p.parse_args()
    result=verify(args.master.read_bytes(),args.cases_per_endpoint)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
