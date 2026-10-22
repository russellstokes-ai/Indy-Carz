#!/usr/bin/env python3
"""Original arcade master Z80 0A30-0A41 conditional input response helper.

Called by the stronger contact-event path at B728. This reproduces the exact
conditional per-car byte assignment, not an unverified game-visible damage
or speed reduction rule. Original 1991 ROM remains private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from random import Random

MASTER_HASH = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "d470099ad81e5a07fbfc417160f06ee821dc1d6cc4601a44482e747c853c0494"
START, STOP = 0x0A30, 0x0A42
# These are physical 0x100-byte state slot offsets, not IX-relative offsets.
# Original IX is 0x80 bytes into each slot: IX+$31 => slot+$B1, etc.
GATE_OFFSET, SOURCE_OFFSET, OUTPUT_OFFSET = 0xB1, 0xF7, 0xD7


def independent(slot: bytes, a: int) -> tuple[bytes, int, bool]:
    """Independent conditional response byte transformation; preserves A."""
    if len(slot) != 256 or not 0 <= a <= 255:
        raise ValueError("Original 256-byte state slot and 8-bit A required")
    result = bytearray(slot)
    active = bool(slot[GATE_OFFSET] & 1)
    if active:
        result[OUTPUT_OFFSET] = (slot[SOURCE_OFFSET] >> 1) & 0x7E
    return bytes(result), a, active


def execute_original(master: bytes, slot: bytes, a: int
                     ) -> tuple[bytes, int, bool]:
    """Boundedly execute actual original Z80 opcodes, including save/restore."""
    if len(master) != 0x90000 or len(slot) != 256 or not 0 <= a <= 255:
        raise ValueError("Original Z80 master, 256-byte slot and A required")
    state = bytearray(slot)
    save: list[int] = []
    zero = False
    changed = False
    pc = START
    for _ in range(20):
        op = master[pc]
        if op == 0xDD:
            ext = master[pc+1]
            if ext == 0xCB:  # BIT 0,(IX+$31)
                if master[pc+2:pc+4] != bytes.fromhex("3146"):
                    raise ValueError(f"Unexpected original status test {pc:04X}")
                zero = not bool(state[GATE_OFFSET] & 1)
                pc += 4
            elif ext == 0x7E:  # LD A,(IX+$77)
                if master[pc+2] != 0x77:
                    raise ValueError("Unexpected original response source offset")
                a = state[SOURCE_OFFSET]
                pc += 3
            elif ext == 0x77:  # LD (IX+$57),A
                if master[pc+2] != 0x57:
                    raise ValueError("Unexpected original response destination offset")
                state[OUTPUT_OFFSET] = a
                changed = True
                pc += 3
            else:
                raise ValueError(f"Unexpected original indexed opcode {ext:02X}")
        elif op == 0xC8:  # RET Z
            pc += 1
            if zero:
                if save:
                    raise ValueError("Original early RET leaves unbalanced stack")
                return bytes(state), a, changed
        elif op == 0xF5:  # PUSH AF
            save.append(a)
            pc += 1
        elif op == 0xCB:  # SRL A
            if master[pc+1] != 0x3F:
                raise ValueError("Unexpected original shift instruction")
            a >>= 1
            pc += 2
        elif op == 0xE6:  # AND $7E
            if master[pc+1] != 0x7E:
                raise ValueError("Unexpected original response mask")
            a &= 0x7E
            pc += 2
        elif op == 0xF1:  # POP AF
            if not save:
                raise ValueError("Original AF stack underflow")
            a = save.pop()
            pc += 1
        elif op == 0xC9:  # RET
            if pc != STOP-1 or save:
                raise ValueError("Unexpected original helper return")
            return bytes(state), a, changed
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")
        if not START <= pc < STOP:
            raise ValueError("Original helper exited without returning")
    raise ValueError("Original instruction budget exceeded")


def verify(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_HASH:
        raise ValueError("Checksum-verified original master ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Original 0A30-0A41 opcode signature changed")

    random = Random(0x0A30)
    checks = 0
    for status in range(256):
        for source in range(256):
            buffer = bytearray(random.randbytes(256))
            buffer[GATE_OFFSET], buffer[SOURCE_OFFSET] = status, source
            a = (status + source) & 255
            expected = independent(bytes(buffer), a)
            actual = execute_original(master, bytes(buffer), a)
            if expected != actual:
                raise AssertionError(f"Original response mismatch at {status},{source}")
            checks += 1

    return {
        "source": "1991 original arcade fixed master 0A30-0A41",
        "stage_sha256": STAGE_SHA, "cases": checks, "mismatches": 0,
        "unchanged_when": "physical slot+0xB1 bit0 clear",
        "updated_when": "physical slot+0xB1 bit0 set",
        "output": "physical slot+0xD7 = (physical slot+0xF7 >> 1) & 0x7E",
        "register_A": "preserved across the stage by PUSH AF/POP AF",
        "scope": "conditional collision-triggered input assignment; full effects still open",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/contact_input_gate_0a30.json"))
    args = parser.parse_args()
    report = verify(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
