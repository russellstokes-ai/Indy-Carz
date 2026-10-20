#!/usr/bin/env python3
"""Original 1991 Indy Heat championship start/advance, independently verified.

Fixed master 2936..2952 initial selection; bank 3 62A9..62C4 advancement;
fixed helper 1747..174D reads the original fifteen-entry event table.
The actual Z80 is interpreted and compared with an independent state model.
Original proprietary ROM input remains LOCAL; no ROM bytes are committed.

Scope ends BEFORE game-state CALL 2120 / launch-time six-slot setup.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
INIT_START, INIT_STOP = 0x2936, 0x2953
ADVANCE_START, ADVANCE_STOP = 0x62A9, 0x62C5
BANK3_BASE = 0x28000
INIT_SHA = "e4610488259e91691551cbf6d6dc11b202a2a78d74a901a1321ea9ad596f5259"
ADVANCE_SHA = "256bd3dcc164aca666c1e08786d82af426ae58131681c9d5bec2e5d23f4fa06c"
HELPER_SHA = "4f7f30e081e5e2f5c619823771e06b1f890771c9211435bca09f3bca9c4dd63d"
TABLE_SHA = "6adb1bd48bc4ac375d6a9472e12d4513393ff7b71ba4b1422b22b4c21250710c"
COURSES = (13, 12, 1, 3, 7, 8, 4, 2, 5, 11, 0, 6, 9, 10, 1)


def _byte(n: int, name: str) -> None:
    if not 0 <= n <= 255:
        raise ValueError(f"{name} must be a byte")


def independent(selector: int, old_round: int, stage: str) -> dict:
    """Mathematical model of the original E69A selector and E69B counter.

    E69A >= 0x80 selects automatic mode. E69A in 0..14 directly selects
    the original championship round. Other positive values are rejected
    because the *documented* 15-byte course table cannot index them.
    """
    _byte(selector, "E69A")
    _byte(old_round, "E69B")
    if stage not in ("initialize", "advance"):
        raise ValueError("Unknown original championship stage")
    if selector < 128:
        if selector >= 15:
            raise ValueError("Unverified original direct selector")
        selected = selector
    elif stage == "initialize":
        selected = 0
    else:
        if old_round >= 15:
            raise ValueError("Unverified original previous championship round")
        selected = (old_round + 1) % 15
    return {
        "round_counter": selected,
        "course_index": COURSES[selected],
        "next_pc": (0x2953 if selected == 0 else 0x2989)
                   if stage == "initialize" else 0x62C5,
        "next_call": None if stage == "initialize" else 0x2120,
        "stage": stage,
    }


def cpu_view(master: bytes, stage: str) -> bytes:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Authentic checksum-verified 1991 master Z80 required")
    view = bytearray(master[:0xE000])
    if stage == "advance":
        view[0x2000:0xA000] = master[BANK3_BASE:BANK3_BASE+0x8000]
    elif stage == "initialize":
        view[0x2000:0xA000] = master[0x2000:0xA000]
    else:
        raise ValueError("Unknown CPU bank stage")
    return bytes(view)


def check_original(master: bytes) -> None:
    init, next_round = cpu_view(master, "initialize"), cpu_view(master, "advance")
    for memory, start, stop, digest in (
        (init, INIT_START, INIT_STOP, INIT_SHA),
        (next_round, ADVANCE_START, ADVANCE_STOP, ADVANCE_SHA),
        (init, 0x1747, 0x174E, HELPER_SHA),
        (init, 0x1ABF, 0x1ACE, TABLE_SHA),
    ):
        if sha256(memory[start:stop]).hexdigest() != digest:
            raise ValueError(f"Original arcade instruction/table changed at {start:04X}")
    if tuple(init[0x1ABF:0x1ACE]) != COURSES:
        raise ValueError("Original championship order changed")


def opcode(master: bytes, selector: int, old_round: int, stage: str) -> dict:
    """Interpret bounded ORIGINAL Z80 opcodes and the original lookup CALL."""
    independent(selector, old_round, stage)  # reject unverified table indices
    m = cpu_view(master, stage)
    a = h = l = 0
    carry = sign = zero = False
    ram = {0xE69A: selector, 0xE69B: old_round, 0xE699: 255}
    first, last = ((INIT_START, INIT_STOP) if stage == "initialize"
                   else (ADVANCE_START, ADVANCE_STOP))
    pc = first
    stack = []
    for _ in range(50):
        op = m[pc]
        if op == 0x3A:  # LD A,(nn)
            address = m[pc+1] | (m[pc+2] << 8)
            if address not in ram:
                raise ValueError("Unexpected original championship RAM read")
            a = ram[address]
            pc += 3
        elif op == 0x32:  # LD (nn),A
            address = m[pc+1] | (m[pc+2] << 8)
            if address not in (0xE69B, 0xE699):
                raise ValueError("Unexpected original championship RAM write")
            ram[address] = a
            pc += 3
        elif op == 0xB7:  # OR A
            zero, sign, carry = a == 0, bool(a & 128), False
            pc += 1
        elif op == 0xF2:  # JP P,nn
            address = m[pc+1] | (m[pc+2] << 8)
            if address not in (0x293E, 0x62B4):
                raise ValueError("Unknown original JP P target")
            pc = address if not sign else pc+3
        elif op == 0xAF:  # XOR A
            a, zero, sign, carry = 0, True, False, False
            pc += 1
        elif op == 0x3C:  # INC A
            a = (a+1) & 255
            zero, sign = a == 0, bool(a & 128)
            pc += 1
        elif op == 0xFE:  # CP immediate
            imm = m[pc+1]
            diff = (a-imm) & 255
            zero, sign, carry = diff == 0, bool(diff & 128), a < imm
            pc += 2
        elif op == 0x20:  # JR NZ
            displacement = m[pc+1]
            displacement = displacement-256 if displacement >= 128 else displacement
            pc += 2 + (displacement if not zero else 0)
        elif op == 0x21:  # LD HL,nn
            l, h = m[pc+1:pc+3]
            pc += 3
        elif op == 0xCD:  # CALL original fixed 1747
            address = m[pc+1] | (m[pc+2] << 8)
            if address != 0x1747:
                raise ValueError("Unexpected original championship table helper")
            stack.append(pc+3)
            pc = address
        elif op == 0x85:  # ADD A,L
            raw = a+l
            carry, a = raw > 255, raw & 255
            zero, sign = a == 0, bool(a & 128)
            pc += 1
        elif op == 0x6F:  # LD L,A
            l = a
            pc += 1
        elif op == 0x30:  # JR NC
            displacement = m[pc+1]
            displacement = displacement-256 if displacement >= 128 else displacement
            pc += 2 + (displacement if not carry else 0)
        elif op == 0x24:  # INC H
            h = (h+1) & 255
            zero, sign = h == 0, bool(h & 128)
            pc += 1
        elif op == 0x7E:  # LD A,(HL)
            address = (h << 8) | l
            if not 0x1ABF <= address < 0x1ACE:
                raise ValueError("Indexed original championship lookup escaped")
            a = m[address]
            pc += 1
        elif op == 0xC9:  # RET from 1747 only
            if not stack:
                raise ValueError("Unbalanced original course-table call")
            pc = stack.pop()
        else:
            raise ValueError(f"Unexpected original championship opcode {op:02X} at {pc:04X}")

        if stage == "initialize" and pc in (0x2953, 0x2989):
            if stack:
                raise ValueError("Unbalanced original call")
            return {
                "round_counter": ram[0xE69B], "course_index": ram[0xE699],
                "next_pc": pc, "next_call": None, "stage": stage,
            }
        if stage == "advance" and pc == ADVANCE_STOP:
            if stack:
                raise ValueError("Unbalanced original call")
            return {
                "round_counter": ram[0xE69B], "course_index": ram[0xE699],
                "next_pc": pc, "next_call": 0x2120, "stage": stage,
            }
        if not (first <= pc < last or 0x1747 <= pc <= 0x174D):
            raise ValueError(f"Original championship code escaped bounded stage: {pc:04X}")
    raise ValueError("Original championship opcode budget exceeded")


def verify(master: bytes) -> dict:
    check_original(master)
    counts = Counter()
    for stage in ("initialize", "advance"):
        for selector in range(256):
            older = (range(256) if selector < 15
                     else range(15) if selector >= 128 else ())
            for previous in older:
                expected = independent(selector, previous, stage)
                actual = opcode(master, selector, previous, stage)
                if expected != actual:
                    raise AssertionError(
                        f"Original {stage} selector={selector} old={previous}: "
                        f"independent={expected}, opcode={actual}"
                    )
                counts[stage] += 1
                counts[f"{stage}:override" if selector < 128 else f"{stage}:auto"] += 1
    return {
        "source": "Original master fixed 2936-2952, bank3 62A9-62C4",
        "cases": counts["initialize"] + counts["advance"],
        "mismatches": 0,
        "case_classes": dict(counts),
        "original_event_count": 15,
        "limitations": "Original CALL 2120 and subsequent race reset not modelled here",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path, help="Private original master.mame_runtime.bin")
    args = parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes()), indent=2))
