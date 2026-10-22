#!/usr/bin/env python3
"""Recover Indy Heat's original six-slot, 15-pair arcade collision prefilter.

Verifies the 1991 checksum-matched ROM and runs a bounded interpreter of the
original Z80 proximity gates. Does NOT port the complete narrow-phase
response, damage, AI or race systems. Original binary data stays private.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
from itertools import combinations, product
import json
from pathlib import Path
import random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
PAIR_START = 0xB057
PAIR_STRIDE = 0x38
PAIR_COUNT = 15
NARROW_PHASE = 0xB3B1
PAIR_END = PAIR_START + PAIR_STRIDE * PAIR_COUNT
PAIRS = list(combinations(range(6), 2))
ENTRY_SIGNATURE = bytes.fromhex("dd 7e fc fd a6 fc 1f d8 dd 7e 33 fd b6 33 e6 02 c0")


def le16(value: int) -> bytes:
    return value.to_bytes(2, "little")


@dataclass(frozen=True)
class Car:
    axis0: int
    axis1: int
    flags_7c: int
    flags_b3: int = 0

    def __post_init__(self) -> None:
        if not (0 <= self.axis0 <= 0xffff and 0 <= self.axis1 <= 0xffff and
                0 <= self.flags_7c <= 255 and 0 <= self.flags_b3 <= 255):
            raise ValueError("Original car fields are unsigned 16/8-bit quantities")


def program_for_pair(pair: tuple[int, int], pc: int) -> bytes:
    """Reconstruct the known, uniform 56-byte Z80 instruction template."""
    left, right = pair
    a, b = 0xe000 + left * 0x100, 0xe000 + right * 0x100
    next_pc = pc + PAIR_STRIDE
    code = (
        b"\x3a" + le16(a + 0x7c) + b"\x2a" + le16(b + 0x7c) +
        b"\xb5\xf2" + le16(next_pc) +
        b"\x2a" + le16(b) + b"\xed\x4b" + le16(a) +
        b"\xed\x42\x7c\xc6\x03\xfe\x06\xd2" + le16(next_pc) +
        b"\xeb\x2a" + le16(b + 0x0a) + b"\xed\x4b" + le16(a + 0x0a) +
        b"\xed\x42\x7c\xc6\x03\xfe\x06\xd2" + le16(next_pc) +
        b"\xdd\x21" + le16(a + 0x80) +
        b"\xfd\x21" + le16(b + 0x80) +
        b"\xcd\xb1\xb3"
    )
    if len(code) != PAIR_STRIDE:
        raise AssertionError("Unexpected arcade template length")
    return code


def validate_layout(master: bytes) -> None:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Original checksum-verified arcade master ROM required")
    # A000..DFFF fixed-ROM is the SAME bytes as bank1 2000..5FFF, not
    # a second unique set of game routines.
    if master[0xa000:0xe000] != master[0x18000:0x1c000]:
        raise ValueError("Original fixed/banked ROM alias differs")
    for index, pair in enumerate(PAIRS):
        pc = PAIR_START + PAIR_STRIDE * index
        if master[pc:pc + PAIR_STRIDE] != program_for_pair(pair, pc):
            raise ValueError(f"Original pair {pair} opcode template differs at {pc:04X}")
    if master[NARROW_PHASE:NARROW_PHASE + len(ENTRY_SIGNATURE)] != ENTRY_SIGNATURE:
        raise ValueError("Original pairwise contact entry differs")
    if master[PAIR_END:PAIR_END + 4] != bytes.fromhex("3a 19 e9 b7"):
        raise ValueError("Original pairwise loop boundary differs")


def model_broadphase(left: Car, right: Car) -> tuple[str, int | None, int | None]:
    """Separate mathematical reconstruction of the original branch conditions."""
    if not ((left.flags_7c | right.flags_7c) & 0x80):
        return "status_skip", None, None
    dx = (right.axis0 - left.axis0) & 0xffff
    if (((dx >> 8) + 3) & 255) >= 6:
        return "axis0_skip", None, None
    # CP 6 retains carry=1 after successful first-axis test, so the
    # original SECOND SBC HL,BC subtracts one extra unit.
    dy = (right.axis1 - left.axis1 - 1) & 0xffff
    if (((dy >> 8) + 3) & 255) >= 6:
        return "axis1_skip", None, None
    return "narrow_phase_call", dx, dy


def original_pair_opcodes(master: bytes, index: int,
                          left: Car, right: Car) -> tuple[str, int | None, int | None]:
    """Execute only original Z80 opcodes in the matching 56-byte pair test."""
    if not 0 <= index < PAIR_COUNT:
        raise ValueError("Original arcade pair index out of range")
    slot_a, slot_b = PAIRS[index]
    addr_a, addr_b = 0xe000 + slot_a * 256, 0xe000 + slot_b * 256
    data = {
        addr_b + 0x7c: right.flags_7c, addr_a: left.axis0,
        addr_b: right.axis0, addr_a + 0x0a: left.axis1,
        addr_b + 0x0a: right.axis1,
    }
    pc = PAIR_START + index * PAIR_STRIDE
    end = pc + PAIR_STRIDE
    a = b = c = d = e = h = l = ix = iy = 0
    carry = sign = swapped_axes = False

    def memword(addr: int) -> int:
        if addr not in data:
            raise ValueError(f"Unexpected original pair RAM word at {addr:04X}")
        return data[addr]

    for _ in range(35):
        op = master[pc]
        if op == 0x3A:   # LD A,(absolute)
            addr = int.from_bytes(master[pc + 1:pc + 3], "little")
            if addr != addr_a + 0x7c:
                raise ValueError("Unexpected first car status address")
            a = left.flags_7c
            pc += 3
        elif op == 0x2A:  # LD HL,(absolute)
            addr = int.from_bytes(master[pc + 1:pc + 3], "little")
            value = memword(addr)
            h, l = value >> 8, value & 255
            pc += 3
        elif op == 0xB5:  # OR L
            a |= l
            carry, sign = False, bool(a & 128)
            pc += 1
        elif op == 0xF2:  # JP P,next pair
            target = int.from_bytes(master[pc + 1:pc + 3], "little")
            if target != end:
                raise ValueError("Unexpected original positive-sign branch")
            if not sign:
                return "status_skip", None, None
            pc += 3
        elif op == 0xED and master[pc + 1] == 0x4B:  # LD BC,(nn)
            addr = int.from_bytes(master[pc + 2:pc + 4], "little")
            value = memword(addr)
            b, c = value >> 8, value & 255
            pc += 4
        elif op == 0xED and master[pc + 1] == 0x42:  # SBC HL,BC
            diff = (h << 8 | l) - (b << 8 | c) - int(carry)
            carry = diff < 0
            diff &= 65535
            h, l = diff >> 8, diff & 255
            pc += 2
        elif op == 0x7C:  # LD A,H
            a = h
            pc += 1
        elif op == 0xC6:  # ADD A,03
            if master[pc + 1] != 3:
                raise ValueError("Original coordinate bias differs")
            total = a + 3
            a, carry = total & 255, total > 255
            pc += 2
        elif op == 0xFE:  # CP 06
            if master[pc + 1] != 6:
                raise ValueError("Original coordinate comparison differs")
            carry = a < 6
            pc += 2
        elif op == 0xD2:  # JP NC,next pair
            target = int.from_bytes(master[pc + 1:pc + 3], "little")
            if target != end:
                raise ValueError("Original out-of-range branch differs")
            if not carry:
                return ("axis1_skip" if swapped_axes else "axis0_skip"), None, None
            pc += 3
        elif op == 0xEB:  # EX DE,HL
            d, e, h, l = h, l, d, e
            swapped_axes = True
            pc += 1
        elif op == 0xDD and master[pc + 1] == 0x21:  # LD IX,nn
            ix = int.from_bytes(master[pc + 2:pc + 4], "little")
            pc += 4
        elif op == 0xFD and master[pc + 1] == 0x21:  # LD IY,nn
            iy = int.from_bytes(master[pc + 2:pc + 4], "little")
            pc += 4
        elif op == 0xCD:  # CALL B3B1, stop BEFORE original narrow-phase
            target = int.from_bytes(master[pc + 1:pc + 3], "little")
            if (target != NARROW_PHASE or ix != addr_a + 0x80 or
                    iy != addr_b + 0x80 or pc + 3 != end):
                raise ValueError("Unexpected original collision candidate call")
            return "narrow_phase_call", d << 8 | e, h << 8 | l
        else:
            raise ValueError(f"Unexpected Z80 pair opcode {op:02X} at {pc:04X}")
    raise ValueError("Original pair routine exceeded instruction budget")


def narrow_entry_model(left: Car, right: Car) -> bool:
    """Model the two original RET gates before the detailed contact maths."""
    return not ((left.flags_7c & right.flags_7c & 1) or
                ((left.flags_b3 | right.flags_b3) & 2))


def original_narrow_entry(master: bytes, left: Car, right: Car) -> bool:
    """Boundedly execute original Z80 $B3B1..$B3C1, stopping at first RET."""
    pc = NARROW_PHASE
    a, carry = 0, False
    for _ in range(9):
        op = master[pc]
        if master[pc:pc + 3] == bytes.fromhex("dd 7e fc"):
            a = left.flags_7c
            pc += 3
        elif master[pc:pc + 3] == bytes.fromhex("fd a6 fc"):
            a &= right.flags_7c
            carry = False
            pc += 3
        elif op == 0x1F:  # RRA
            new_carry = bool(a & 1)
            a = (int(carry) << 7) | (a >> 1)
            carry = new_carry
            pc += 1
        elif op == 0xD8:  # RET C
            if carry:
                return False
            pc += 1
        elif master[pc:pc + 3] == bytes.fromhex("dd 7e 33"):
            a = left.flags_b3
            pc += 3
        elif master[pc:pc + 3] == bytes.fromhex("fd b6 33"):
            a |= right.flags_b3
            carry = False
            pc += 3
        elif master[pc:pc + 2] == bytes.fromhex("e6 02"):
            a &= 2
            carry = False
            pc += 2
        elif op == 0xC0:  # RET NZ
            if a:
                return False
            pc += 1
        else:
            raise ValueError(f"Unexpected original narrow entry opcode at {pc:04X}")
        if pc == NARROW_PHASE + len(ENTRY_SIGNATURE):
            return True
    raise ValueError("Original narrow entry exceeded opcode budget")


def verify(master: bytes, random_cases_per_pair: int = 1200) -> dict:
    validate_layout(master)
    if not 0 <= random_cases_per_pair <= 50000:
        raise ValueError("Random cases must be 0..50000 per pair")
    rng = random.Random(0xC0111510)
    outcomes: Counter[str] = Counter()
    checks = 0
    boundary = (-0x401, -0x301, -0x300, -0x2ff, -0x101, -1, 0, 1,
                0xff, 0x100, 0x1ff, 0x2ff, 0x300, 0x301, 0x401)
    for index in range(PAIR_COUNT):
        for dx, dy in product(boundary, boundary):
            for status in (0, 0x80, 0x81, 0xff):
                left = Car(0x8000, 0x7000, status)
                right = Car((0x8000 + dx) & 65535, (0x7000 + dy) & 65535, 0)
                model = model_broadphase(left, right)
                original = original_pair_opcodes(master, index, left, right)
                if original != model:
                    raise AssertionError(f"Original arcade proximity mismatch pair {index}: {model} != {original}")
                outcomes[model[0]] += 1
                checks += 1
        for _ in range(random_cases_per_pair):
            x, y = rng.randrange(65536), rng.randrange(65536)
            left = Car(x, y, rng.choice((0, 1, 0x80, 0x81, 255)))
            right = Car((x + rng.randint(-1100, 1100)) & 65535,
                        (y + rng.randint(-1100, 1100)) & 65535,
                        rng.choice((0, 1, 0x80, 0x81, 255)))
            model = model_broadphase(left, right)
            original = original_pair_opcodes(master, index, left, right)
            if original != model:
                raise AssertionError(f"Random original arcade proximity mismatch pair {index}")
            outcomes[model[0]] += 1
            checks += 1
    narrow_checks = 0
    for s1, s2, b1, b2 in product(
            (0, 1, 0x80, 0x81), (0, 1, 0x80, 0x81),
            (0, 2, 0xfe, 0xff), (0, 2, 0xfe, 0xff)):
        a, b = Car(0, 0, s1, b1), Car(0, 0, s2, b2)
        if narrow_entry_model(a, b) != original_narrow_entry(master, a, b):
            raise AssertionError("Original narrow-phase early return gate mismatch")
        narrow_checks += 1
    return {
        "set": "1991 indyheat arcade",
        "cpu_range": "master fixed B057..B39E",
        "narrow_phase_pc": "B3B1",
        "pair_count": len(PAIRS),
        "pairs": [{"left": a, "right": b, "pc": f"{PAIR_START+i*PAIR_STRIDE:04X}"}
                  for i, (a, b) in enumerate(PAIRS)],
        "bytes_per_pair": PAIR_STRIDE,
        "rom_alias": "master fixed A000..DFFF = master bank1 2000..5FFF",
        "first_gate": "(status_a[7C] | status_b[7C]) bit7 set",
        "axis0": "(((word_b[00]-word_a[00]) & 0xFFFF) >> 8) biased +3 modulo 256 is <6",
        "axis1": "(((word_b[0A]-word_a[0A]-1) & 0xFFFF) >> 8) biased +3 modulo 256 is <6",
        "second_subtraction_note": "carry=1 survives first successful Z80 CP 06",
        "narrow_entry_early_returns": "both status[7C] bit0, or either status[B3] bit1",
        "original_opcode_pair_cases": checks,
        "original_opcode_narrow_entry_cases": narrow_checks,
        "mismatches": 0,
        "skip_decisions": dict(outcomes),
        "unverified": "Detailed original contact geometry, impulses, crash/damage, track-wall and gameplay conditions",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("master", type=Path, help="PRIVATE master.mame_runtime.bin")
    ap.add_argument("--out", type=Path,
                    default=Path("local/recovery/original_pair_broadphase.json"))
    ap.add_argument("--random-cases-per-pair", type=int, default=1200)
    args = ap.parse_args()
    report = verify(args.master.read_bytes(), args.random_cases_per_pair)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {report['original_opcode_pair_cases']} pair-candidate cases and "
          f"{report['original_opcode_narrow_entry_cases']} entry gates with "
          f"{report['mismatches']} mismatches")
    print(f"Private report: {args.out}")


if __name__ == "__main__":
    main()
