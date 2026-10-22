#!/usr/bin/env python3
"""Recover Indy Heat's original collision approach-angle decision, $B510..$B545.

Two *original* calls to $A600 calculate eight-bit directional angles.
Between them the original Z80 uses two 16-bit car-indexed field differences,
including the carry left by A600 and the carry left by a 3-bit shift.
Then it selects the next response branch based on the wrapped 8-bit angular
difference: outside [64,192) -> B5AC; inside -> B546.

Both indexed fields' exact gameplay meanings remain UNVERIFIED. No generic
velocity/collision engine is created and original ROM data remain private.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from random import Random

from arcade_collision_angle_opcode_parity import (
    TABLE_BEGIN, TABLE_END, independent_angle_with_carry, execute_original,
)

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "cf6c642dc8c6c0e27ad10a5eccb0db43a1b1606532a27e17f510c5f8770b020f"
START, BRANCH_POINT = 0xB510, 0xB546
OTHER_BRANCH = 0xB5AC


def independent_direction_branch(master: bytes, b: int, c: int,
                                 ix_word1: int, iy_word1: int,
                                 ix_word2: int, iy_word2: int) -> tuple[str,int,int,int]:
    """Independent high-level reconstruction, preserving both Z80 carry effects."""
    if len(master) <= TABLE_END:
        raise ValueError("Original ROM table not present")
    if any(not 0 <= v < 256 for v in (b, c)):
        raise ValueError("Original collision relative inputs must be bytes")
    if any(not 0 <= v < 65536 for v in (ix_word1, iy_word1, ix_word2, iy_word2)):
        raise ValueError("Indexed car fields are 16-bit values")
    table = master[TABLE_BEGIN:TABLE_END]
    incoming_angle, _, incoming_carry = independent_angle_with_carry(table, b, c)
    difference1 = (iy_word1 - ix_word1 - incoming_carry) & 0xffff
    scaled_b = ((difference1 << 3) & 0xffff) >> 8
    # Last of three ADD HL,HL instructions sends input bit 13 to carry.
    incoming_second_carry = (difference1 >> 13) & 1
    difference2 = (iy_word2 - ix_word2 - incoming_second_carry) & 0xffff
    scaled_c = ((difference2 << 3) & 0xffff) >> 8
    outgoing_angle, _, _ = independent_angle_with_carry(table, scaled_b, scaled_c)
    angular_delta = (outgoing_angle - incoming_angle) & 255
    return ("B5AC" if angular_delta < 0x40 or angular_delta >= 0xC0 else "B546",
            angular_delta, scaled_b, scaled_c)


def execute_original_stage(master: bytes, b: int, c: int,
                           ix_word1: int, iy_word1: int,
                           ix_word2: int, iy_word2: int) -> tuple[str,int,int,int]:
    """Bounded original Z80 execution, stopping at one of the two branch PCs."""
    if len(master) != 0x90000:
        raise ValueError("Original master Z80 executable required")
    if any(not 0 <= v < 256 for v in (b, c)):
        raise ValueError("Original collision relative components must be bytes")
    if any(not 0 <= v < 65536 for v in (ix_word1, iy_word1, ix_word2, iy_word2)):
        raise ValueError("Original indexed word must be 16-bit")
    a = h = l = d = e = carry = 0
    pc = START
    for _ in range(80):
        op = master[pc]
        if op == 0xCD:  # CALL $A600: returns angle AND carry
            if master[pc+1:pc+3] != bytes.fromhex("00 a6"):
                raise ValueError(f"Unexpected original angle call at {pc:04X}")
            a, _, _, carry = execute_original(master, b, c, include_flags=True)
            pc += 3
        elif op == 0xFD:  # IY word field (-$62 or -$58)
            ext, offset = master[pc+1:pc+3]
            word = iy_word1 if offset in (0x9F, 0x9E) else iy_word2
            part = (word >> 8) & 255 if offset in (0x9F, 0xA9) else word & 255
            if ext == 0x66:
                h = part
            elif ext == 0x6E:
                l = part
            else:
                raise ValueError(f"Unexpected IY word instruction at {pc:04X}")
            pc += 3
        elif op == 0xDD:  # IX word field (-$62 or -$58)
            ext, offset = master[pc+1:pc+3]
            word = ix_word1 if offset in (0x9F, 0x9E) else ix_word2
            part = (word >> 8) & 255 if offset in (0x9F, 0xA9) else word & 255
            if ext == 0x56:
                d = part
            elif ext == 0x5E:
                e = part
            else:
                raise ValueError(f"Unexpected IX word instruction at {pc:04X}")
            pc += 3
        elif op == 0xED and master[pc+1] == 0x52:  # SBC HL,DE
            value = ((h << 8) | l) - ((d << 8) | e) - carry
            carry = int(value < 0)
            value &= 65535
            h, l = value >> 8, value & 255
            pc += 2
        elif op == 0x29:  # ADD HL,HL, three times per component
            value = (((h << 8) | l) << 1)
            h, l, carry = (value >> 8) & 255, value & 255, int(value > 65535)
            pc += 1
        elif op == 0x44:  # LD B,H
            b = h
            pc += 1
        elif op == 0x4C:  # LD C,H
            c = h
            pc += 1
        elif op == 0x57:  # LD D,A: save first angle
            d = a
            pc += 1
        elif op == 0x92:  # SUB D: wrapped angle separation
            a = (a-d) & 255
            pc += 1
        elif op == 0xFE:  # CP $40 / CP $C0
            carry = int(a < master[pc+1])
            pc += 2
        elif op in (0xDA, 0xD2):  # JP C / JP NC, $B5AC
            if master[pc+1:pc+3] != bytes.fromhex("ac b5"):
                raise ValueError(f"Unexpected collision gate branch at {pc:04X}")
            take = carry if op == 0xDA else not carry
            pc = OTHER_BRANCH if take else pc+3
        else:
            raise ValueError(f"Unrecognised original contact instruction {op:02X} at {pc:04X}")
        if pc in (BRANCH_POINT, OTHER_BRANCH):
            return (f"{pc:04X}", a, b, c)
        if not START <= pc < BRANCH_POINT:
            raise ValueError(f"Collision-angle stage exceeded original boundary at {pc:04X}")
    raise ValueError("Original collision-angle classifier exceeded instruction budget")


def verify(master: bytes, random_cases: int = 5000, edge_cases: int = 25000) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Original checksum-verified Indy Heat master ROM required")
    if hashlib.sha256(master[START:BRANCH_POINT]).hexdigest() != STAGE_SHA:
        raise ValueError("Original direction comparator instructions differ")
    if random_cases < 0 or edge_cases < 0 or random_cases+edge_cases > 200000:
        raise ValueError("Invalid bounded test configuration")
    rng = Random(0xB5AC)
    words = (0, 1, 2, 0x7f, 0x80, 0xff, 0xffff,
             0x8000, 0x7fff, 0x2000, 0x1fff, 0x3fff)
    observed = Counter()
    total = 0

    def check(args: tuple[int,int,int,int,int,int]) -> None:
        nonlocal total
        expected = independent_direction_branch(master, *args)
        actual = execute_original_stage(master, *args)
        if actual != expected:
            raise AssertionError(f"Original contact direction gate mismatch {args}")
        observed[actual[0]] += 1
        total += 1

    for _ in range(random_cases):
        check((rng.randrange(256), rng.randrange(256),
               *[rng.randrange(65536) for _ in range(4)]))
    for _ in range(edge_cases):
        check((rng.choice((0,1,64,128,255)),
               rng.choice((0,1,64,128,255)),
               *[rng.choice(words) for _ in range(4)]))
    return {
        "source": "1991 arcade master fixed Z80 PC B510..B545",
        "function_calls": "A600 twice; original return carry affects first SBC",
        "first_indexed_comparison": "IY[-0x62] - IX[-0x62] - carry(A600)",
        "second_indexed_comparison": "IY[-0x58] - IX[-0x58] - carry(last first-component HL*2)",
        "relative_components": "high byte of (16-bit delta * 8) modulo 65536",
        "difference": "(angle(second vector) - angle(first vector)) & 255",
        "branch": "B5AC if delta <64 or >=192; else B546",
        "test_cases": total,
        "mismatches": 0,
        "branch_counts": dict(observed),
        "scope": "Direction-gate classification only; downstream impulses/damage still OPEN",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path)
    p.add_argument("--out", type=Path,
                   default=Path("local/recovery/original_collision_direction_gate.json"))
    args = p.parse_args()
    r = verify(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
