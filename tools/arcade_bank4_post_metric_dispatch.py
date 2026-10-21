#!/usr/bin/env python3
"""Original arcade master bank4 213F-22B9 post-metric response.

Two previously verified CALL 22BA outputs and original fifth-car linked
record are supplied explicitly. Interpreter executes actual bank4 Z80 bytes,
including 16-bit flag/carry behaviour. Original CALL 1C8C uses independently
verified integer state mixing with a controlled R-register input. Original
CALL 1783 pointer setup and both CALL 22BA routines are separately checked;
their downstream effects are NOT guessed here. Opaque jumps 10E6/10EB are
reported, never treated as successfully completed AI/physics actions.

Original ROM/data/art is private; public script uses user-supplied ROM only
when verifying and ships neither source opcodes nor the proprietary lookup.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random
from arcade_original_rng_1c8c import independent as original_rng

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
BANK4_BASE = 0x30000
START, STOP = 0x213F, 0x22BA
STAGE_SHA = "f0e0e7245ae06bb2e13464e58c18a63afc0bc1d5ee6a6e506bd0ca98150a9ceb"

def byte(v: int) -> int: return v & 255
def word(v: int) -> int: return v & 65535
def signed16(v: int) -> int: return v - 65536 if v & 32768 else v

def _inputs(first:int, fifth:int, old:int, divider:int, e639:int, c:int,
            f02:int, f04:int, f39:int, event:int, f62:int,
            linked:int, rng:int, refresh:int) -> None:
    if divider not in (2,4): raise ValueError("Original E638 must be 2 or 4")
    if any(not isinstance(n,int) or not 0 <= n < 65536
           for n in (first,fifth,old,rng)):
        raise ValueError("Original 16-bit pair metrics and state required")
    if any(not isinstance(n,int) or not 0 <= n < 256
           for n in (e639,c,f02,f04,f39,event,f62,linked,refresh)):
        raise ValueError("Original 8-bit car/global bytes and Z80 refresh required")


def independent(first:int, fifth:int, old:int, divider:int, e639:int,
                c:int, f02:int, f04:int, f39:int, event:int, f62:int,
                linked:int, rng:int, refresh:int) -> dict:
    """Original bounded model. First metric was selected IX car, fifth from E480."""
    _inputs(first,fifth,old,divider,e639,c,f02,f04,f39,event,f62,linked,rng,refresh)
    delta = word(fifth-first)
    negative = bool(byte(byte(e639-f02)-divider) & 128)
    c = byte(c-1)
    route = None
    if negative:
        if c & 128:
            adjusted = word(delta-64)
            if signed16(adjusted) >= 0:
                b,limit,route=0xF0,0xC0,"228F"
            else:
                b,limit,route=0xFF,0x80,"225A";event |= 1
        elif c == 0:
            adjusted=word(delta-8)
            if signed16(adjusted)>=0:
                b,limit,route=0xF0,0xC0,"228F"
            else:
                b,limit,route=0xC0,0x60,"225A";event |= 1
        else:
            c=byte(c-1)
            if c==0:
                adjusted=word(delta-4)
                if signed16(adjusted)>=0:
                    b,limit,route=0xF0,0xC0,"228F"
                else:
                    b,limit,route=0x80,0x20,"2247"
            else:
                c=byte(c-1)
                if c==0:
                    adjusted=delta
                    if signed16(adjusted)>=0:
                        b,limit,route=0xD0,0x80,"228F"
                    else:
                        b,limit,route=0x80,0x20,"2247"
                else:
                    adjusted=word(delta+8)
                    if signed16(adjusted)>=0:
                        b,limit,route=0xB0,0x20,"228F"
                        if signed16(word(((e639<<8)|0xC0) -
                                         ((f02<<8)|f04)))<0:
                            f39=0
                    else:
                        b,limit,route=0x80,0x20,"2247"
    else:
        if c & 128:
            adjusted=word(delta-48)
            if signed16(adjusted)>=0:
                b,limit,route=0xF0,0xC0,"228F"
            else:
                b,limit,route=0xFF,0x80,"2247"
        elif c==0:
            adjusted=word(delta-16)
            if signed16(adjusted)>=0:
                b,limit,route=0xF0,0xC0,"228F"
            else:
                b,limit,route=0xC0,0x60,"2247"
        else:
            c=byte(c-1)
            if c==0:
                adjusted=word(delta-8)
                if signed16(adjusted)>=0:
                    b,limit,route=0xF0,0xC0,"228F"
                else:
                    b,limit,route=0x80,0x30,"2247"
            else:
                c=byte(c-1)
                if c==0:
                    adjusted=word(delta-6)
                    if signed16(adjusted)>=0:
                        b,limit,route=0xE0,0xB0,"228F"
                    else:
                        b,limit,route=0x80,0x30,"2247"
                else:
                    adjusted=word(delta-4)
                    if signed16(adjusted)>=0:
                        b,limit,route=0xD0,0x80,"228F"
                    else:
                        b,limit,route=0x80,0x30,"2247"

    rng_used=False
    if route=="2247":
        if adjusted >> 8 == 255:
            rng, random_byte=original_rng(rng,refresh)
            rng_used=True
            if random_byte >= (adjusted & 255):
                event |= 1
        else:
            event |= 1

    selected=b if signed16(word(adjusted-old))<0 else limit
    new_linked=byte(linked+selected)
    overflow=linked+selected>255
    if route=="228F":
        exit_label=("return_c_229D" if overflow else
                    "return_m_22A2" if byte(f62-1)&128 else
                    "external_10E6")
    else:
        exit_label=("return_nc_2268" if not overflow else
                    "return_nc_226F" if byte(f62+1)>=16 else
                    "external_10EB")
    return {"e61c":adjusted,"fifth_39":f39,"fifth_event":event,
            "linked_3a":new_linked,"rng_state":rng,"rng_used":rng_used,
            "route":route,"exit":exit_label,"selected_change":selected,
            "initial_metric_delta":delta}


def original_opcodes(master:bytes,first:int,fifth:int,old:int,divider:int,
                     e639:int,c:int,f02:int,f04:int,f39:int,event:int,
                     f62:int,linked:int,rng:int,refresh:int) -> dict:
    """Execute real bank4 213F-22B9 original opcodes, with verified callees injected.

    22BA is independently opcode-verified: input 'first' and 'fifth' supply
    its two return HL values. Original fifth-car IX=E480 is checked, and
    CALL 1783 is represented by the separately verified fifth-car IY pointer.
    The original 1C8C result is the separately opcode-verified integer rule.
    Remaining 10E6/10EB are opaque external jumps.
    """
    _inputs(first,fifth,old,divider,e639,c,f02,f04,f39,event,f62,linked,rng,refresh)
    if len(master)!=0x90000: raise ValueError("Authenticated original master size required")
    source=master[BANK4_BASE:BANK4_BASE+0x8000]
    pc=START
    a=b=h=l=d=e=0
    ix=iy=0
    zero=sign=carry=False
    stack:list[tuple[str,int]]=[]
    calls=0
    e61c=old
    rng_used=False
    route=None
    selection=None

    def code(address:int)->int:return source[address-0x2000]
    def immediate(address:int)->int:return code(address)|(code(address+1)<<8)
    def pair(hi:int,lo:int)->int:return (hi<<8)|lo
    def finish(label:str)->dict:
        if route is None or selection is None or stack or ix!=4 or iy!=1 or calls!=2:
            raise ValueError("Original control-flow or metric call stack incomplete")
        return {"e61c":e61c,"fifth_39":f39,"fifth_event":event,
                "linked_3a":linked,"rng_state":rng,"rng_used":rng_used,
                "route":route,"exit":label,"selected_change":selection,
                "initial_metric_delta":word(fifth-first)}

    for _ in range(140):
        op=code(pc)
        if op==0xCD:
            target=immediate(pc+1)
            if target==0x22BA:
                if calls==0: h,l=first>>8,first&255
                elif calls==1: h,l=fifth>>8,fifth&255
                else:raise ValueError("More than two original 22BA calls")
                calls+=1
            elif target==0x1783:
                if ix!=4:raise ValueError("Original fifth-car linked pointer missing")
                iy=1
            elif target==0x1C8C:
                rng,a=original_rng(rng,refresh)
                rng_used=True
            else:raise ValueError(f"Unverified original CALL {target:04X}")
            pc+=3
        elif op==0xDD:
            sub=code(pc+1)
            if sub==0x21:
                if immediate(pc+2)!=0xE480:raise ValueError("Fifth car IX pointer changed")
                ix=4;pc+=4
            elif sub==0xCB:
                if (code(pc+2),code(pc+3))!=(0xF7,0xC6):
                    raise ValueError("Unexpected original event SET")
                event |= 1;pc+=4
            elif sub==0x36:
                if (code(pc+2),code(pc+3))!=(0x39,0):
                    raise ValueError("Unexpected original car byte reset")
                f39=0;pc+=4
            elif sub in (0x46,0x4E,0x7E,0x96):
                disp=code(pc+2)
                if (sub,disp)==(0x46,0x02):b=f02
                elif (sub,disp)==(0x4E,0x04):c=f04
                elif (sub,disp)==(0x7E,0xE2):a=f62
                elif (sub,disp)==(0x96,0x02):
                    raw=a-f02;carry=raw<0;a=byte(raw)
                    zero=a==0;sign=bool(a&128)
                else:raise ValueError("Unknown original fifth car indexed field")
                pc+=3
            else:raise ValueError(f"Unknown original IX opcode {sub:02X}")
        elif op==0xFD:
            sub=code(pc+1)
            if code(pc+2)!=0x3A:raise ValueError("Original IY linked byte changed")
            if sub==0x86:
                raw=a+linked;carry=raw>255
                a=byte(raw);zero=a==0;sign=bool(a&128)
            elif sub==0x77:linked=a
            else:raise ValueError("Unexpected original IY opcode")
            pc+=3
        elif op==0xED:
            sub=code(pc+1)
            if sub in (0x52,0x4A,0x42):
                hl=pair(h,l)
                amount=pair(d,e) if sub==0x52 else pair(b,c)
                raw=(hl+amount+int(carry) if sub==0x4A
                     else hl-amount-int(carry))
                carry=(raw>65535 if sub==0x4A else raw<0)
                raw=word(raw);h,l=raw>>8,raw&255
                sign=bool(raw&32768);zero=raw==0
                pc+=2
            elif sub==0x5B:
                if immediate(pc+2)!=0xE61C:raise ValueError("Unknown original global load")
                d,e=e61c>>8,e61c&255;pc+=4
            else:raise ValueError("Unexpected original ED")
        elif op==0x3A:
            addr=immediate(pc+1)
            if addr==0xE638:a=divider
            elif addr==0xE639:a=e639
            else:raise ValueError("Unknown original global read")
            pc+=3
        elif op==0x22:
            if immediate(pc+1)!=0xE61C:raise ValueError("Unknown original global store")
            e61c=pair(h,l);pc+=3
        elif op==0x01:b,c=code(pc+2),code(pc+1);pc+=3
        elif op==0x06:b=code(pc+1);pc+=2
        elif op==0x0E:c=code(pc+1);pc+=2
        elif op==0x2E:l=code(pc+1);pc+=2
        elif op==0x3E:a=code(pc+1);pc+=2
        elif op==0x47:b=a;pc+=1
        elif op==0x4F:c=a;pc+=1
        elif op==0x78:a=b;pc+=1
        elif op==0x79:a=c;pc+=1
        elif op==0x7C:a=h;pc+=1
        elif op==0x67:h=a;pc+=1
        elif op==0x45:b=l;pc+=1
        elif op==0xE5:stack.append(("hl",pair(h,l)));pc+=1
        elif op==0xD1:
            tag,v=stack.pop()
            if tag!="hl":raise ValueError("Original POP DE stack mismatch")
            d,e=v>>8,v&255;pc+=1
        elif op==0xE1:
            tag,v=stack.pop()
            if tag!="hl":raise ValueError("Original POP HL stack mismatch")
            h,l=v>>8,v&255;pc+=1
        elif op==0xC5:stack.append(("bc",pair(b,c)));pc+=1
        elif op==0xC1:
            tag,v=stack.pop()
            if tag!="bc":raise ValueError("Original POP BC mismatch")
            b,c=v>>8,v&255;pc+=1
        elif op==0xB7:carry=False;zero=a==0;sign=bool(a&128);pc+=1
        elif op==0xB8:
            v=a-b;carry=v<0;zero=byte(v)==0;sign=bool(byte(v)&128);pc+=1
        elif op==0xFE:
            v=a-code(pc+1);carry=v<0;zero=byte(v)==0;sign=bool(byte(v)&128);pc+=2
        elif op==0x3C:a=byte(a+1);zero=a==0;sign=bool(a&128);pc+=1
        elif op==0x3D:a=byte(a-1);zero=a==0;sign=bool(a&128);pc+=1
        elif op==0x0D:c=byte(c-1);zero=c==0;sign=bool(c&128);pc+=1
        elif op==0x18:
            n=code(pc+1);pc=pc+2+(n if n<128 else n-256)
        elif op in (0x20,0x28,0x38):
            n=code(pc+1);n=n if n<128 else n-256
            take=not zero if op==0x20 else zero if op==0x28 else carry
            pc=pc+2+(n if take else 0)
        elif op in (0xF2,0xFA,0xC3):
            dst=immediate(pc+1)
            take=not sign if op==0xF2 else sign if op==0xFA else True
            pc=dst if take else pc+3
        elif op in (0xD0,0xD8,0xF8):
            take=not carry if op==0xD0 else carry if op==0xD8 else sign
            if take:
                site={0x2268:"return_nc_2268",0x226F:"return_nc_226F",
                      0x229D:"return_c_229D",0x22A2:"return_m_22A2"}.get(pc)
                if site is None:raise ValueError("Unexpected original return")
                return finish(site)
            pc+=1
        else:
            raise ValueError(f"Unexpected bank4 original opcode {op:02X} at {pc:04X}")
        if pc in (0x10E6,0x10EB):
            return finish("external_10E6" if pc==0x10E6 else "external_10EB")
        if pc==0x2247:route="2247"
        if pc==0x225A and route is None:route="225A"
        if pc==0x228F:route="228F"
        if pc in (0x2262,0x2297):selection=a
        if not START <= pc < STOP:
            raise ValueError(f"Original Z80 escaped verified bank4 routine at {pc:04X}")
    raise ValueError("Original bank4 post-metric instruction budget exceeded")


def verify(master:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated original master required")
    segment=master[BANK4_BASE+START-0x2000:BANK4_BASE+STOP-0x2000]
    if sha256(segment).hexdigest()!=STAGE_SHA:
        raise ValueError("Original 213F-22B9 bytecode fingerprint mismatch")
    if not 0<=cases<=250000:raise ValueError("Invalid case count")
    rng=Random(0x213F)
    branches=Counter()
    for i in range(cases):
        first=rng.randrange(65536)
        delta=rng.choice((0,1,2,3,4,5,6,8,16,32,48,64,128,0x7FF0,
                          0x8000,0xFFF0,0xFFFF,rng.randrange(65536)))
        fifth=word(first+delta)
        e639=rng.randrange(256)
        args=(first,fifth,rng.choice((0,0,1,64,32767,32768,65535,rng.randrange(65536))),
              2 if i&1 else 4,e639,
              rng.choice((0,1,2,3,4,5,127,128,255,rng.randrange(256))),
              rng.choice((0,1,2,3,255,e639,rng.randrange(256))),
              rng.randrange(256),rng.randrange(256),rng.randrange(256),
              rng.randrange(256),rng.randrange(256),
              rng.randrange(65536),rng.randrange(256))
        expected=independent(*args)
        actual=original_opcodes(master,*args)
        if expected!=actual:
            differences={k:(expected[k],actual.get(k)) for k in expected
                         if expected[k]!=actual.get(k)}
            raise AssertionError(f"Original bank4 213F mismatch case {i}: {differences}")
        branches[actual["route"]+"/"+actual["exit"]]+=1
    return {"source":"original 1991 arcade master bank4 213F-22B9",
            "case_count":cases,"mismatches":0,"branches":dict(branches),
            "scope":"22BA and 1783 caller results injected from separately verified routines; "
                    "original 1C8C controlled R; full 10E6/10EB and gameplay still OPEN"}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("master",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    args=p.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.cases),indent=2))
