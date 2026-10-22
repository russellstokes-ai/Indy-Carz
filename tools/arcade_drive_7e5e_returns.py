#!/usr/bin/env python3
"""Original Z80 7E5E–7EA2 early returns; stop before event dispatch.

Recovered authentic ROM instructions distinguish four safe returns to
7091 from still-unverified 7EA3.. event processing. No side effects of
that later routine or its nested calls are fabricated.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

START, STOP, CALL_RETURN = 0x7E5E, 0x7EA3, 0x7091
MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "3cd3606a7aef94188d2d9e33a7dd6f44baec5a1ba7a59f25a16392a3388fc22f"


def _check(*values: int) -> None:
    if len(values) != 10 or any(not 0 <= value <= 255 for value in values):
        raise ValueError("Original 7E5E gate requires ten authentic unsigned bytes")


def _result(branch: str, ix3a: int) -> dict:
    return {"branch": branch,
            "next_pc": STOP if branch == "dispatch_7ea3" else CALL_RETURN,
            "ix3a": ix3a,
            "complete": branch != "dispatch_7ea3"}


def independent(ix31: int, e603: int, ix_minus3: int, e602: int,
                e674: int, e638: int, e639: int, ix02: int,
                ix51: int, ix3a: int) -> dict:
    """Independent signed flag/branch model without instruction decoding."""
    _check(ix31, e603, ix_minus3, e602, e674, e638, e639, ix02, ix51, ix3a)
    if ix31 & 0x40:
        return _result("return_flag", ix3a)
    if e603:
        return _result("dispatch_7ea3", ix3a)
    if ix_minus3 == 4 and e602 == 0 and e674 < 2:
        difference = (e639 - ix02 - e638) & 255
        if difference & 0x80:  # original JP P not taken after CP B
            return _result("return_special", 0x48)
    if e639 == ix02:
        return _result("return_equal", ix3a)
    if ((e639 - 1) & 255) == ix02 and ix51 >= 0x1E:
        return _result("return_neighbor", ix3a)
    return _result("dispatch_7ea3", ix3a)


def original_opcodes(master: bytes, ix31: int, e603: int, ix_minus3: int,
                     e602: int, e674: int, e638: int, e639: int,
                     ix02: int, ix51: int, ix3a: int) -> dict:
    """Execute original authenticated 7E5E–7EA2 PC/flags, no guessed calls."""
    if len(master) != 0x90000 or sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Authenticated original 7E5E opcode window required")
    _check(ix31, e603, ix_minus3, e602, e674, e638, e639, ix02, ix51, ix3a)
    indexed = {0x31: ix31, 0xFD: ix_minus3, 0x02: ix02, 0x51: ix51}
    ram = {0xE603: e603, 0xE602: e602, 0xE674: e674,
           0xE638: e638, 0xE639: e639}
    a = b = 0
    carry = zero = sign = False
    pc = START

    def byte(offset: int = 0) -> int:
        return master[pc + offset]

    def word() -> int:
        return byte(1) | (byte(2) << 8)

    for _ in range(42):
        if pc == STOP:
            return _result("dispatch_7ea3", ix3a)
        if not START <= pc < STOP:
            raise ValueError(f"Original 7E5E stage escaped: {pc:04X}")
        op = byte()
        if op == 0xDD:
            suffix, disp = byte(1), byte(2)
            if suffix == 0xCB and (disp, byte(3)) == (0x31, 0x76):
                zero = not bool(indexed[0x31] & 0x40)
                pc += 4
            elif suffix == 0x7E and disp in (0xFD, 0x51):
                a = indexed[disp]
                pc += 3
            elif suffix == 0x96 and disp == 0x02:
                raw = a - indexed[disp]
                a, carry, zero, sign = raw & 255, raw < 0, (raw & 255) == 0, bool(raw & 128)
                pc += 3
            elif suffix == 0xBE and disp == 0x02:
                raw = a - indexed[disp]
                carry, zero, sign = raw < 0, (raw & 255) == 0, bool(raw & 128)
                pc += 3
            elif suffix == 0x36 and (disp, byte(3)) == (0x3A, 0x48):
                ix3a = 0x48
                pc += 4
            else:
                raise ValueError(f"Unknown original DD at {pc:04X}")
        elif op == 0x3A:  # LD A,(nn)
            address = word()
            if address not in ram:
                raise ValueError("Unknown original 7E5E memory source")
            a = ram[address]
            pc += 3
        elif op == 0xB7:  # OR A
            carry, zero, sign = False, a == 0, bool(a & 128)
            pc += 1
        elif op == 0xFE:  # CP n
            raw = a - byte(1)
            carry, zero, sign = raw < 0, (raw & 255) == 0, bool(raw & 128)
            pc += 2
        elif op == 0x47:  # LD B,A
            b = a
            pc += 1
        elif op == 0xB8:  # CP B (sign for JP P)
            raw = a - b
            carry, zero, sign = raw < 0, (raw & 255) == 0, bool(raw & 128)
            pc += 1
        elif op == 0x3D:  # DEC A (preserves carry)
            a = (a - 1) & 255
            zero, sign = a == 0, bool(a & 128)
            pc += 1
        elif op in (0x20, 0x30):  # JR NZ or JR NC with true PC relative
            shift = byte(1)
            active = not zero if op == 0x20 else not carry
            pc += 2 + (shift if active else 0)
        elif op == 0xF2:  # JP P,7E90
            if word() != 0x7E90:
                raise ValueError("Unexpected original JP P target")
            pc = 0x7E90 if not sign else pc + 3
        elif op in (0xC0, 0xC8, 0xD0, 0xC9):
            taken = (not zero if op == 0xC0 else
                     zero if op == 0xC8 else
                     not carry if op == 0xD0 else True)
            if taken:
                reason = {0x7E62: "return_flag", 0x7E8F: "return_special",
                          0x7E96: "return_equal", 0x7EA2: "return_neighbor"}.get(pc)
                if reason is None:
                    raise ValueError("Unexpected original 7E5E return instruction")
                return _result(reason, ix3a)
            pc += 1
        else:
            raise ValueError(f"Unsupported original 7E5E opcode {op:02X} at {pc:04X}")
    raise ValueError("Original 7E5E exceeded bounded 42-instruction budget")


def verify_original(master: bytes, cases: int = 100000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Authenticated private original master region required")
    if not 0 <= cases <= 250000:
        raise ValueError("Invalid parity case count")
    rng = Random(0x7E5E7EA3)
    coverage: Counter[str] = Counter()
    for index in range(cases):
        route = index % 6
        carflag = rng.randrange(256)
        e603 = rng.randrange(256)
        carid = rng.randrange(256)
        e602 = rng.randrange(256)
        e674 = rng.randrange(256)
        e638, e639, ix02 = rng.randrange(256), rng.randrange(256), rng.randrange(256)
        ix51, ix3a = rng.randrange(256), rng.randrange(256)
        if route == 0:
            carflag |= 0x40
        else:
            carflag &= ~0x40
            e603 = 1 if route == 1 else 0
            carid = 4 if route == 2 else 3
            e602, e674 = 0, 1
            if route == 2:
                e639 = ix02
                e638 = 128
            elif route == 3:
                e639 = ix02
            elif route in (4, 5):
                e639 = (ix02 + 1) & 255
                ix51 = 30 if route == 4 else 29
        fields = carflag, e603, carid, e602, e674, e638, e639, ix02, ix51, ix3a
        actual = original_opcodes(master, *fields)
        expected = independent(*fields)
        if actual != expected:
            raise AssertionError(f"Original 7E5E mismatch {index} {fields}: {actual} != {expected}")
        coverage[actual["branch"]] += 1
    return {"source": "Original bank0 7E5E–7EA2 early-return gate",
            "original_z80_cases": cases, "mismatches": 0,
            "branches": dict(coverage), "opaque_stop": "7EA3 event dispatch",
            "scope": "no nested event, collision or 8022/8659 effects"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_master", type=Path)
    parser.add_argument("--cases", type=int, default=100000)
    args = parser.parse_args()
    print(json.dumps(verify_original(args.private_master.read_bytes(), args.cases), indent=2))
