#!/usr/bin/env python3
"""Original bounded Z80 2AD1–2AD5: real early return vs event dispatch.

The following 2AD6–2BCC code changes bank selectors, publishes race
event words and writes memory through original ROM-sourced tables. It
is NOT included in this tiny gate's verified behavior.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

START, STOP, CALL_RETURN = 0x2AD1, 0x2AD6, 0x709B
MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "989b44feeff748361f08fa51bddd4608c6ebfe4ba08bfe8c3b329d41e9bb31ba"


def independent(ix31: int) -> dict:
    if not 0 <= ix31 <= 255:
        raise ValueError("Original IX+31 bit field must be an unsigned byte")
    if ix31 & 1:
        return {"branch": "return_709b", "next_pc": CALL_RETURN, "complete": True}
    return {"branch": "dispatch_2ad6", "next_pc": STOP, "complete": False}


def original_opcodes(master: bytes, ix31: int) -> dict:
    if len(master) != 0x90000 or sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Authenticated original 2AD1 instruction window required")
    if not 0 <= ix31 <= 255:
        raise ValueError("Original IX+31 byte required")
    pc = START
    zero = False
    for _ in range(2):
        if pc == 0x2AD1:
            if master[pc:pc + 4] != bytes((0xDD, 0xCB, 0x31, 0x46)):
                raise ValueError("Unexpected original bit0 opcode")
            zero = not bool(ix31 & 1)
            pc += 4
        elif pc == 0x2AD5:
            if master[pc] != 0xC0:
                raise ValueError("Unexpected original RET NZ opcode")
            if not zero:
                return {"branch": "return_709b", "next_pc": CALL_RETURN, "complete": True}
            pc += 1
    if pc == STOP:
        return {"branch": "dispatch_2ad6", "next_pc": STOP, "complete": False}
    raise ValueError("Original 2AD1 did not reach expected bounded gate")


def verify_original(master: bytes, cases: int = 100000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Private authenticated owner master required")
    if not 0 <= cases <= 250000:
        raise ValueError("Invalid original verification case count")
    counts: Counter[str] = Counter()
    for i in range(cases):
        ix31 = (((i * 97) ^ (i >> 3)) & 0xFE) | (i & 1)
        actual = original_opcodes(master, ix31)
        expected = independent(ix31)
        if actual != expected:
            raise AssertionError(f"Original 2AD1 mismatch {i}: {actual} != {expected}")
        counts[actual["branch"]] += 1
    return {"source": "Original 1991 Z80 2AD1–2AD5 bit gate",
            "original_z80_cases": cases, "mismatches": 0,
            "branches": dict(counts), "opaque_stop": "2AD6 banked event code",
            "scope": "one gate, not full 2AD1 function or frame"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_master", type=Path)
    parser.add_argument("--cases", type=int, default=100000)
    options = parser.parse_args()
    print(json.dumps(verify_original(options.private_master.read_bytes(), options.cases), indent=2))
