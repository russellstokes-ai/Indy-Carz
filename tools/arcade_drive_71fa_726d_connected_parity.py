#!/usr/bin/env python3
"""Verify complete bounded original Z80 driving sequence 71FA→7225→7245.

Composes three independently reconstructed arithmetic stages and challenges
the combined state outputs with the ORIGINAL instruction interpreters:
 - 71FA..7224: signed XROM accumulation / nonlocal CALL PE 1689
 - 7225..7244: signed 16-bit motion sign-crossing clamp
 - 7245..726C: signed cosine/XROM motion projection into E933
All ROM/XROM bytes remain private and never belong in public GitHub.

This is a verified contiguous driving calculation, NOT entire original
acceleration, tyre friction, turbo, AI, steering scheduling or game physics.
"""
from __future__ import annotations
import argparse,json
from hashlib import sha256
from random import Random
from collections import Counter
from pathlib import Path

from arcade_drive_71fa_xrom_accumulator import (
    independent as first_model,
    original_opcodes as first_machine,
    MASTER_SHA,XROM_SHA
)
from arcade_velocity_sign_gate_7225 import (
    independent as clamp_model,
    original_opcodes as clamp_machine
)
from arcade_drive_7245_heading_projection import (
    independent as projection_model,
    original_z80 as projection_machine
)

OUT_PC=0x726D
EXCEPTION_PC=0x1689


def _validate(c:int,e933:int,de:int,e76b:int,e768:int,e769:int)->None:
    if not (0<=c<256 and 0<=e933<65536 and 0<=de<65536
            and 0<=e76b<65536 and 0<=e768<256 and 0<=e769<65536):
        raise ValueError("One original 8-bit C, one 8-bit heading, four 16-bit words required")


def independent(c:int,e933:int,de:int,e76b:int,e768:int,e769:int)->dict:
    _validate(c,e933,de,e76b,e768,e769)
    result=first_model(c,e933,de)
    if result["exit"]=="external_1689":
        return {"complete":False,"next_pc":EXCEPTION_PC,
                "e76b":e76b,"e933":e933,
                "path":"external_1689","projection":None}
    motion=clamp_model(e76b,result["de"])
    projection=projection_model(e768,e769,motion["de_after"])
    return {"complete":True,"next_pc":OUT_PC,
            "e76b":motion["stored_e76b"],"e933":projection["e933"],
            "path":result["exit"]+"/"+motion["branch"],
            "projection":projection}


def original_z80(master:bytes,xrom:bytes,c:int,e933:int,de:int,
                 e76b:int,e768:int,e769:int)->dict:
    _validate(c,e933,de,e76b,e768,e769)
    original_first=first_machine(master,xrom,c,e933,de)
    if original_first["exit"]=="external_1689":
        return {"complete":False,"next_pc":EXCEPTION_PC,
                "e76b":e76b,"e933":e933,
                "path":"external_1689","projection":None}
    original_motion=clamp_machine(master,e76b,original_first["de"])
    original_projection=projection_machine(
        master,xrom,e768,e769,original_motion["de_after"])
    if (original_first["next_pc"]!=0x7225 or
        original_motion["next_pc"]!=0x7245 or
        original_projection["next_pc"]!=OUT_PC):
        raise ValueError("Original Z80 CPU chain lost one of its checked boundaries")
    return {"complete":True,"next_pc":OUT_PC,
            "e76b":original_motion["stored_e76b"],
            "e933":original_projection["e933"],
            "path":original_first["exit"]+"/"+original_motion["branch"],
            "projection":original_projection}


def verify(master:bytes,xrom:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authentic checksum-verified private arcade master required")
    if len(xrom)!=0x40000 or sha256(xrom).hexdigest()!=XROM_SHA:
        raise ValueError("Authentic checksum-verified private arcade XROM required")
    if not 0<=cases<=250000:raise ValueError("Original sequence test budget outside validated domain")
    rng=Random(0x726D);branches=Counter()
    for i in range(cases):
        c=rng.choice((0,0,1,127,128,255,rng.randrange(256)))
        e933=rng.choice((0,65535,32767,32768,rng.randrange(65536)))
        de=rng.choice((0,65535,32767,32768,rng.randrange(65536)))
        e76b=rng.choice((0,65535,32767,32768,rng.randrange(65536)))
        e768=rng.randrange(256)
        e769=rng.randrange(65536)
        inputs=(c,e933,de,e76b,e768,e769)
        expected=independent(*inputs)
        actual=original_z80(master,xrom,*inputs)
        if expected!=actual:
            diff={k:(expected.get(k),actual.get(k))
                  for k in expected if expected.get(k)!=actual.get(k)}
            raise AssertionError(f"Original contiguous Z80 update differs at case {i}: {diff}")
        branches[expected["path"]]+=1
    return {"source":"Authentic original 1991 arcade fixed master Z80 71FA-726C",
            "connected_motion_cases":cases,"mismatches":0,
            "exit_branch_counts":dict(sorted(branches.items())),
            "instruction_regions":["71FA-7224","7225-7244","7245-726C"],
            "normal_continuation":"726D",
            "nonlocal_exception":"1689 (no normal driving continuation)",
            "scope":"Three original driving subroutines connected; full physics inputs and scheduling still open"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_master",type=Path)
    parser.add_argument("original_xrom",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    args=parser.parse_args()
    print(json.dumps(verify(args.original_master.read_bytes(),
                            args.original_xrom.read_bytes(),args.cases),indent=2))
