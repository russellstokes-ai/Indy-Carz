#!/usr/bin/env python3
"""Original B728-B777 two-car event branch, limited to original 0971 fast return.

The original master Z80 calls 0A30 against IX even inside the IY branch;
do not "correct" that surprising pointer behaviour. This verified path
covers cases where every invoked 0971 returns immediately via RET NZ.
All other 0971 effects are deliberately rejected, not guessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from random import Random

from arcade_collision_contact_input_gate import execute_original as original_input_helper

MASTER_HASH = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
START, STOP = 0xB728, 0xB778
STAGE_SHA = "2f1cafa7bdd97f1c002be910f91fe13276b5b7336bbb641595591b0c45f2b7ff"

# Physical 0x100-byte state-slot offsets. IX/IY point 0x80 into each slot.
ACTIVE = 0xDC      # BIT 1,(IX/IY+0x5C)
GATE = 0xB1        # BIT 0,(IX+0x31); original 0971 early-RET gate
CAR_FLAGS = 0xB3   # SET 3 then RES 4 at IX/IY+0x33
CAR_FF = 0xE3      # IX/IY+0x63
SOURCE = 0xF7      # IX/IY+0x77
TARGET = 0xD7      # IX+0x57; the 0A30 call uses first IX even in IY branch


class FullHandlerUnverified(ValueError):
    """Original 0971 may continue into still-unrecovered RAM/ROM effects."""


def _validate(first: bytes, second: bytes, a: int) -> None:
    if len(first) != 256 or len(second) != 256 or not 0 <= a <= 255:
        raise ValueError("Two original physical 256-byte car slots and 8-bit A required")


def independent(first: bytes, second: bytes, a: int) -> tuple[bytes, bytes, int]:
    """Independent exact state model for bounded original fast-return domain."""
    _validate(first, second, a)
    left, right = bytearray(first), bytearray(second)
    for active_car in (left, right):
        if not active_car[ACTIVE] & 2:
            continue
        active_car[ACTIVE] = 0x30
        active_car[CAR_FF] = 255
        active_car[CAR_FLAGS] = (active_car[CAR_FLAGS] | 8) & ~16
        active_car[SOURCE] = 255

        # IMPORTANT: the original CALL 0A30 precedes the IX/IY swap needed
        # for the later CALL 0971 in the second-car case. It acts on IX.
        if left[GATE] & 1:
            left[TARGET] = (left[SOURCE] >> 1) & 0x7E

        # Only the early-RET path of 0971 is proven in this tool.
        if not active_car[GATE] & 1:
            raise FullHandlerUnverified("Full original 0971 path not yet recovered")
    return bytes(left), bytes(right), a


def execute_original(master: bytes, first: bytes, second: bytes, a: int
                     ) -> tuple[bytes, bytes, int]:
    """Bounded opcode execution, composing original 0A30 opcode interpreter.

    Implements original indexed writes/tests, relative branches, IX/IY
    pointer stack, AF save/restore and verified early exit at 0971. Fails
    closed before unverified 0971 continuation; no gameplay assumptions.
    """
    _validate(first, second, a)
    if len(master) != 0x90000:
        raise ValueError("Private original master ROM length required")
    slots = [bytes(first), bytes(second)]
    ix, iy = 0, 1
    zero = False
    saved_af: list[int] = []
    pointer_stack: list[int] = []
    pc = START
    for _ in range(70):
        op = master[pc]
        if op in (0xDD, 0xFD):
            which = ix if op == 0xDD else iy
            ext = master[pc+1]
            if ext == 0xCB:  # BIT 1 / SET 3 / RES 4
                disp, code = master[pc+2:pc+4]
                offset = 0x80 + disp
                if (disp, code) == (0x5C, 0x4E):
                    zero = not bool(slots[which][offset] & 2)
                elif (disp, code) in ((0x33, 0xDE), (0x33, 0xA6)):
                    changed = bytearray(slots[which])
                    if code == 0xDE:
                        changed[offset] |= 8
                    else:
                        changed[offset] &= ~16
                    slots[which] = bytes(changed)
                else:
                    raise ValueError(f"Unexpected original indexed CB opcode at {pc:04X}")
                pc += 4
            elif ext == 0x36:  # LD (IX/IY+d),immediate
                disp, value = master[pc+2:pc+4]
                if (disp, value) not in ((0x5C, 0x30), (0x63, 0xFF), (0x77, 0xFF)):
                    raise ValueError(f"Unexpected original indexed write at {pc:04X}")
                changed = bytearray(slots[which])
                changed[0x80+disp] = value
                slots[which] = bytes(changed)
                pc += 4
            elif ext == 0xE5:  # PUSH IX/IY
                pointer_stack.append(which)
                pc += 2
            elif ext == 0xE1:  # POP IX
                if op != 0xDD or not pointer_stack:
                    raise ValueError("Original indexed pointer stack underflow")
                ix = pointer_stack.pop()
                pc += 2
            else:
                raise ValueError(f"Unexpected original indexed opcode {ext:02X} at {pc:04X}")
        elif op == 0x28:  # JR Z
            delta = master[pc+1]
            delta = delta - 256 if delta >= 128 else delta
            pc += 2 + (delta if zero else 0)
        elif op == 0xCD:
            target = master[pc+1] | master[pc+2] << 8
            if target == 0x0A30:
                updated, new_a, _ = original_input_helper(master, slots[ix], a)
                slots[ix], a = updated, new_a
            elif target == 0x0971:
                # Actual first 5 Z80 bytes: BIT 0,(IX+31); RET NZ.
                # Never emulate the rest of 0971 with placeholder effects.
                if master[0x0971:0x0976] != bytes.fromhex("ddcb3146c0"):
                    raise ValueError("Original 0971 conditional-return prefix changed")
                if not slots[ix][GATE] & 1:
                    raise FullHandlerUnverified("Original 0971 did not early-return")
            else:
                raise ValueError(f"Unexpected original event CALL {target:04X}")
            pc += 3
        elif op == 0xF5:  # PUSH AF
            saved_af.append(a)
            pc += 1
        elif op == 0xF1:  # POP AF
            if not saved_af:
                raise ValueError("Original AF stack underflow")
            a = saved_af.pop()
            pc += 1
        elif op == 0x3E:  # LD A,0 before original 0971 helper
            if master[pc+1] != 0:
                raise ValueError("Original 0971 call argument not zero")
            a = 0
            pc += 2
        else:
            raise ValueError(f"Unexpected original Z80 collision opcode {op:02X} at {pc:04X}")

        if pc == STOP:
            if saved_af or pointer_stack or ix != 0:
                raise ValueError("Original B728 exited with unbalanced stack or IX")
            return slots[0], slots[1], a
        if not START <= pc < STOP:
            raise ValueError(f"Original B728 stage escaped to {pc:04X}")
    raise ValueError("Original event exceeded bounded instruction budget")


def verify(master: bytes, cases: int = 100000) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_HASH:
        raise ValueError("Checksum-verified original 1991 arcade master required")
    if hashlib.sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Original B728-B777 stage signature differs")
    if not 0 <= cases <= 300000:
        raise ValueError("Invalid bounded case budget")

    rng = Random(0xB728)
    branches = {"none": 0, "only_ix": 0, "only_iy": 0, "both": 0}
    for i in range(cases):
        left, right = bytearray(rng.randbytes(256)), bytearray(rng.randbytes(256))
        active_mask = i % 4
        for number, slot in enumerate((left, right)):
            slot[ACTIVE] = (slot[ACTIVE] & ~2) | ((active_mask >> number & 1) << 1)
            # Fast-return control is known precisely. Keep all active
            # original 0971 invocations within that verified domain.
            slot[GATE] |= 1
        input_a = 4+rng.randrange(124)
        reference = independent(bytes(left), bytes(right), input_a)
        machine = execute_original(master, bytes(left), bytes(right), input_a)
        if reference != machine:
            raise AssertionError(f"Original B728 mismatch case {i}, pair {active_mask:02b}")
        branches[("none", "only_ix", "only_iy", "both")[active_mask]] += 1

    return {
        "source": "1991 original fixed master B728-B777",
        "stage_sha256": STAGE_SHA, "cases": cases, "mismatches": 0,
        "original_active_pair_paths": branches,
        "0A30": "original opcode-interpreted; operates on IX even in IY branch",
        "0971": "verified original BIT0/RET NZ fast-return branch only",
        "scope": "complete B728 two-car effect path only where every invoked 0971 early-returns",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--cases", type=int, default=100000)
    args = parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(), args.cases), indent=2))


if __name__ == "__main__":
    main()
