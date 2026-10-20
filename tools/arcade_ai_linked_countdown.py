#!/usr/bin/env python3
"""Original 1991 arcade AI 22B8–230A linked countdown and positional gate.

Separately verified original Z80 instructions and an independent state model,
then composes 230B–2360 (arcade_ai_pending_event_rules.py). Original helper
1783 resolves an IY record pointer; the linked byte observations are
controlled inputs, NOT invented live-MAME values. Do not commit ROM bytes.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from random import Random
import argparse,json
from arcade_ai_pending_event_rules import independent as pending_model,opcode as pending_opcode

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
START,STOP=0x22B8,0x230B
STAGE_SHA="f84385302534c1e87b5d1f3c2f09f373b29e384d8e2454f82d0f6bada034bd55"

BIT4_7E=0xFE    # physical original car byte: IX+7E
BIT4_31=0xB1    # IX+31
BIT7_32=0xB2    # IX+32
FIRST_AXIS=0x0B # IX-75
SECOND_AXIS=0x01# IX-7F
GATE_5C=0xDC   # IX+5C
PENDING=0x77   # IX-09

def validate(slot:bytes,linked_0e:int,linked_20:int,e642:int,e95b:int)->None:
    if (len(slot)!=256 or any(not 0<=x<=255 for x in (linked_0e,linked_20))
            or any(not 0<=x<=65535 for x in (e642,e95b))):
        raise ValueError("Original 256-byte car, two linked bytes, two 16-bit bounds required")

def independent(slot:bytes,linked_0e:int,linked_20:int,e642:int,e95b:int)->dict:
    validate(slot,linked_0e,linked_20,e642,e95b)
    car=bytearray(slot)
    if (car[BIT4_7E]&16 and linked_20==3 and not(car[BIT4_31]&16)
            and not(car[BIT7_32]&128)):
        car[PENDING]|=2
        return {"reason":"forced_event_bit1","car":bytes(car),"linked_0e":0,"linked_changed":True}

    countdown=(linked_0e-1)&255
    if not countdown&128:
        return {"reason":"timer_active","car":bytes(car),"linked_0e":countdown,"linked_changed":True}

    x,y=car[FIRST_AXIS],car[SECOND_AXIS]
    if ((e642&255)<=x<(e642>>8) and (e95b&255)<=y<(e95b>>8) and car[GATE_5C]&2):
        car[PENDING]|=2
        return {"reason":"bounded_gate_event_bit1","car":bytes(car),
                "linked_0e":linked_0e,"linked_changed":False}
    branch,after=pending_model(bytes(car),linked_20)
    return {"reason":"fallback_"+branch,"car":after,
            "linked_0e":linked_0e,"linked_changed":False}

def opcode(master:bytes,slot:bytes,linked_0e:int,linked_20:int,e642:int,e95b:int)->dict:
    """Interpret the real original master Z80 22B8–230A only.

    Interpret original 1783 CALL as already-verified pointer resolution.
    Tail 230B is independently opcode-verified by its own strict interpreter.
    """
    validate(slot,linked_0e,linked_20,e642,e95b)
    if len(master)!=0x90000:raise ValueError("Original master must be 0x90000 bytes")
    car=bytearray(slot)
    linked={0x0E:linked_0e,0x20:linked_20}
    ram={0xE642:e642,0xE95B:e95b}
    a=h=l=0;carry=zero=sign=False;pc=START;iy_stack=[];linked_changed=False
    for _ in range(100):
        op=master[pc]
        if op==0xFD:
            ext=master[pc+1]
            if ext==0xE5:iy_stack.append(1);pc+=2
            elif ext==0xE1:
                if not iy_stack:raise ValueError("Original POP IY underflow")
                iy_stack.pop();pc+=2
            elif ext in (0x7E,0x77,0x36):
                offset=master[pc+2]
                if offset not in (0x0E,0x20):raise ValueError("Unexpected linked-state byte")
                if ext==0x7E:a=linked[offset];pc+=3
                elif ext==0x77:
                    linked[offset]=a;linked_changed=True;pc+=3
                else:
                    linked[offset]=master[pc+3];linked_changed=True;pc+=4
            else:raise ValueError(f"Unexpected indexed IY opcode {ext:02X}")
        elif op==0xDD:
            ext=master[pc+1]
            if ext==0xCB:
                disp,code=master[pc+2:pc+4]
                if disp==0x7E and code==0x66:zero=not bool(car[BIT4_7E]&16)
                elif disp==0x31 and code==0x66:zero=not bool(car[BIT4_31]&16)
                elif disp==0x32 and code==0x7E:zero=not bool(car[BIT7_32]&128)
                elif disp==0x5C and code==0x4E:zero=not bool(car[GATE_5C]&2)
                elif disp==0xF7 and code==0xCE:car[PENDING]|=2
                else:raise ValueError(f"Unexpected IX status opcode {code:02X}")
                pc+=4
            elif ext==0x7E:
                disp=master[pc+2]
                if disp==0x8B:a=car[FIRST_AXIS]
                elif disp==0x81:a=car[SECOND_AXIS]
                else:raise ValueError("Unexpected original coordinate source")
                pc+=3
            else:raise ValueError(f"Unexpected IX opcode {ext:02X}")
        elif op==0xCD:
            target=master[pc+1]|(master[pc+2]<<8)
            if target!=0x1783 or len(iy_stack)!=1:
                raise ValueError("Unexpected original linked pointer helper")
            pc+=3
        elif op==0x2A:
            addr=master[pc+1]|(master[pc+2]<<8)
            if addr not in ram:raise ValueError("Unexpected original bound source")
            word=ram[addr];l,h=word&255,word>>8;pc+=3
        elif op==0xFE:
            n=master[pc+1];zero=a==n;carry=a<n;sign=bool((a-n)&128);pc+=2
        elif op in (0xBC,0xBD):
            other=h if op==0xBC else l
            carry=a<other;zero=a==other;sign=bool((a-other)&128);pc+=1
        elif op==0x3D:
            a=(a-1)&255;zero=a==0;sign=bool(a&128);pc+=1
        elif op in (0x20,0x28,0x30,0x38,0x18):
            delta=master[pc+1];delta=delta-256 if delta>=128 else delta
            take=(op==0x18 or op==0x20 and not zero or op==0x28 and zero
                  or op==0x30 and not carry or op==0x38 and carry)
            pc+=2+(delta if take else 0)
        elif op in (0xC2,0xD2,0xFA):
            target=master[pc+1]|(master[pc+2]<<8)
            take=(op==0xC2 and not zero or op==0xD2 and not carry or op==0xFA and sign)
            pc=target if take else pc+3
        elif op==0xB7:zero=a==0;carry=False;sign=bool(a&128);pc+=1
        elif op==0xC9:
            if pc!=0x22EA or iy_stack:raise ValueError("Unexpected original early return")
            return {"reason":"timer_active","car":bytes(car),
                    "linked_0e":linked[0x0E],"linked_changed":linked_changed}
        if pc==0x2336:
            if iy_stack:raise ValueError("Original event escaped with saved IY")
            car[PENDING]|=2
            return {"reason":"forced_event_bit1" if linked_changed else "bounded_gate_event_bit1",
                    "car":bytes(car),"linked_0e":linked[0x0E],"linked_changed":linked_changed}
        if pc==STOP:
            if iy_stack:raise ValueError("Original tail with saved IY")
            branch,after=pending_opcode(master,bytes(car),linked[0x20])
            return {"reason":"fallback_"+branch,"car":after,
                    "linked_0e":linked[0x0E],"linked_changed":linked_changed}
        if not START<=pc<STOP:
            raise ValueError(f"Original AI stage escaped at {pc:04X}")
    raise ValueError("Original AI wrapper instruction budget exceeded")

def verify(master:bytes,cases:int=100000)->dict:
    if (len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA
            or sha256(master[START:STOP]).hexdigest()!=STAGE_SHA):
        raise ValueError("Private checksum-matched original AI program required")
    if not 0<=cases<=250000:raise ValueError("Invalid case budget")
    rng=Random(0x22B8);hist={}
    for k in range(cases):
        car=bytearray(rng.randbytes(256))
        car[BIT4_7E]=(car[BIT4_7E]&~16)|(16 if k&1 else 0)
        car[BIT4_31]=(car[BIT4_31]&~16)|(16 if k&2 else 0)
        car[BIT7_32]=(car[BIT7_32]&~128)|(128 if k&4 else 0)
        car[GATE_5C]=(car[GATE_5C]&~2)|(2 if k&8 else 0)
        timer=rng.choice((0,1,2,127,128,129,255,rng.randrange(256)))
        linked=rng.choice((2,3,rng.randrange(256)))
        xlo,xhi=sorted((rng.randrange(256),rng.randrange(256)))
        ylo,yhi=sorted((rng.randrange(256),rng.randrange(256)))
        e642=xlo|(xhi<<8);e95b=ylo|(yhi<<8)
        independent_out=independent(bytes(car),timer,linked,e642,e95b)
        opcode_out=opcode(master,bytes(car),timer,linked,e642,e95b)
        if independent_out!=opcode_out:
            raise AssertionError(f"Original AI linked countdown mismatch {k}: "
                                 f"{independent_out['reason']} vs {opcode_out['reason']}")
        hist[opcode_out["reason"]]=hist.get(opcode_out["reason"],0)+1
    return {"source":"Original arcade bank0 22B8-2360 (composed with verified 230B)",
            "stage_sha256":STAGE_SHA,"cases":cases,"mismatches":0,
            "outcomes":hist,"limitation":"Original linked timer/window/event flags; not full AI route or strategy"}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("--cases",type=int,default=100000)
    a=parser.parse_args()
    print(json.dumps(verify(a.master.read_bytes(),a.cases),indent=2))
