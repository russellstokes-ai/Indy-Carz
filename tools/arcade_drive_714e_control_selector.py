#!/usr/bin/env python3
"""Original 1991 Indy Heat master 714E-71C7, two-byte B/C physics source.

The Z80 code selects B/C from a caller-supplied 257-byte memory window
whose base is E96B. It uses carried SBC HL,DE borrow, 8-bit selector
doubling (indices 128..255 alias 0..127), RRCA BLENDING (not naive
averaging), and E76C sign-bit override. Some input states jump directly
to 7315, bypassing original 71C8–7314 movement math.

Private source Z80 ROM is required only by the bounded opcode verifier.
The public source contains no original game lookup values, maps or art.
A synthetic memory window cannot establish real track/handling tuning.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from random import Random

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA="3612f429e9a4824f63a4f42446fc1838a63014f645b6871906e2a1e0d0ef8d62"
START,STOP,BYPASS=0x714E,0x71C8,0x7315


def _validate(e76d,e76f,ix6e,ix6f,e76c,source,b0,c0,carry):
    if (any(not isinstance(x,int) for x in
            (e76d,e76f,ix6e,ix6f,e76c,b0,c0,carry))
        or not 0<=e76d<65536 or not 0<=e76f<65536
        or any(not 0<=x<256 for x in (ix6e,ix6f,e76c,b0,c0))
        or carry not in (0,1) or len(source)!=257):
        raise ValueError("Two original words, five bytes, carried flag and 257-byte table view required")


def _pair(source:bytes,selector:int)->tuple[int,int]:
    off=(selector*2)&255
    return source[off],source[off+1]


def _rrca(byte:int)->int:
    return ((byte>>1)|((byte&1)<<7))&255


def independent(e76d:int,e76f:int,ix6e:int,ix6f:int,e76c:int,
                source:bytes,b0:int=0,c0:int=0,carry:int=0)->dict:
    _validate(e76d,e76f,ix6e,ix6f,e76c,source,b0,c0,carry)
    b,c=b0,c0
    if e76d>=0x100+carry:
        if e76f>=0x100:
            return {"next_pc":BYPASS,"b":b,"c":c,
                    "path":"bypass_7315","overridden":False}
        b,c=_pair(source,ix6f)
        b>>=1;path="direct_6f"
    elif e76f>=0x101:
        b,c=_pair(source,ix6e)
        b>>=1;path="direct_6e"
    elif ix6e==ix6f:
        b,c=_pair(source,ix6e)
        path="matching_indices"
    else:
        x,y=_pair(source,ix6e)
        z,w=_pair(source,ix6f)
        b=_rrca((x+z)&255)
        c=_rrca((y+w)&255)
        path="rotated_blend"
    overridden=bool(e76c&128)
    if overridden:
        b,c=source[0],source[1]
    return {"next_pc":STOP,"b":b,"c":c,"path":path,
            "overridden":overridden}


def opcode(master:bytes,e76d:int,e76f:int,ix6e:int,ix6f:int,
           e76c:int,source:bytes,b0:int=0,c0:int=0,carry:int=0)->dict:
    """Interpret original REAL Z80 714E-71C7, strictly bounded.

    B and C and exact next-PC are returned from ORIGINAL Z80 execution;
    never copy outputs from the independent mathematical model.
    """
    _validate(e76d,e76f,ix6e,ix6f,e76c,source,b0,c0,carry)
    if len(master)!=0x90000:
        raise ValueError("Authentic master Z80 executable dimension required")
    table_ptr=0xE410
    ram={0xE76D:e76d&255,0xE76E:e76d>>8,
         0xE76F:e76f&255,0xE770:e76f>>8,
         0xE76C:e76c,0xE96B:table_ptr&255,0xE96C:table_ptr>>8}
    for i,byte in enumerate(source):
        addr=(table_ptr+i)&65535
        if addr in ram:raise ValueError("Test table aliases original global")
        ram[addr]=byte
    pc=START;a=h=l=d=e=0;b,c=b0,c0
    carry=bool(carry)
    zero=sign=False

    def read(addr:int)->int:
        if addr not in ram:
            raise ValueError(f"Unexpected original CPU RAM/table read at {addr:04X}")
        return ram[addr]
    def word(addr:int)->int:return read(addr)|(read(addr+1)<<8)

    for _ in range(90):
        op=master[pc]
        if op==0x11:
            e,d=master[pc+1:pc+3];pc+=3
        elif op==0x2A:
            addr=master[pc+1]|(master[pc+2]<<8)
            if addr not in (0xE76D,0xE76F,0xE96B):
                raise ValueError("Unexpected original 16-bit table/global pointer")
            value=word(addr);h,l=value>>8,value&255;pc+=3
        elif op==0xED:
            ext=master[pc+1]
            if ext==0x52:
                raw=(h<<8|l)-(d<<8|e)-int(carry)
                carry=raw<0
                wordval=raw&65535
                h,l=wordval>>8,wordval&255
                zero=wordval==0;sign=bool(wordval&32768);pc+=2
            elif ext==0x5B:
                addr=master[pc+2]|(master[pc+3]<<8)
                if addr!=0xE96B:raise ValueError("Unexpected original 16-bit DE table pointer")
                value=word(addr);d,e=value>>8,value&255;pc+=4
            else:raise ValueError(f"Unexpected original ED opcode {ext:02X}")
        elif op in (0xDA,0xD2,0xCA,0xF2):
            dest=master[pc+1]|(master[pc+2]<<8)
            jump=(carry if op==0xDA else not carry if op==0xD2
                  else zero if op==0xCA else not sign)
            pc=dest if jump else pc+3
        elif op==0xDD:
            ext,disp=master[pc+1:pc+3]
            if ext==0x7E and disp in (0x6E,0x6F):
                a=ix6e if disp==0x6E else ix6f
            elif ext==0x6E and disp==0x6F:
                l=ix6f
            else:raise ValueError("Unexpected original car indexed source")
            pc+=3
        elif op==0x18:
            off=master[pc+1];pc+=2+(off-256 if off>=128 else off)
        elif op==0x87:
            raw=a*2;carry=raw>255;a=raw&255;zero=a==0;sign=bool(a&128);pc+=1
        elif op==0x85:
            raw=a+l;carry=raw>255;a=raw&255;zero=a==0;sign=bool(a&128);pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x24:h=(h+1)&255;pc+=1
        elif op==0x46:b=read(h<<8|l);pc+=1
        elif op==0x23:
            value=(h<<8|l)+1;value&=65535;h,l=value>>8,value&255;pc+=1
        elif op==0x4E:c=read(h<<8|l);pc+=1
        elif op==0xCB:
            if master[pc+1]!=0x38:raise ValueError("Unexpected original SRL opcode")
            carry=bool(b&1);b>>=1;zero=b==0;pc+=2
        elif op==0xBD:
            raw=a-l;carry=raw<0;zero=a==l;sign=bool(raw&128);pc+=1
        elif op==0x83:
            raw=a+e;carry=raw>255;a=raw&255;zero=a==0;pc+=1
        elif op==0x5F:e=a;pc+=1
        elif op==0x14:d=(d+1)&255;pc+=1
        elif op==0x13:
            val=((d<<8)|e)+1;val&=65535;d,e=val>>8,val&255;pc+=1
        elif op==0x7D:a=l;pc+=1
        elif op==0x1A:a=read(d<<8|e);pc+=1
        elif op==0x86:
            raw=a+read(h<<8|l);carry=raw>255;a=raw&255;zero=a==0;pc+=1
        elif op==0x0F:carry=bool(a&1);a=_rrca(a);pc+=1
        elif op==0x47:b=a;pc+=1
        elif op==0x4F:c=a;pc+=1
        elif op==0x3A:
            addr=master[pc+1]|(master[pc+2]<<8)
            if addr!=0xE76C:raise ValueError("Unexpected original motion-direction read")
            a=read(addr);pc+=3
        elif op==0xB7:zero=a==0;sign=bool(a&128);carry=False;pc+=1
        else:raise ValueError(f"Unknown original Z80 opcode {op:02X} at {pc:04X}")

        if pc in (STOP,BYPASS):
            return {"next_pc":pc,"b":b,"c":c}
        if not START<=pc<STOP:
            raise ValueError(f"Original Z80 left bounded 714E control selector at {pc:04X}")
    raise ValueError("Original Z80 714E stage instruction budget exceeded")


def verify(master:bytes,cases:int=100000)->dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authentic privately checksum-verified original master required")
    if sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError("Original 714E source opcode SHA differs")
    if not 0<=cases<=250000:raise ValueError("Invalid original opcode test budget")
    rng=Random(0x714E);hist=Counter()
    for i in range(cases):
        values=(
            rng.choice((0,1,255,256,257,65535,rng.randrange(65536))),
            rng.choice((0,1,255,256,257,65535,rng.randrange(65536))),
            rng.choice((0,1,126,127,128,129,254,255,rng.randrange(256))),
        )
        ix6e=values[2]
        ix6f=rng.choice((ix6e,0,1,127,128,255,rng.randrange(256)))
        e76c=rng.choice((0,127,128,255,rng.randrange(256)))
        source=rng.randbytes(257)
        old_b,old_c=rng.randrange(256),rng.randrange(256)
        carry=i&1
        args=(values[0],values[1],ix6e,ix6f,e76c,source,old_b,old_c,carry)
        expected=independent(*args)
        actual=opcode(master,*args)
        if any(actual[k]!=expected[k] for k in ("next_pc","b","c")):
            raise AssertionError(f"Original B/C source parity failed input {i}: "
                                 f"Z80={actual}, independent={expected}")
        hist[expected["path"]]+=1
        if expected["overridden"]:hist["direction_override"]+=1
    return {"source":"1991 original arcade master Z80 714E–71C7",
            "opcode_cases":cases,"mismatches":0,
            "branch_cases":dict(sorted(hist.items())),
            "source_table":"257 private runtime table bytes supplied by caller; NEVER embedded",
            "original_carry_in":"inherited from prior 7148 arithmetic; externally supplied",
            "scope":"Verified B/C selector; upstream source-table construction and entire physics frame scheduling OPEN"}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("master",type=Path)
    p.add_argument("--cases",type=int,default=100000)
    a=p.parse_args()
    print(json.dumps(verify(a.master.read_bytes(),a.cases),indent=2))
