#!/usr/bin/env python3
"""Verify original Indy Heat arcade movement arithmetic, master PC $71D9-$71F9.

This reproduces one bounded portion of the original Z80 *machine instructions*
against a separate formula using private ROM images. It does not identify the
complete movement model, coordinates, traction, AI, collisions, or fuel logic.
No original executable or assets are stored in this repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MASTER_LEN = 0x90000
XROM_LEN = 0x40000
EXPECTED_MASTER = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
EXPECTED_XROM = "1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
START = 0x71D9
END = 0x71FA


def formula(b: int, car_byte_f5: int, state_e76c: int) -> int:
    """Independent model of one ROM's signed 16-bit intermediate displacement.

    Game multiplies unsigned B by (IX-$0B), rounds, doubles modulo 256,
    then shifts left 4 and optionally two's-complement negates based on the
    sign bit of RAM address E76C. The larger movement context is unknown.
    """
    if any(not 0 <= value <= 255 for value in (b, car_byte_f5, state_e76c)):
        raise ValueError("All fields must be byte values")
    product = (b * car_byte_f5 + 128) >> 8
    unsigned = ((product << 1) & 255) << 4
    return (-unsigned if state_e76c & 0x80 else unsigned) & 0xFFFF


def original_z80_stage(master: bytes, xrom: bytes,
                       b: int, car_byte_f5: int, state_e76c: int) -> int:
    """Execute only real original instructions from $71D9 to $71F9.

    Stops at the first instruction of the next stage ($71FA).
    Every unknown/unexpected instruction fails closed.
    """
    if len(master) != MASTER_LEN or len(xrom) != XROM_LEN:
        raise ValueError("Invalid ROM region length")
    pc = START
    a = h = l = d = e = 0
    carry = sign = False
    xrom_address = 0
    for _ in range(40):
        op = master[pc]
        if op == 0x60:  # LD H,B
            h = b
            pc += 1
        elif op == 0xDD:  # LD L,(IX-$0B)
            if master[pc + 1:pc + 3] != bytes.fromhex("6ef5"):
                raise ValueError(f"Unexpected DD opcode at {pc:04X}")
            l = car_byte_f5
            pc += 3
        elif op == 0x22:  # LD ($FFFE),HL = X-ROM slot 1 address
            if master[pc + 1:pc + 3] != bytes.fromhex("feff"):
                raise ValueError("Unexpected X-ROM address register")
            xrom_address = h << 8 | l
            pc += 3
        elif op == 0x3A:  # LD A,($FFFE) or LD A,($E76C)
            address = int.from_bytes(master[pc + 1:pc + 3], "little")
            if address == 0xFFFE:
                a = xrom[0x20000 + 2 * xrom_address]
            elif address == 0xE76C:
                a = state_e76c
            else:
                raise ValueError(f"Unexpected Z80 memory address {address:04X}")
            pc += 3
        elif op == 0x87:  # ADD A,A (8-bit wrapping)
            result = a * 2
            a = result & 255
            carry, sign = result > 255, bool(a & 0x80)
            pc += 1
        elif op == 0x26:  # LD H,0
            if master[pc + 1] != 0:
                raise ValueError("Unexpected LD H constant")
            h = 0
            pc += 2
        elif op == 0x6F:  # LD L,A
            l = a
            pc += 1
        elif op == 0x29:  # ADD HL,HL
            word = ((h << 8) | l) * 2
            h, l = (word >> 8) & 255, word & 255
            carry = word > 65535
            pc += 1
        elif op == 0xEB:  # EX DE,HL
            h, l, d, e = d, e, h, l
            pc += 1
        elif op == 0xB7:  # OR A => clears carry, updates sign
            carry = False
            sign = bool(a & 0x80)
            pc += 1
        elif op == 0xF2:  # JP P,$71FA
            if master[pc + 1:pc + 3] != bytes.fromhex("fa71"):
                raise ValueError("Unexpected branch destination")
            pc = END if not sign else pc + 3
        elif op == 0x21:  # LD HL,0
            if master[pc + 1:pc + 3] != bytes.fromhex("0000"):
                raise ValueError("Unexpected LD HL constant")
            h = l = 0
            pc += 3
        elif op == 0xED:  # SBC HL,DE
            if master[pc + 1] != 0x52:
                raise ValueError("Unexpected Z80 ED opcode")
            word = (((h << 8) | l) - ((d << 8) | e) - int(carry)) & 0xFFFF
            h, l = word >> 8, word & 255
            pc += 2
        else:
            raise ValueError(f"Unsupported opcode {op:02X} at {pc:04X}")
        if pc == END:
            return (d << 8) | e
    raise ValueError("Failed to reach expected Z80 stage boundary")


def verify(master: bytes, xrom: bytes) -> dict:
    if hashlib.sha256(master).hexdigest() != EXPECTED_MASTER:
        raise ValueError("Master image does not match verified 1991 arcade region")
    if hashlib.sha256(xrom).hexdigest() != EXPECTED_XROM:
        raise ValueError("X-ROM image does not match verified 1991 arcade region")
    cases = 0
    for b in range(256):
        for car_byte in range(256):
            for sign_value in (0, 0x80):
                expected = formula(b, car_byte, sign_value)
                observed = original_z80_stage(master, xrom, b, car_byte, sign_value)
                if observed != expected:
                    raise AssertionError(
                        f"B={b}, IX-0B={car_byte}, E76C={sign_value}: "
                        f"original={observed:04X}, formula={expected:04X}"
                    )
                cases += 1
    return {
        "machine": "1991 Indy Heat arcade master Z80",
        "stage_start_pc": "71D9",
        "stage_end_pc_exclusive": "71FA",
        "cases": cases,
        "arithmetic_mismatches": 0,
        "formula": "signed16(((((B * (IX-0B) + 128) >> 8) * 2) & 255) << 4, sign=E76C[7])",
        "status": "arithmetic stage verified, complete motion/collision model NOT recovered",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path, help="Private MAME-rotated master region")
    p.add_argument("xrom", type=Path, help="Private interleaved X-ROM region")
    p.add_argument("--out", type=Path,
                   default=Path("local/recovery/displacement_opcode_parity.json"))
    args = p.parse_args()
    results = verify(args.master.read_bytes(), args.xrom.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
