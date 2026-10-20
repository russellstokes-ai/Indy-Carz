#!/usr/bin/env python3
"""Original arcade master Z80 0971-0984 entry: three verified early returns.

The longer continuation at 0985 is NOT reconstructed. Any input reaching
it raises FullHandlerUnverified instead of inventing gameplay or CPU effects.
This public code contains independent byte maths and a bounded original
instruction interpreter, not user-owned ROM binaries or disassembly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from random import Random

MASTER_HASH = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "9cf5938e82faad23619e335977fcc5c4c553dc6b3a280399d0abe3e3ed4c9233"
START, STOP = 0x0971, 0x0985

# Original IX pointer sits 0x80 bytes into the physical 0x100-byte slot.
GATE = 0xB1         # IX+0x31
OUTPUT = 0xCE       # IX+0x4E
THRESHOLD = 0x7D    # IX-0x03
SECOND_GATE = 0xA3  # IX+0x23


class FullHandlerUnverified(ValueError):
    """Original helper continues beyond its three verified early exits."""


def independent(slot: bytes, accumulator: int, initial_b: int = 0) -> tuple[bytes, int, int, str]:
    """(whole slot, A, B, exit label) using independently recovered tests."""
    if len(slot) != 256 or not 0 <= accumulator <= 255 or not 0 <= initial_b <= 255:
        raise ValueError("Original 256-byte slot and 8-bit A/B required")
    if slot[GATE] & 1:
        return slot, accumulator, initial_b, "ret_at_0975"

    changed = bytearray(slot)
    changed[OUTPUT] = accumulator
    b = accumulator
    if slot[THRESHOLD] >= 3:
        return bytes(changed), slot[THRESHOLD], b, "ret_at_097F"
    if slot[SECOND_GATE] != 0:
        return bytes(changed), slot[SECOND_GATE], b, "ret_at_0984"
    raise FullHandlerUnverified(
        "Original 0971 continues at 0985; complete downstream effects unknown"
    )


def execute_original(master: bytes, slot: bytes, accumulator: int,
                     initial_b: int = 0) -> tuple[bytes, int, int, str]:
    """Execute all original opcodes from 0971 until one verified return.

    The real indexed status/read/write offsets and Z80 CP/RET flags are
    interpreted directly from the supplied original executable. No slow
    path beyond 0984 is emulated.
    """
    if (len(master) != 0x90000 or len(slot) != 256 or not 0 <= accumulator <= 255
            or not 0 <= initial_b <= 255):
        raise ValueError("Original master Z80, slot and 8-bit A required")
    state = bytearray(slot)
    a, b = accumulator, initial_b
    zero = carry = False
    pc = START
    for _ in range(16):
        opcode = master[pc]
        if opcode == 0xDD:
            ext = master[pc+1]
            if ext == 0xCB:  # BIT 0,(IX+0x31)
                if master[pc+2:pc+4] != bytes.fromhex("3146"):
                    raise ValueError("Unexpected original 0971 status BIT instruction")
                zero = not bool(state[GATE] & 1)
                pc += 4
            elif ext == 0x77:  # LD (IX+0x4E),A
                if master[pc+2] != 0x4E:
                    raise ValueError("Unexpected original 0971 write offset")
                state[OUTPUT] = a
                pc += 3
            elif ext == 0x7E:  # LD A,(IX-0x03) / (IX+0x23)
                offset = master[pc+2]
                if offset == 0xFD:
                    a = state[THRESHOLD]
                elif offset == 0x23:
                    a = state[SECOND_GATE]
                else:
                    raise ValueError("Unexpected original 0971 source offset")
                pc += 3
            else:
                raise ValueError(f"Unexpected original indexed opcode {ext:02X}")
        elif opcode == 0xC0:  # RET NZ
            site = pc
            pc += 1
            if not zero:
                return (bytes(state), a, b,
                        "ret_at_0975" if site == 0x0975 else "ret_at_0984")
        elif opcode == 0x47:  # LD B,A
            b = a
            pc += 1
        elif opcode == 0xFE:  # CP unsigned 3
            if master[pc+1] != 3:
                raise ValueError("Unexpected original 0971 comparison threshold")
            difference = a - 3
            carry, zero = difference < 0, difference == 0
            pc += 2
        elif opcode == 0xD0:  # RET NC
            if not carry:
                return bytes(state), a, b, "ret_at_097F"
            pc += 1
        elif opcode == 0xB7:  # OR A
            zero, carry = a == 0, False
            pc += 1
        else:
            raise ValueError(f"Unexpected original Z80 opcode {opcode:02X} at {pc:04X}")

        if pc == STOP:
            raise FullHandlerUnverified("Original 0971 reached 0985 slow path")
        if not START <= pc < STOP:
            raise ValueError("Original 0971 left bounded stage unexpectedly")
    raise ValueError("Original 0971 exceeded bounded opcode budget")


def verify(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_HASH:
        raise ValueError("Original checksum-verified master ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Original 0971 entry opcode signature changed")

    rng = Random(0x0971)
    exits = {"ret_at_0975": 0, "ret_at_097F": 0,
             "ret_at_0984": 0, "unverified_0985": 0}
    for status_bit in (0, 1):
        for threshold in range(256):
            for secondary in range(256):
                slot = bytearray(rng.randbytes(256))
                slot[GATE] = (slot[GATE] & ~1) | status_bit
                slot[THRESHOLD], slot[SECOND_GATE] = threshold, secondary
                initial_a = (threshold + secondary) & 255
                initial_b = (threshold ^ secondary) & 255

                try:
                    expected = independent(bytes(slot), initial_a, initial_b)
                except FullHandlerUnverified:
                    try:
                        execute_original(master, bytes(slot), initial_a, initial_b)
                    except FullHandlerUnverified:
                        exits["unverified_0985"] += 1
                        continue
                    raise AssertionError("Original 0971 returned but model did not")

                actual = execute_original(master, bytes(slot), initial_a, initial_b)
                if actual != expected:
                    raise AssertionError(
                        f"Original 0971 mismatch bit={status_bit}, "
                        f"threshold={threshold}, secondary={secondary}"
                    )
                exits[expected[3]] += 1

    return {
        "source": "1991 original arcade master Z80 0971-0984",
        "stage_sha256": STAGE_SHA,
        "exhaustive_input_cases": 2*256*256,
        "verified_return_cases": sum(v for k,v in exits.items() if k != "unverified_0985"),
        "unverified_continuation_cases": exits["unverified_0985"],
        "mismatches": 0,
        "original_exit_counts": exits,
        "write_if_bit0_clear": "physical slot+0xCE = input A",
        "exit1": "slot+0xB1 bit0 set (no write)",
        "exit2": "unsigned slot+0x7D >= 3",
        "exit3": "slot+0xA3 nonzero",
        "open": "original 0985 onward, including graphics/data transfer and live race effects",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes()), indent=2))


if __name__ == "__main__":
    main()
