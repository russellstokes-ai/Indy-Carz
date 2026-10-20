#!/usr/bin/env python3
"""Original 1991 arcade master B86C-B883 conditional two-car recovery dispatch.

Decodes original CPU branch selection only, not unverified B884 effects.
B884 is an opaque, independently queued target and may have nonlocal exits.
Original source ROM is private; only safe mathematical logic is published.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from random import Random
import argparse

MASTER_HASH='521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7'
STAGE_HASH='ce97b9878481042b4fad94ba2488d32b6ec8b8b2b2335649655b1e06a9cdb746'
START,STOP,TARGET=0xB86C,0xB884,0xB884


def model(first:bytes,second:bytes)->tuple[int,...]:
    if len(first)!=256 or len(second)!=256:raise ValueError('Two original 256-byte slots required')
    # IX/IY point to slot+0x80, so original (IX/IY-4) is physical slot+0x7C.
    return tuple(i for i,s in enumerate((first,second)) if not (s[0x7C]&2))


def opcode(master:bytes,first:bytes,second:bytes)->tuple[int,...]:
    if len(master)!=0x90000 or len(first)!=256 or len(second)!=256:
        raise ValueError('Original master and two 0x100-byte slots required')
    slots=(first,second)
    ix,iy=0,1
    zero=False
    calls=[]
    pointers=[]
    pc=START
    for _ in range(20):
        op=master[pc]
        if op in (0xDD,0xFD):
            ext=master[pc+1]
            if ext==0xCB:
                if master[pc+2:pc+4]!=bytes.fromhex('fc4e'):
                    raise ValueError(f'Unexpected indexed original BIT at {pc:04X}')
                zero=not bool(slots[ix if op==0xDD else iy][0x7C]&2)
                pc+=4
            elif ext==0xE5:
                pointers.append(ix if op==0xDD else iy)
                pc+=2
            elif ext==0xE1:
                if op!=0xDD or not pointers:raise ValueError('Original IX stack imbalance')
                ix=pointers.pop();pc+=2
            else:raise ValueError(f'Unexpected indexed instruction {ext:02X}')
        elif op==0xCC:  # CALL Z, B884
            target=master[pc+1]|master[pc+2]<<8
            if target!=TARGET:raise ValueError('Unexpected original conditional contact target')
            if zero:calls.append(ix)  # Opaque target effects must be separately verified.
            pc+=3
        elif op==0xCD:  # CALL B884 with second car temporarily in IX
            target=master[pc+1]|master[pc+2]<<8
            if target!=TARGET:raise ValueError('Unexpected original contact target')
            calls.append(ix)
            pc+=3
        elif op==0xC0:  # RET NZ if second original status bit1 set
            pc+=1
            if not zero:
                if pointers or ix!=0 or iy!=1:raise ValueError('Original early RET pointer mismatch')
                return tuple(calls)
        elif op==0xC9:
            if pc!=STOP-1 or pointers or ix!=0 or iy!=1:
                raise ValueError('Original return/pointer mismatch')
            return tuple(calls)
        else:
            raise ValueError(f'Unexpected B86C opcode {op:02X} at {pc:04X}')
        if not START<=pc<STOP:raise ValueError(f'B86C escaped fixed stage at {pc:04X}')
    raise ValueError('B86C bounded instruction limit exceeded')


def verify(master:bytes)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_HASH:
        raise ValueError('Private checksum-verified original master ROM required')
    if hashlib.sha256(master[START:STOP]).hexdigest()!=STAGE_HASH:
        raise ValueError('Original B86C dispatcher opcode SHA mismatch')
    rng=Random(0xB86C)
    counts={'none':0,'first':0,'second':0,'both':0}
    for left in range(256):
        for right in range(256):
            first,second=bytearray(rng.randbytes(256)),bytearray(rng.randbytes(256))
            first[0x7C],second[0x7C]=left,right
            expected=model(bytes(first),bytes(second))
            observed=opcode(master,bytes(first),bytes(second))
            if observed!=expected:raise AssertionError(f'Original B86C mismatch status={left},{right}')
            counts[{(): 'none',(0,):'first',(1,):'second',(0,1):'both'}[observed]]+=1
    return {'original_source':'1991 Indy Heat arcade fixed master Z80 B86C-B883',
            'original_stage_sha256':STAGE_HASH,
            'exhaustive_status_pairs':65536,'mismatches':0,
            'opaque_B884_call_order_cases':counts,
            'scope':'exact conditional calls and IX restoration only; B884 side effects NOT modelled'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('master',type=Path)
    args=ap.parse_args()
    print(json.dumps(verify(args.master.read_bytes()),indent=2))
if __name__=='__main__':main()
