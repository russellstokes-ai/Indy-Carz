#!/usr/bin/env python3
"""Bounded original Indy Heat 1991 arcade master bank-3 racing signals.

Original-rom-gated opcode execution is independent of mathematical models.
All externally called routines stay opaque, never invented or conflated with
the racing engine. Original ROM bytes and private disassembly stay local.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from random import Random

MASTER_HASH="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
BANK3_BASE=0x28000
SIGNALS=(0x6C9B,0x6CC6,"cc6fa627ac747a2c81d37ba51d9beebae1a8885e04ab6495f813d45c19aac0f7")
GLOBAL=(0x6C62,0x6C84,"5c1f5fd4ef0a823ac34f3ac5dbe03f43ca31b1ca5f4854d14ef5bec9e18a1efc")
SERVICE=(0x6C84,0x6C9B,"fd5b8dd9f9a0fd487d19d21ae4dc9fb9b3aa6540ad4cb2b3c3e96bfab9fabe76")
FRAME=(0x624C,0x627C,"d81d8445b899a8a3066f7658de1ddc0ba6e253e0d67915655d3cd9af41886511")

def check_byte(x:int)->None:
    if not isinstance(x,int) or not 0<=x<=255:raise ValueError("Expected Z80 byte")

def race_event_model(status:int,b:int)->tuple[int,int,bool,str]:
    """Physical slot+77 event byte, A, zero flag, original event case.

    Bit0 outranks bit2 outranks bit1. If bit1 and B nonzero the returned
    zero flag is TRUE, which causes the external caller 7585 RET Z.
    """
    check_byte(status);check_byte(b)
    if status&1:return status&~1,1,False,"bit0"
    if status&4:return status&~4,1,False,"bit2"
    if status&2:
        return (status&~2,0,True,"bit1_b_nonzero") if b else (status&~2,255,False,"bit1_b_zero")
    return status,status,True,"no_pending_bit"

def race_event_opcode(bank:bytes,status:int,b:int)->tuple[int,int,bool,str]:
    """Interpret bounded ORIGINAL instructions at bank3 6C9B..6CC5."""
    check_byte(status);check_byte(b)
    a=0;zero=False;pc=SIGNALS[0];changed=status
    for _ in range(24):
        op=bank[pc]
        if op==0xDD:
            ext=bank[pc+1]
            if ext==0x7E:
                if bank[pc+2]!=0xF7:raise ValueError("Unexpected IX read")
                a=changed;pc+=3
            elif ext==0xCB:
                disp,code=bank[pc+2:pc+4]
                if disp!=0xF7 or code not in (0x86,0x96,0x8E):
                    raise ValueError("Unexpected original indexed reset")
                changed &=~(1<<{0x86:0,0x96:2,0x8E:1}[code]);pc+=4
            else:raise ValueError(f"Unexpected IX opcode {ext:02X}")
        elif op==0xCB:
            code=bank[pc+1]
            if code not in (0x47,0x57,0x4F):raise ValueError("Unexpected BIT")
            zero=not bool(a&(1<<{0x47:0,0x57:2,0x4F:1}[code]))
            pc+=2
        elif op==0x28:
            off=bank[pc+1]
            pc+=2+(off-256 if off>=128 else off) if zero else 2
        elif op==0x20:
            off=bank[pc+1]
            pc+=2+(off-256 if off>=128 else off) if not zero else 2
        elif op==0x3E:a=bank[pc+1];pc+=2
        elif op==0x78:a=b;pc+=1
        elif op==0xB7:zero=a==0;pc+=1
        elif op==0xF6:a|=bank[pc+1];zero=a==0;pc+=2
        elif op==0xAF:a=0;zero=True;pc+=1
        elif op in (0xC8,0xC9):
            if op==0xC8 and not zero:
                pc+=1;continue
            label={0x6CA9:"bit0",0x6CB5:"bit2",0x6CB8:"no_pending_bit",
                   0x6CC3:"bit1_b_zero",0x6CC5:"bit1_b_nonzero"}.get(pc)
            if label is None:raise ValueError(f"Unexpected original return {pc:04X}")
            return changed,a,zero,label
        else:raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
        if not SIGNALS[0]<=pc<SIGNALS[1]:raise ValueError("Event escaped original stage")
    raise ValueError("Original event instruction budget exceeded")

def global_gate_model(e603:int,flags:tuple[int,int,int])->dict:
    check_byte(e603)
    if len(flags)!=3:raise ValueError("Exactly first three racing slots")
    for v in flags:check_byte(v)
    if e603:return {"next_pc":0x556F,"e603":e603,"calls":[]}
    if flags[0]&flags[1]&flags[2]&1:
        return {"next_pc":0x556F,"e603":1,"calls":[0x105F]}
    return {"next_pc":0x1069,"e603":0,"calls":[]}

def global_gate_opcode(bank:bytes,e603:int,flags:tuple[int,int,int])->dict:
    global_gate_model(e603,flags)
    mem={0xE603:e603,0xE0B1:flags[0],0xE1B1:flags[1],0xE2B1:flags[2],
         0xE1B2:0xAB,0xE2B2:0xCD}
    a=h=l=0;z=False;calls=[];pc=GLOBAL[0]
    for _ in range(20):
        op=bank[pc]
        if op==0x3A:
            addr=bank[pc+1]|bank[pc+2]<<8
            if addr not in mem:raise ValueError("Unexpected RAM read")
            a=mem[addr];pc+=3
        elif op==0x2A:
            addr=bank[pc+1]|bank[pc+2]<<8
            if addr not in (0xE1B1,0xE2B1):raise ValueError("Unexpected word")
            l,h=mem[addr],mem[addr+1];pc+=3
        elif op==0xA5:a &= l;z=a==0;pc+=1
        elif op==0xB7:z=a==0;pc+=1
        elif op==0xCB:
            if bank[pc+1]!=0x47:raise ValueError("Unexpected BIT instruction")
            z=not bool(a&1);pc+=2
        elif op in (0xC2,0xCA,0xC3):
            addr=bank[pc+1]|bank[pc+2]<<8
            if addr not in (0x556F,0x1069):raise ValueError("Unexpected branch")
            jump=op==0xC3 or (op==0xC2 and not z) or (op==0xCA and z)
            pc=addr if jump else pc+3
        elif op==0xCD:
            addr=bank[pc+1]|bank[pc+2]<<8
            if addr!=0x105F:raise ValueError("Unexpected external CALL")
            calls.append(addr);pc+=3
        elif op==0x3E:a=bank[pc+1];pc+=2
        elif op==0x32:
            addr=bank[pc+1]|bank[pc+2]<<8
            if addr!=0xE603:raise ValueError("Unexpected RAM write")
            mem[addr]=a;pc+=3
        else:raise ValueError(f"Unexpected gate opcode {op:02X} at {pc:04X}")
        if pc in (0x556F,0x1069):
            return {"next_pc":pc,"e603":mem[0xE603],"calls":calls}
        if not GLOBAL[0]<=pc<GLOBAL[1]:raise ValueError("Gate escaped stage")
    raise ValueError("Global gate instruction budget exceeded")

def service_model(car_23:int,global_dc:int,car_1e:int)->dict:
    for v in (car_23,global_dc,car_1e):check_byte(v)
    if not car_23:return {"next":"return_6C88","car_1e":car_1e,"calls":[]}
    if global_dc:return {"next":"return_6C8D","car_1e":car_1e,"calls":[]}
    return {"next":"jump_103C","car_1e":car_1e&~1,
            "calls":[("CALL",0x103C),("CALL",0x103C),("JP",0x103C)]}

def service_opcode(bank:bytes,car_23:int,global_dc:int,car_1e:int)->dict:
    service_model(car_23,global_dc,car_1e)
    a=z=0;pc=SERVICE[0];state=car_1e;calls=[]
    for _ in range(15):
        op=bank[pc]
        if op==0xDD:
            ext=bank[pc+1]
            if ext==0x7E:
                if bank[pc+2]!=0x23:raise ValueError("Unexpected indexed source")
                a=car_23;pc+=3
            elif ext==0xCB:
                if bank[pc+2:pc+4]!=bytes.fromhex("1e86"):raise ValueError("Unexpected bit reset")
                state &=~1;pc+=4
            else:raise ValueError("Unexpected IX instruction")
        elif op==0x3A:
            if bank[pc+1:pc+3]!=bytes.fromhex("dce7"):raise ValueError("Unexpected global read")
            a=global_dc;pc+=3
        elif op==0xB7:z=(a==0);pc+=1
        elif op==0xC8:
            if z:return {"next":"return_6C88","car_1e":state,"calls":calls}
            pc+=1
        elif op==0xC0:
            if not z:return {"next":"return_6C8D","car_1e":state,"calls":calls}
            pc+=1
        elif op==0xCD:
            addr=bank[pc+1]|bank[pc+2]<<8
            if addr!=0x103C:raise ValueError("Unexpected external CALL")
            calls.append(("CALL",addr));pc+=3
        elif op==0xC3:
            addr=bank[pc+1]|bank[pc+2]<<8
            if addr!=0x103C:raise ValueError("Unexpected original tail")
            calls.append(("JP",addr))
            return {"next":"jump_103C","car_1e":state,"calls":calls}
        else:raise ValueError(f"Unexpected service opcode {op:02X} at {pc:04X}")
        if not SERVICE[0]<=pc<SERVICE[1]:raise ValueError("Service escaped")
    raise ValueError("Service instruction budget exceeded")

def frame_call_schedule(bank:bytes)->list[tuple[str,int,int|None,int|None]]:
    """Static exact CALL sites; external callbacks and their side effects opaque."""
    pc=FRAME[0];ix=None;hl=None;out=[]
    for _ in range(40):
        op=bank[pc]
        if op==0xDD and bank[pc+1]==0x21:
            ix=bank[pc+2]|bank[pc+3]<<8;pc+=4
        elif op==0x2A:
            addr=bank[pc+1]|bank[pc+2]<<8
            if addr not in (0xE094,0xE194,0xE294):raise ValueError("Unexpected callback source")
            hl=None;pc+=3
        elif op==0x21:
            hl=bank[pc+1]|bank[pc+2]<<8;pc+=3
        elif op==0xCD:
            addr=bank[pc+1]|bank[pc+2]<<8
            if addr not in (0x1078,0x18C0,0x6C8E,0x1087):raise ValueError("Unexpected frame call")
            out.append(("CALL",addr,ix,hl));pc+=3
        else:raise ValueError(f"Unexpected frame opcode {op:02X} at {pc:04X}")
        if pc==FRAME[1]:return out
        if not FRAME[0]<=pc<FRAME[1]:raise ValueError("Frame block escaped")
    raise ValueError("Frame instruction budget exceeded")

def bank_view(master:bytes)->bytes:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_HASH:
        raise ValueError("Checksum-verified original master Z80 required")
    bank=bytearray(master[:0xE000]);bank[0x2000:0xA000]=master[BANK3_BASE:BANK3_BASE+0x8000]
    for lo,hi,digest in (SIGNALS,GLOBAL,SERVICE,FRAME):
        if hashlib.sha256(bank[lo:hi]).hexdigest()!=digest:
            raise ValueError(f"Original Z80 opcode fingerprint mismatch at {lo:04X}")
    return bytes(bank)

def verify(master:bytes,gate_samples:int=16000,service_samples:int=4096)->dict:
    bank=bank_view(master);events={}
    for status in range(256):
        for b in range(256):
            expected=race_event_model(status,b)
            actual=race_event_opcode(bank,status,b)
            if expected!=actual:raise AssertionError(f"Original race event mismatch {status},{b}")
            events[actual[3]]=events.get(actual[3],0)+1
    rng=Random(0x6C9B);gate_counts={}
    for n in range(gate_samples):
        e603=rng.randrange(256) if n%5==0 else 0
        flags=tuple(rng.randrange(256) for _ in range(3))
        expected=global_gate_model(e603,flags)
        actual=global_gate_opcode(bank,e603,flags)
        if expected!=actual:raise AssertionError(f"Original gate mismatch {n}")
        key=f'{actual["next_pc"]:04X}'
        gate_counts[key]=gate_counts.get(key,0)+1
    services={}
    for n in range(service_samples):
        a=rng.randrange(256) if n%3 else 0
        b=rng.randrange(256) if n%5 else 0
        c=rng.randrange(256)
        expected=service_model(a,b,c)
        actual=service_opcode(bank,a,b,c)
        if expected!=actual:raise AssertionError(f"Original service mismatch {n}")
        services[actual["next"]]=services.get(actual["next"],0)+1
    seq=frame_call_schedule(bank)
    required=[("CALL",0x1078,None,None)]
    for ix in (0xE080,0xE180,0xE280):
        required.extend((("CALL",0x18C0,ix,None),("CALL",0x6C8E,ix,None)))
    required.append(("CALL",0x1087,0xE280,2))
    if seq!=required:raise AssertionError("Original frame call order changed")
    return {"source":"Original 1991 arcade master Z80 bank3",
            "event_opcode_cases":65536,"gate_opcode_cases":gate_samples,
            "service_opcode_cases":service_samples,"mismatches":0,
            "event_branches":events,"gate_exits":gate_counts,
            "service_branches":services,"frame_call_sequence":seq,
            "limitations":"External calls 103C/105F/1078/1087/18C0 and their side effects unresolved; no live frame parity"}

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("--gate-samples",type=int,default=16000)
    parser.add_argument("--service-samples",type=int,default=4096)
    opts=parser.parse_args()
    print(json.dumps(verify(opts.master.read_bytes(),opts.gate_samples,opts.service_samples),indent=2))

if __name__=="__main__":main()
