#!/usr/bin/env python3
"""Original 1991 Indy Heat arcade six-slot scratch serializer parity.

Original master Z80:
  61CE–6299 (DI; saved SP; 48 POP HL / LD (scratch),HL; restored SP/EI)
  629A–6365 (DI; saved SP; 48 reversed LD HL,(scratch) / PUSH HL)
48 words = 96 bytes, exactly physical slot+00..+5F ↔ E72B..E78A.
The SIXTH auxiliary slot E500 is valid, even though only five racing
cars are driven. High 160 bytes of a slot are NEVER touched by these
two data transfers; original IX indexed routines handle those fields.

This checker compares a direct independent byte model with execution
of the original source-verified POP/PUSH opcode sequences using only the
owner's private, checksum-authenticated 1991 arcade ROM. It does not
claim to reconstruct CPU interrupt or callback schedule effects.
"""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
LOAD_SHA="080b1fa9f61bb98a35255ca33314852651863496214cb40c52046631979ec9b2"
SAVE_SHA="5003e0e0ff0dbf82e95c17ec02452ebc8ed73a2037b39368c2dc4c70994a7b03"
SCRATCH=0xE72B
SLOT_STARTS=tuple(0xE000+0x100*n for n in range(6))
RAM_BASE,RAM_LEN=0xE000,0x2000
COPIED_BYTES=96
WORDS=48


def _check(ram:bytes,slot:int)->None:
    if len(ram)!=RAM_LEN or slot not in SLOT_STARTS:
        raise ValueError("Full original master E000–FFFF memory and one of six 256-byte slots required")

def direct(ram:bytes,slot:int,loading:bool)->bytes:
    _check(ram,slot)
    source=(slot if loading else SCRATCH)-RAM_BASE
    target=(SCRATCH if loading else slot)-RAM_BASE
    out=bytearray(ram)
    out[target:target+COPIED_BYTES]=ram[source:source+COPIED_BYTES]
    return bytes(out)

def original_opcode_transfers(master:bytes,ram:bytes,slot:int,loading:bool)->bytes:
    """Replay each authentic POP/LD or LD/PUSH with original CPU stack direction.

    Original prologue/epilogue are independently signature-checked;
    stack/interrupt register bookkeeping is outside this byte model.
    """
    _check(ram,slot)
    if len(master)!=0x90000:raise ValueError("Original master ROM required")
    out=bytearray(ram)
    if loading:
        pc=0x61D4
        sp=slot
        for n in range(WORDS):
            if master[pc]!=0xE1 or master[pc+1]!=0x22:
                raise ValueError(f"Original POP/LD bytecode changed at {pc:04X}")
            address=master[pc+2]|(master[pc+3]<<8)
            if address!=SCRATCH+2*n:
                raise ValueError("Original scratch POP order changed")
            start=sp-RAM_BASE
            word=out[start]|out[start+1]<<8
            sp+=2
            dst=address-RAM_BASE
            out[dst],out[dst+1]=word&255,word>>8
            pc+=4
        if pc!=0x6294 or sp!=slot+0x60:
            raise ValueError("Original 48-word POP stage incomplete")
    else:
        pc=0x62A0
        sp=slot+0x60
        for n in range(WORDS):
            if master[pc]!=0x2A or master[pc+3]!=0xE5:
                raise ValueError(f"Original LD/PUSH bytecode changed at {pc:04X}")
            address=master[pc+1]|master[pc+2]<<8
            if address!=SCRATCH+2*(WORDS-1-n):
                raise ValueError("Original reversed scratch PUSH order changed")
            src=address-RAM_BASE
            word=out[src]|out[src+1]<<8
            sp-=2
            dst=sp-RAM_BASE
            out[dst],out[dst+1]=word&255,word>>8
            pc+=4
        if pc!=0x6360 or sp!=slot:
            raise ValueError("Original 48-word PUSH stage incomplete")
    return bytes(out)

def verify(master:bytes,cases:int=12000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Owner's privately checksum-verified original master required")
    if hashlib.sha256(master[0x61CE:0x629A]).hexdigest()!=LOAD_SHA:
        raise ValueError("Original 61CE source bytecode changed")
    if hashlib.sha256(master[0x629A:0x6366]).hexdigest()!=SAVE_SHA:
        raise ValueError("Original 629A source bytecode changed")
    if not 0<=cases<=100000:raise ValueError("Invalid original byte-model test budget")
    rng=Random(0x61CE);counts=Counter()
    for index in range(cases):
        slot=SLOT_STARTS[index%6]
        ram=rng.randbytes(RAM_LEN)
        for loading in (True,False):
            expect=direct(ram,slot,loading)
            machine=original_opcode_transfers(master,ram,slot,loading)
            if expect!=machine:
                raise AssertionError(f"Original six-slot serializer differs slot {slot:04X}, mode={loading}")
            counts["load" if loading else "save"]+=1
        # Every byte of the low 96-byte slot roundtrips after
        # LOAD followed by SAVE, regardless of old scratch contents.
        restored=direct(direct(ram,slot,True),slot,False)
        first=slot-RAM_BASE
        if restored[first:first+0x100]!=ram[first:first+0x100]:
            raise AssertionError("Original car record must roundtrip all 256 bytes")
        counts["roundtrip"]+=1
    return {"source":"Original master Z80 61CE–6299 / 629A–6365",
            "test_states":cases,"original_instruction_transfer_comparisons":cases*2,
            "roundtrip_checks":cases,"mismatches":0,
            "six_slot_addresses":[f"{x:04X}" for x in SLOT_STARTS],
            "original_low_bytes_copied":COPIED_BYTES,
            "original_high_bytes_preserved":160,
            "limitations":"CPU original DI/EI and callback scheduling separately validated, not simulated here"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_master",type=Path)
    p.add_argument("--cases",type=int,default=12000)
    args=p.parse_args()
    print(json.dumps(verify(args.private_master.read_bytes(),args.cases),indent=2))
