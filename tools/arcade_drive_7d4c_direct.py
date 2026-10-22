#!/usr/bin/env python3
"""Original master Z80 7D4C–7D64: direct-position branch/opaque slow exit.

Runs real 1991 original instructions under an authenticated private ROM;
the distinct 7D65–7E35 smoothing path is deliberately NOT simulated.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

START = 0x7D4C
STOP = 0x7D65
MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "a4fc47491840f382dcb8f9b95dbbc6173a776b07e6df6f46143a0a28b4a81794"


def _check(ix5c: int, ix65: int, ix66: int, ix67: int, ix68: int,
           original_y: int, original_x: int) -> None:
    if any(not 0 <= byte <= 255 for byte in (ix5c, ix65, ix66, ix67, ix68)):
        raise ValueError("All original indexed fields are single bytes")
    if not (0 <= original_x <= 65535 and 0 <= original_y <= 65535):
        raise ValueError("Original coordinate words required")


def independent(ix5c: int, ix65: int, ix66: int, ix67: int, ix68: int,
                original_y: int, original_x: int) -> dict:
    _check(ix5c, ix65, ix66, ix67, ix68, original_y, original_x)
    if ix5c & 2:
        return {"branch": "direct_7024", "next_pc": 0x7024,
                "y": (ix66 << 8) | ix65, "x": (ix68 << 8) | ix67}
    return {"branch": "slow_7d65", "next_pc": 0x7D65,
            "y": original_y, "x": original_x}


def original_opcodes(master: bytes, ix5c: int, ix65: int, ix66: int,
                     ix67: int, ix68: int, original_y: int, original_x: int) -> dict:
    _check(ix5c, ix65, ix66, ix67, ix68, original_y, original_x)
    if len(master) != 0x90000:
        raise ValueError("Original master region is required")
    if sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Original opcode window changed")
    pc = START
    h = l = 0
    y, x = original_y, original_x
    zero = False
    for _ in range(12):
        if pc == STOP:
            return {"branch": "slow_7d65", "next_pc": STOP, "y": y, "x": x}
        op = master[pc]
        if op == 0xDD:
            suffix = master[pc + 1]
            if suffix == 0xCB and master[pc + 2:pc + 4] == bytes((0x5C, 0x4E)):
                zero = not bool(ix5c & 2)
                pc += 4
            elif suffix == 0x66 and master[pc + 2] in (0x66, 0x68):
                h = ix66 if master[pc + 2] == 0x66 else ix68
                pc += 3
            elif suffix == 0x6E and master[pc + 2] in (0x65, 0x67):
                l = ix65 if master[pc + 2] == 0x65 else ix67
                pc += 3
            else:
                raise ValueError(f"Unexpected original 7D4C indexed opcode {suffix:02X}")
        elif op == 0x28:
            relative = master[pc + 1]
            pc += 2 + ((relative if relative < 128 else relative - 256) if zero else 0)
        elif op == 0x22:
            target = master[pc + 1] | (master[pc + 2] << 8)
            if target == 0xE72B:
                y = (h << 8) | l
            elif target == 0xE735:
                x = (h << 8) | l
            else:
                raise ValueError("Unexpected original centre-coordinate destination")
            pc += 3
        elif op == 0xC9:
            if pc != 0x7D64:
                raise ValueError("Unexpected early original RET")
            return {"branch": "direct_7024", "next_pc": 0x7024, "y": y, "x": x}
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")
    raise ValueError("Original 7D4C opcode budget exceeded")


def verify_original(master: bytes, cases: int = 100000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Authenticated original master Z80 required")
    if not 0 <= cases <= 250000:
        raise ValueError("Invalid bounded verification budget")
    rng = Random(0x7D4C7D65)
    histogram: Counter[str] = Counter()
    for index in range(cases):
        ix5c = (rng.randrange(256) | 2) if index % 2 else (rng.randrange(256) & ~2)
        args = (ix5c, *[rng.randrange(256) for _ in range(4)],
                rng.randrange(65536), rng.randrange(65536))
        expected = independent(*args)
        actual = original_opcodes(master, *args)
        if actual != expected:
            raise AssertionError(f"Original 7D4C mismatch at {index}: {args}, {expected}, {actual}")
        histogram[actual["branch"]] += 1
    return {"source": "Original 1991 master bank0 7D4C–7D64",
            "cases": cases, "mismatches": 0,
            "branches": dict(histogram),
            "unknown_path": "7D65–7E35 slow smoothing NOT simulated",
            "scope": "direct-position branch of original 701A special call only"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_master", type=Path)
    parser.add_argument("--cases", type=int, default=100000)
    args = parser.parse_args()
    print(json.dumps(verify_original(args.private_master.read_bytes(), args.cases), indent=2))
