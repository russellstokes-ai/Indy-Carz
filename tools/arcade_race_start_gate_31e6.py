#!/usr/bin/env python3
"""Original 1991 arcade master 31E9-3207 race-start gate and helper 0A4F.

31E6 begins with CALL 2CF9 (separately opcode-verified in the counter
module). This module starts just after that call and stops at the next
unknown external call at 3208. Original CPU bytes execute only in a private
workspace; the public repo contains clean independent arithmetic/models.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
SIGNATURES = (
    (0x31E6, 0x31E9, "a83a83088590861f53cf4f9995f4740cc8da6a1975167f8bf3e3bb48c3e59d34"),
    (0x31E9, 0x3208, "4dc24bd57d1f1bcdb1106a643eac82fa591bf3f201424c36ac17e98b6e06ae3c"),
    (0x0A4F, 0x0A5E, "cd87890b3f60286ef30540615f02c142d23f2facdd47c8872f6d85d093314cd3"),
)


def independent(e603: int, e67b: int, e67c: int,
                ed59: int, car91: int) -> dict:
    """Exact bounded original 31E9 state writes and original 0A4F subtraction."""
    if (any(not 0 <= x <= 255 for x in (e603, e67b, e67c, car91))
            or not 0 <= ed59 < 65536):
        raise ValueError("Original four bytes and one 16-bit ED59 word required")
    if e603 == 0 and e67b == 0:
        return {
            "e61f": 0, "e69f": 0, "e67b": 0, "e67c": e67c,
            "car91": car91, "accumulator": 0, "exit": "early_ret_31FA",
        }
    return {
        "e61f": 0, "e69f": 0, "e67b": 0x1F, "e67c": 1,
        "car91": (car91-(ed59 & 255)) & 255,
        "accumulator": 1, "exit": "continue_3208",
    }


def actual_opcodes(master: bytes, e603: int, e67b: int, e67c: int,
                   ed59: int, car91: int) -> dict:
    """Interpret real Z80 bytes at 31E9 and original 0A4F helper only.

    Strict opcode and RAM address allowlists. The 3208 external CALL and
    preceeding 2CF9 preamble are deliberately NOT assumed to be no-ops.
    """
    independent(e603, e67b, e67c, ed59, car91)
    if len(master) != 0x90000:
        raise ValueError("Authentic original master size required")
    ix = 0xE080
    ram = {0xE603:e603, 0xE67B:e67b, 0xE67C:e67c,
           0xE61F:17, 0xE69F:19, 0xED59:ed59&255,
           0xED5A:ed59>>8, ix+0x11:car91}
    a = h = l = 0
    zero = False
    pc = 0x31E9
    stack: list[tuple[str, object]] = []

    def result(exit_name: str) -> dict:
        return {
            "e61f":ram[0xE61F], "e69f":ram[0xE69F],
            "e67b":ram[0xE67B], "e67c":ram[0xE67C],
            "car91":ram[ix+0x11], "accumulator":a, "exit":exit_name,
        }

    for _ in range(50):
        op = master[pc]
        if op == 0xAF: a=0; zero=True; pc+=1
        elif op == 0x32:
            addr=master[pc+1] | master[pc+2]<<8
            if addr not in (0xE61F,0xE69F,0xE67B,0xE67C):
                raise ValueError("Unexpected original global store")
            ram[addr]=a;pc+=3
        elif op == 0x3A:
            addr=master[pc+1] | master[pc+2]<<8
            if addr not in (0xE603,0xE67B):
                raise ValueError("Unexpected original global read")
            a=ram[addr];pc+=3
        elif op == 0xB7:zero=a==0;pc+=1
        elif op == 0x20:
            offset=master[pc+1]
            if offset>=128:offset-=256
            pc+=2+(offset if not zero else 0)
        elif op == 0xC8:
            if pc!=0x31FA:raise ValueError("Unexpected Z80 RET Z")
            if zero:return result("early_ret_31FA")
            pc+=1
        elif op == 0x3E:
            a=master[pc+1]; zero=(a==0);pc+=2
        elif op == 0xCD:
            target=master[pc+1]|master[pc+2]<<8
            if target!=0x0A4F:raise ValueError("Original CALL leaves verified stage")
            stack.append(("ret",pc+3));pc=target
        elif op == 0xF5:stack.append(("af",(a,zero)));pc+=1
        elif op == 0xE5:stack.append(("hl",(h,l)));pc+=1
        elif op == 0xDD:
            ext,disp=master[pc+1:pc+3]
            if disp!=0x11 or ext not in (0x7E,0x77):
                raise ValueError("Unexpected original car indexed source")
            if ext==0x7E:a=ram[ix+disp]
            else:ram[ix+disp]=a
            pc+=3
        elif op == 0x2A:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=0xED59:raise ValueError("Unexpected original word read")
            l,h=ram[addr],ram[addr+1];pc+=3
        elif op == 0x95:
            a=(a-l)&255
            zero=(a==0)
            pc+=1
        elif op == 0xE1:
            tag,pair=stack.pop()
            if tag!="hl":raise ValueError("Original saved HL mismatch")
            h,l=pair;pc+=1
        elif op == 0xF1:
            tag,pair=stack.pop()
            if tag!="af":raise ValueError("Original saved AF mismatch")
            a,zero=pair;pc+=1
        elif op == 0xC9:
            tag,pc=stack.pop()
            if tag!="ret":raise ValueError("Original return stack mismatch")
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")

        if pc==0x3208:
            if stack:raise ValueError("Original return incomplete")
            return result("continue_3208")
        if not (0x31E9<=pc<0x3208 or 0x0A4F<=pc<0x0A5E):
            raise ValueError("Original race-start code escaped bounded path")
    raise ValueError("Original gate instruction budget exceeded")


def verify(master: bytes, extra_early_cases: int = 4096) -> dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authenticated original 1991 arcade master required")
    for start,stop,digest in SIGNATURES:
        if sha256(master[start:stop]).hexdigest()!=digest:
            raise ValueError(f"Original race-start checksum changed at {start:04X}")
    if not 0<=extra_early_cases<=50000:
        raise ValueError("Extra original early-return tests out of range")
    rng=Random(0x31E9)
    counts=Counter()
    for e603 in range(256):
        for e67b in range(256):
            args=(e603,e67b,rng.randrange(256),rng.randrange(65536),rng.randrange(256))
            expected=independent(*args)
            observed=actual_opcodes(master,*args)
            if expected!=observed:
                raise AssertionError(f"Original 31E9 parity mismatch E603={e603} E67B={e67b}")
            counts[expected["exit"]]+=1
    for _ in range(extra_early_cases):
        args=(0,0,rng.randrange(256),rng.randrange(65536),rng.randrange(256))
        if independent(*args)!=actual_opcodes(master,*args):
            raise AssertionError("Original early-return path changed")
        counts["additional_early_ret"]+=1
    return {"source":"original fixed master 31E9-3207 and 0A4F",
            "original_call_2cf9":"separately verified; called at 31E6",
            "cases":65536+extra_early_cases,"mismatches":0,
            "branches":dict(counts),
            "scope":"verified race-start globals and byte adjustment only; following CALL 856F etc unverified"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master",type=Path)
    parser.add_argument("--additional-early",type=int,default=4096)
    args=parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.additional_early),indent=2))
