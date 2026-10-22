#!/usr/bin/env python3
"""Original arcade 1C8C-1CA1 Z80 refresh-state mixer.

This reproduces one original bounded fixed-master routine using the saved
16-bit E678 word and the Z80 R register at its LD A,R instruction. Actual R
timing in a race is not known from static ROM analysis. Original program
bytes must remain private; the supplied ROM is only read for parity checks.
"""
from __future__ import annotations
from hashlib import sha256
from random import Random
from pathlib import Path
import argparse
import json

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "e9bdd8bcfd216a3bedea612f9885c4926d1ccba9dfd13ed13684102687bf6f7e"
START, STOP = 0x1C8C, 0x1CA2


def independent(previous: int, refresh: int) -> tuple[int, int]:
    if not (isinstance(previous, int) and 0 <= previous <= 65535
            and isinstance(refresh, int) and 0 <= refresh <= 255):
        raise ValueError("Original 16-bit saved state and Z80 R byte required")
    doubled = (previous << 1) & 65535
    h = (0x1D ^ (doubled >> 8) ^ refresh) & 255
    l = 0x87 ^ (doubled & 255)
    return (h << 8) | l, h ^ l


def original_opcodes(master: bytes, previous: int, refresh: int) -> tuple[int, int]:
    independent(previous, refresh)
    if len(master) != 0x90000:
        raise ValueError("Authentic original 0x90000 master required")
    mem = {0xE678: previous & 255, 0xE679: previous >> 8}
    pc, a, h, l = START, 0, 0, 0
    for _ in range(24):
        op = master[pc]
        if op == 0x2A:
            address = master[pc+1] | master[pc+2] << 8
            if address != 0xE678: raise ValueError("Unexpected original RNG read")
            l, h = mem[address], mem[address+1]
            pc += 3
        elif op == 0x29:
            value = ((h << 8) | l) * 2 & 65535
            h, l = value >> 8, value & 255
            pc += 1
        elif op == 0x3E:
            a = master[pc+1]; pc += 2
        elif op == 0xAC:
            a ^= h; pc += 1
        elif op == 0xAD:
            a ^= l; pc += 1
        elif op == 0x67:
            h = a; pc += 1
        elif op == 0x6F:
            l = a; pc += 1
        elif op == 0xED:
            if master[pc+1] != 0x5F:
                raise ValueError("Unexpected original Z80 refresh read")
            a = refresh; pc += 2
        elif op == 0x22:
            address = master[pc+1] | master[pc+2] << 8
            if address != 0xE678: raise ValueError("Unexpected original RNG write")
            mem[address], mem[address+1] = l, h
            pc += 3
        elif op == 0x7C:
            a = h; pc += 1
        elif op == 0xC9:
            if pc != STOP - 1: raise ValueError("Unexpected return")
            return mem[0xE678] | mem[0xE679] << 8, a
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")
        if not START <= pc < STOP:
            raise ValueError("Original RNG left bounded source")
    raise ValueError("Original RNG instruction budget exceeded")


def verify(master: bytes, cases: int = 65536) -> dict:
    if (len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA
            or sha256(master[START:STOP]).hexdigest() != STAGE_SHA):
        raise ValueError("Checksum-verified authentic arcade ROM required")
    if not 0 <= cases <= 250000: raise ValueError("Invalid verification case count")
    rng = Random(0x1C8C)
    for i in range(cases):
        old = i * 257 if i < 256 else rng.randrange(65536)
        refresh = (i & 255) if i < 256 else rng.randrange(256)
        a, b = independent(old, refresh), original_opcodes(master, old, refresh)
        if a != b: raise AssertionError(f"Original RNG parity failure {i}: {a} vs {b}")
    return {"source": "original arcade fixed master 1C8C-1CA1",
            "cases": cases, "mismatches": 0, "limitation":
            "Exact input R required; original live Z80 refresh timing not established"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("master", type=Path)
    ap.add_argument("--cases", type=int, default=65536)
    args = ap.parse_args()
    print(json.dumps(verify(args.master.read_bytes(), args.cases), indent=2))
