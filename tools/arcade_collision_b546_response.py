#!/usr/bin/env python3
"""Original arcade B546-B5AB two-vehicle correction, opcode parity.

Bounded B546..B5AB Z80 execution, using separately-verified B985/BA20
helpers. Valid only for entry after CP C0 sets carry=1; other incoming
flags, exceptional $1689 path and full impact/damage model unverified.
Original arcade ROM image remains private and is not committed.
"""
from __future__ import annotations
import hashlib
import json
import argparse
from pathlib import Path
from random import Random
from collections import Counter
from arcade_collision_geometry_push import emulate as push_emulate, model as push_model, u16, MASTER_SHA

START=0xB546
STOP=0xB5AC
STAGE_SHA="bfbc581e4e804ecc7a1de682b3db94e04602fd5420e4252ddfa0a93aa6c52eb4"

def asr16(value:int)->int:
    signed=value-65536 if value&0x8000 else value
    return (signed>>1)&65535

def model(first:bytes,second:bytes,counter:int)->tuple[str,bytes,bytes,int]:
    if len(first)!=256 or len(second)!=256 or not 0<=counter<=255:
        raise ValueError("Invalid car slots / counter")
    previous=1  # carry from original CP C0 at B541
    a,b=first,second
    counter=(counter+1)&255
    for slot,label in ((0,"IX"),(1,"IY")):
        v=a if slot==0 else b
        if v[0x7c]&2:
            if slot==1:
                return "second_skipped",a,b,counter
            continue
        x=(u16(v,0x1e)-u16(v,0)-previous)&65535
        bc=asr16(x)
        y=(u16(v,0x28)-u16(v,0x0a)-(x&1))&65535
        de=asr16(y)
        status,changed=push_model(v,bc,de)
        if status!="applied":
            return label+":"+status,a,b,counter
        # ADD HL,DE in final translated word supplies carry to the next
        # SBC; original B985 leaves carry unchanged in its final SET/RET.
        previous=int(u16(v,0x12)+de>65535)
        if slot==0:a=changed
        else:b=changed
    return "applied",a,b,counter

def original(master:bytes,first:bytes,second:bytes,counter:int)->tuple[str,bytes,bytes,int]:
    if len(master)!=0x90000 or any(len(s)!=256 for s in (first,second)):
        raise ValueError("Original arcade ROM and slot dimensions required")
    if not 0<=counter<=255:raise ValueError("Invalid collision event counter")
    a=0;b=c=d=e=h=l=0
    ix=bytearray(first);iy=bytearray(second)
    z=False;carry=1
    pc=START
    for _ in range(75):
        op=master[pc]
        if op==0x3A:  # LD A,(E926)
            dest=u16(master,pc+1)
            if dest!=0xE926:raise ValueError("Unrecognised original global")
            a=counter;pc+=3
        elif op==0x3C:  # INC A
            a=(a+1)&255;z=a==0;pc+=1
        elif op==0x32:  # LD (E926),A
            if u16(master,pc+1)!=0xE926:raise ValueError("Unexpected global write")
            counter=a;pc+=3
        elif op in (0xDD,0xFD):  # IX / IY car-state fields
            which=ix if op==0xDD else iy
            ext=master[pc+1]
            if ext==0xCB: # BIT 1,(IX/IY-4); carry is preserved
                disp,bitop=master[pc+2:pc+4]
                if (disp,bitop)!=(0xFC,0x4E):raise ValueError("Unexpected indexed bit test")
                z=not bool(which[0x7c]&2)
                pc+=4
            else:
                off=(master[pc+2]-0x80)&255
                if ext==0x66:h=which[off]
                elif ext==0x6E:l=which[off]
                elif ext==0x56:d=which[off]
                elif ext==0x5E:e=which[off]
                else:raise ValueError(f"Unexpected Z80 indexed opcode {ext:02X}")
                pc+=3
        elif op==0xED:  # SBC HL,DE with preserved carry
            if master[pc+1]!=0x52:raise ValueError("Expected SBC HL,DE")
            val=(h<<8|l)-(d<<8|e)-carry
            carry=int(val<0)
            val&=65535;h,l=val>>8,val&255
            pc+=2
        elif op==0xCB:
            ext=master[pc+1]
            if ext==0x2C: # SRA H
                carry=h&1;h=(h>>1)|(h&0x80)
            elif ext==0x1D: # RR L
                old=l;l=(l>>1)|(carry<<7);carry=old&1
            else:raise ValueError(f"Unexpected shift opcode {ext:02X}")
            pc+=2
        elif op==0x44:b=h;pc+=1
        elif op==0x4D:c=l;pc+=1
        elif op==0xEB:h,l,d,e=d,e,h,l;pc+=1
        elif op==0x20: # JR NZ
            rel=master[pc+1];rel=rel-256 if rel>=128 else rel
            pc+=2+(rel if not z else 0)
        elif op==0xC0: # RET NZ
            if not z:return "second_skipped",bytes(ix),bytes(iy),counter
            pc+=1
        elif op==0xCD: # CALL B985
            dest=u16(master,pc+1)
            if dest!=0xB985:raise ValueError(f"Unexpected original target {dest:04X}")
            delta_bc=b<<8|c;delta_de=d<<8|e
            old=bytes(ix)
            state,after,_=push_emulate(master,old,delta_bc,delta_de,"IX")
            if state!="applied":return "IX:"+state,bytes(ix),bytes(iy),counter
            ix=bytearray(after)
            carry=int(u16(old,0x12)+delta_de>65535)
            pc+=3
        elif op==0xC3: # tail-call BA20
            dest=u16(master,pc+1)
            if dest!=0xBA20:raise ValueError("Unexpected tail-call destination")
            state,after,_=push_emulate(master,bytes(iy),b<<8|c,d<<8|e,"IY")
            if state!="applied":return "IY:"+state,bytes(ix),bytes(iy),counter
            return "applied",bytes(ix),after,counter
        else:
            raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
        if not START<=pc<STOP:raise ValueError(f"Unexpected B546 branch {pc:04X}")
    raise ValueError("B546 instruction budget exceeded")

def verify(master:bytes,cases=16000)->dict:
    if hashlib.sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Private checksum-verified arcade master required")
    digest=hashlib.sha256(master[START:STOP]).hexdigest()
    if digest!=STAGE_SHA:
        raise ValueError("Original B546 branch instruction bytes changed")
    if not 0<=cases<=100000:
        raise ValueError("Invalid case count")
    rng=Random(0xB546)
    counts=Counter()
    for i in range(cases):
        slots=[]
        for _ in range(2):
            v=bytearray(rng.randbytes(256))
            # Current vs prior positions are sampled with modest differences.
            for base,prev in ((0,0x1e),(0x0a,0x28)):
                orig=rng.randrange(65536)
                v[base:base+2]=orig.to_bytes(2,"little")
                diff=rng.randrange(-1800,1801)
                v[prev:prev+2]=((orig+diff)&65535).to_bytes(2,"little")
            if i%4==1:v[0x7c]|=2
            elif i%4==2:v[0x7c]&=~2
            slots.append(bytes(v))
        n=rng.randrange(256)
        expected=model(*slots,n)
        observed=original(master,*slots,n)
        if expected!=observed:
            raise AssertionError(f"Original collision response mismatch #{i} expected={expected[0]} got={observed[0]}")
        counts[observed[0]]+=1
    return {"source":"original arcade master fixed B546..B5AB with B985/BA20 subroutines",
            "stage_sha256":digest,"opcode_cases":cases,"mismatches":0,"outcomes":dict(counts),
            "incoming_carry":"1 from CP C0 only for the identified B546 entry",
            "first_translation":"half(previous-current-incoming carry) with 16-bit arithmetic shift",
            "second_axis_carry":"borrow from final bit of first 16-bit arithmetic right shift",
            "intercar_carry":"outgoing C from final IX geometry ADD HL,DE flows into IY first SBC",
            "limits":"Full collision impulse, high-delta trap, sound/damage and other entry flags remain unresolved"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("master",type=Path)
    p.add_argument("--cases",type=int,default=16000)
    p.add_argument("--out",type=Path,default=Path("local/engine-extraction/collision_b546_branch_parity.json"))
    a=p.parse_args();r=verify(a.master.read_bytes(),a.cases)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2))
