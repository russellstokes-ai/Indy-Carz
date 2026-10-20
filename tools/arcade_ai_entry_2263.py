#!/usr/bin/env python3
"""Original Indy Heat 1991 AI entry: master bank0 2263–22B7.

Instruction-level bounded original ROM parity, composing verified 22B8–2360
linked countdown and event chain. Calls 31E6/1190 and tail JP 021A are
unresolved external actions; they must never be fabricated as working AI.
Original copyrighted ROM bytes/disassembly remain private.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from random import Random
import json,argparse
from arcade_ai_linked_countdown import independent as linked_model,opcode as linked_opcode

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
START,END=0x2263,0x22B8
STAGE_SHA="c0b031e03d5c3d6b74fb3b456d2879d7530ceeca04318982e875d171fb23fafd"

class UnverifiedAIExternal(ValueError):pass

def validate(car:bytes,e603:int,e627:int,ed59:int,
             linked_0e:int,linked_20:int,e642:int,e95b:int)->None:
    if (len(car)!=256 or any(not 0<=x<256 for x in
           (e603,e627,linked_0e,linked_20)) or
           any(not 0<=x<65536 for x in (ed59,e642,e95b))):
        raise ValueError("Original car and bounded 8/16-bit Z80 globals required")

def independent(car:bytes,e603:int,e627:int,ed59:int,
                linked_0e:int,linked_20:int,e642:int,e95b:int)->dict:
    validate(car,e603,e627,ed59,linked_0e,linked_20,e642,e95b)
    out=bytearray(car)
    if out[0xB3]&2:
        return {"exit":"original_ret_nz","car":bytes(out),"linked_0e":linked_0e}
    if e603==0 and out[0x91]>=(ed59&255) and out[0xA3]==0:
        raise UnverifiedAIExternal("Original CALL 31E6 remains unverified")
    target=(((e627&14)>>1)-3)&255
    if out[0x7D]!=target:
        return {"exit":"opaque_jump_021A_no_update","car":bytes(out),"linked_0e":linked_0e}
    if out[0x7D]==4 and not(e627&16):
        raise UnverifiedAIExternal("Original CALL 1190 reassigns IX; not recovered")
    out[0xD7]=(out[0xF7]>>1)&0x7E
    result=linked_model(bytes(out),linked_0e,linked_20,e642,e95b)
    return {"exit":"verified_ai_path_then_opaque_021A","car":result["car"],
            "linked_0e":result["linked_0e"],"event_reason":result["reason"]}

def opcode(master:bytes,car:bytes,e603:int,e627:int,ed59:int,
           linked_0e:int,linked_20:int,e642:int,e95b:int)->dict:
    validate(car,e603,e627,ed59,linked_0e,linked_20,e642,e95b)
    if len(master)!=0x90000:raise ValueError("Original 0x90000 master ROM required")
    out=bytearray(car)
    ram={0xE603:e603,0xE627:e627,0xED59:ed59&255,0xED5A:ed59>>8}
    a=b=c=h=l=0;z=carry=False;pc=START;linked_result=None
    for _ in range(75):
        op=master[pc]
        if op==0xDD:
            ext=master[pc+1]
            if ext==0xCB:
                disp,code=master[pc+2:pc+4]
                if (disp,code)!=(0x33,0x4E):
                    raise ValueError("Unexpected original indexed BIT")
                z=not bool(out[0xB3]&2);pc+=4
            elif ext==0x7E:
                disp=master[pc+2]
                offset={0x11:0x91,0x23:0xA3,0xFD:0x7D,0x77:0xF7}.get(disp)
                if offset is None:raise ValueError("Unknown original IX source")
                a=out[offset];pc+=3
            elif ext==0xBE:
                if master[pc+2]!=0xFD:raise ValueError("Unexpected original indexed CP")
                z=a==out[0x7D];carry=a<out[0x7D];pc+=3
            elif ext==0x96:
                if master[pc+2]!=0xBB:raise ValueError("Unexpected original indexed SUB")
                a=(a-out[0x3B])&255;z=a==0;pc+=3
            elif ext==0x77:
                if master[pc+2]!=0x57:raise ValueError("Unexpected IX write")
                out[0xD7]=a;pc+=3
            else:raise ValueError(f"Unknown indexed Z80 opcode {ext:02X}")
        elif op==0xC0:
            if not z:
                if pc!=0x2267:raise ValueError("Unexpected RET NZ")
                return {"exit":"original_ret_nz","car":bytes(out),"linked_0e":linked_0e}
            pc+=1
        elif op==0x3A:
            addr=master[pc+1]|(master[pc+2]<<8)
            if addr not in ram:raise ValueError("Unexpected original global byte source")
            a=ram[addr];pc+=3
        elif op==0x2A:
            addr=master[pc+1]|(master[pc+2]<<8)
            if addr!=0xED59:raise ValueError("Unexpected original global word source")
            l,h=ram[addr],ram[addr+1];pc+=3
        elif op==0xB7:z=a==0;carry=False;pc+=1
        elif op==0xBD:z=a==l;carry=a<l;pc+=1
        elif op==0xFE:
            n=master[pc+1];z=a==n;carry=a<n;pc+=2
        elif op==0xE6:a &= master[pc+1];z=a==0;carry=False;pc+=2
        elif op==0xCB:
            if master[pc+1]!=0x3F:raise ValueError("Unexpected original shift")
            carry=bool(a&1);a>>=1;z=a==0;pc+=2
        elif op==0xD6:
            n=master[pc+1];z=a==n;carry=a<n;a=(a-n)&255;pc+=2
        elif op in (0x20,0x38):
            delta=master[pc+1];delta=delta-256 if delta>=128 else delta
            take=(op==0x20 and not z or op==0x38 and carry)
            pc+=2+(delta if take else 0)
        elif op==0xC2:
            target=master[pc+1]|(master[pc+2]<<8)
            if target!=0x22B5:raise ValueError("Unexpected JP NZ target")
            pc=target if not z else pc+3
        elif op==0xCC:
            target=master[pc+1]|(master[pc+2]<<8)
            if target!=0x31E6:raise ValueError("Unexpected original CALL Z")
            if z:raise UnverifiedAIExternal("Original CALL 31E6 remains unverified")
            pc+=3
        elif op==0xCD:
            target=master[pc+1]|(master[pc+2]<<8)
            if target==0x1190:raise UnverifiedAIExternal("Original CALL 1190 reassigns IX; not recovered")
            if target!=0x22B8:raise ValueError("Unknown original AI event call")
            linked_result=linked_opcode(master,bytes(out),linked_0e,linked_20,e642,e95b)
            out=bytearray(linked_result["car"]);pc+=3
        elif op==0x79:a=c;pc+=1
        elif op==0x4F:c=a;pc+=1
        elif op==0x47:b=a;pc+=1
        elif op==0xAF:a=0;z=True;carry=False;pc+=1
        elif op==0x3E:a=master[pc+1];pc+=2
        elif op==0xC3:
            target=master[pc+1]|(master[pc+2]<<8)
            if target!=0x021A or pc!=0x22B5:
                raise ValueError("Unexpected original AI tail jump")
            if linked_result:
                return {"exit":"verified_ai_path_then_opaque_021A","car":bytes(out),
                        "linked_0e":linked_result["linked_0e"],
                        "event_reason":linked_result["reason"]}
            return {"exit":"opaque_jump_021A_no_update",
                    "car":bytes(out),"linked_0e":linked_0e}
        else:raise ValueError(f"Unknown original AI opcode {op:02X} at {pc:04X}")
        if not START<=pc<END:raise ValueError("Original AI entry escaped verified stage")
    raise ValueError("Original AI entry instruction budget exceeded")

def verify(master:bytes,cases:int=100000)->dict:
    if (len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA
            or sha256(master[START:END]).hexdigest()!=STAGE_SHA):
        raise ValueError("Original master 2263 stage checksum mismatch")
    if not 0<=cases<=250000:raise ValueError("Invalid case budget")
    rng=Random(0x2263);verified={};unknown={}
    for i in range(cases):
        car=bytearray(rng.randbytes(256))
        car[0xB3]=(car[0xB3]&~2)|(2 if i%10==0 else 0)
        e603=0 if i%5 else rng.choice((1,255))
        e627=rng.randrange(256)
        if i%2==0:car[0x7D]=(((e627&14)>>1)-3)&255
        if i%13==0:car[0xA3]=0;car[0x91]=200
        ed59=rng.choice((0,100,255,rng.randrange(65536)))
        linked_timer=rng.choice((0,1,32,129,255))
        linked_val=rng.choice((0,2,3,255))
        args=(bytes(car),e603,e627,ed59,linked_timer,linked_val,0xF010,0xC040)
        try:expected=independent(*args)
        except UnverifiedAIExternal as exc:
            reason=str(exc);unknown[reason]=unknown.get(reason,0)+1
            try:opcode(master,*args)
            except UnverifiedAIExternal:continue
            raise AssertionError(f"Original refused case {i} did not refuse in Z80")
        observed=opcode(master,*args)
        if expected!=observed:
            raise AssertionError(f"Original AI entry mismatch {i}: {expected['exit']} {observed['exit']}")
        verified[observed["exit"]]=verified.get(observed["exit"],0)+1
    return {"source":"Original arcade bank0 2263-2360 (bounded original call paths)",
            "input_cases":cases,"verified_case_counts":verified,"unverified_external_call_cases":unknown,
            "mismatches":0,"limit":"Original 31E6,1190,021A effects and complete AI remain OPEN"}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path);parser.add_argument("--cases",type=int,default=100000)
    a=parser.parse_args();print(json.dumps(verify(a.master.read_bytes(),a.cases),indent=2))
