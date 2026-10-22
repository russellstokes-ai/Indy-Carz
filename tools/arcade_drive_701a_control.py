#!/usr/bin/env python3
"""1991 Indy Heat original master Z80 701A–7048 bounded input gate.

Execute actual authenticated original instructions from the return of CALL
75F2 at PC701A to original branch 709C, 7049, or opaque CALL 7D4C.
The 7D4C external call is NEVER fabricated or treated as returning.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

from arcade_drive_709c_speed import slot1_low

START = 0x701A
STAGE_END = 0x7049
STAGE_SHA = "5a106e4061f3c05fda71a5f3e6bbf1e880b0b6da58738eeaed5c008b88f80e71"
MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"


def _check(ix5c: int, ix57: int, ix31: int, ix33: int, counter: int) -> None:
    if any(not 0 <= v <= 255 for v in (ix5c, ix57, ix31, ix33, counter)):
        raise ValueError("Original five input bytes required")


def independent(ix5c: int, ix57: int, ix31: int,
                ix33: int, counter: int) -> dict:
    """Independent state machine using only known bit and X-ROM low rules."""
    _check(ix5c, ix57, ix31, ix33, counter)
    if ix5c & 1:
        return {"branch": "special_7d4c", "next_pc": 0x7D4C,
                "counter": counter, "b": None}
    if (ix31 & 0x10) or (ix33 & 1):
        return {"branch": "fast_709c", "next_pc": 0x709C,
                "counter": (counter + 1) & 255,
                "b": slot1_low(ix57, 0x60)}
    return {"branch": "slow_7049", "next_pc": 0x7049,
            "counter": 0, "b": ix57}


def original_opcodes(master: bytes, ix5c: int, ix57: int, ix31: int,
                     ix33: int, counter: int) -> dict:
    """Bounded executor of actual original bytes; stops at unknown CALL."""
    _check(ix5c, ix57, ix31, ix33, counter)
    if len(master) != 0x90000:
        raise ValueError("Original master Z80 ROM region required")
    if sha256(master[START:STAGE_END]).hexdigest() != STAGE_SHA:
        raise ValueError("Original 701A opcode fingerprint mismatch")
    pc = START
    a = h = l = b = 0
    zero = False
    xrom1_address = 0

    def read16(at: int) -> int:
        return master[at] | master[at + 1] << 8

    for _ in range(30):
        if pc in (0x709C, 0x7049, 0x7D4C):
            return {"branch": {0x709C: "fast_709c", 0x7049: "slow_7049",
                               0x7D4C: "special_7d4c"}[pc],
                    "next_pc": pc, "counter": counter,
                    "b": None if pc == 0x7D4C else b}
        if not START <= pc < STAGE_END:
            raise ValueError(f"Original 701A escaped bounded stage at {pc:04X}")
        op = master[pc]
        if op == 0xDD:
            suffix = master[pc + 1]
            if suffix == 0xCB:
                displacement, bit_op = master[pc + 2:pc + 4]
                if (displacement, bit_op) == (0x5C, 0x46):
                    zero = not bool(ix5c & 1)
                elif (displacement, bit_op) == (0x31, 0x66):
                    zero = not bool(ix31 & 0x10)
                elif (displacement, bit_op) == (0x33, 0x46):
                    zero = not bool(ix33 & 1)
                else:
                    raise ValueError("Unexpected original indexed BIT")
                pc += 4
            elif suffix == 0x46 and master[pc + 2] == 0x57:
                b = ix57
                pc += 3
            elif suffix == 0x34 and master[pc + 2] == 0xE3:
                counter = (counter + 1) & 255
                pc += 3
            elif suffix == 0x36 and master[pc + 2:pc + 4] == bytes((0xE3, 0)):
                counter = 0
                pc += 4
            else:
                raise ValueError(f"Unexpected original DD {suffix:02X} at {pc:04X}")
        elif op == 0xCA:
            target = read16(pc + 1)
            if target != 0x7027:
                raise ValueError("Unexpected original JP Z target")
            pc = target if zero else pc + 3
        elif op in (0x20, 0x28, 0x18):
            displacement = master[pc + 1]
            active = True if op == 0x18 else (not zero if op == 0x20 else zero)
            pc += 2 + ((displacement if displacement < 128 else displacement - 256) if active else 0)
        elif op == 0xCD:
            if read16(pc + 1) != 0x7D4C:
                raise ValueError("Unexpected external original CALL")
            # Halt BEFORE calling unresolved original 7D4C. We have not
            # claimed or simulated its global side effects/return 7572.
            pc = 0x7D4C
        elif op == 0x60:
            h = b
            pc += 1
        elif op == 0x2E:
            l = master[pc + 1]
            pc += 2
        elif op == 0x22:
            if read16(pc + 1) != 0xFFFE:
                raise ValueError("Unexpected original X-ROM write")
            xrom1_address = (h << 8) | l
            pc += 3
        elif op == 0x3A:
            if read16(pc + 1) != 0xFFFE:
                raise ValueError("Unexpected original X-ROM read")
            b_high = xrom1_address >> 8
            l_low = xrom1_address & 255
            a = slot1_low(b_high, l_low)
            pc += 3
        elif op == 0x47:
            b = a
            pc += 1
        else:
            raise ValueError(f"Unsupported original 701A opcode {op:02X} at {pc:04X}")
    raise ValueError("Original 701A gate exceeded 30 instruction budget")


def verify_original(master: bytes, cases: int = 100000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Authenticated original master ROM required")
    if not 0 <= cases <= 250000:
        raise ValueError("Invalid bounded verification budget")
    rng = Random(0x701A7049)
    hist: Counter[str] = Counter()
    for index in range(cases):
        route = index % 3
        ix5c = (rng.randrange(256) | 1) if route == 0 else (rng.randrange(256) & ~1)
        ix31 = (rng.randrange(256) | 0x10) if route == 1 else (rng.randrange(256) & ~0x10)
        ix33 = (rng.randrange(256) & ~1) if route == 2 else rng.randrange(256)
        args = (ix5c, rng.choice((0, 1, 127, 128, 255, rng.randrange(256))),
                ix31, ix33, rng.choice((0, 1, 254, 255, rng.randrange(256))))
        actual = original_opcodes(master, *args)
        expected = independent(*args)
        if actual != expected:
            raise AssertionError(f"Original 701A state mismatch {index} {args}: {actual} != {expected}")
        hist[actual["branch"]] += 1
    return {"source": "Original 1991 master bank0 701A–7048",
            "original_z80_cases": cases, "mismatches": 0,
            "branches": dict(hist),
            "unresolved_external": "7D4C CALL stops without guessed return",
            "scope": "post-75F2 bounded driving branch, not full original car frame"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_master", type=Path)
    parser.add_argument("--cases", type=int, default=100000)
    args = parser.parse_args()
    print(json.dumps(verify_original(args.private_master.read_bytes(), args.cases), indent=2))
