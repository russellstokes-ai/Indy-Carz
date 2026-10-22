#!/usr/bin/env python3
"""Reproduce original arcade pedal stage using bounded opcode execution.

Input: privately reconstructed master and X-ROM images from user-owned set.
No ROMs are committed. Only original Z80 $67B5-$67D5 input path is covered;
neither the upstream poll loop nor downstream car acceleration is tested.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def pedal_formula(raw: int, factor: int, bias: int) -> int:
    """Independently recovered 8-bit X-ROM multiplier + threshold/saturation."""
    product = (raw * factor + 128) >> 8
    sum_value = product + bias
    if sum_value < 256:
        return 0
    return min((sum_value - 256) * 2, 0x7E)


def execute_original_pedal(master: bytes, xrom: bytes,
                           raw: int, factor: int, bias: int) -> int:
    """Run only Z80 opcodes actually reached from arcade bank 0 $67B5."""
    pc = 0x67B5
    a = h = l = xrom_addr = 0
    carry = sign = False
    car = {0x58: factor, 0x59: bias}

    def byte(address: int) -> int:
        return master[address]

    def add(left: int, right: int) -> tuple[int, bool, bool]:
        value = left + right
        return value & 255, value > 255, bool(value & 0x80)

    for _ in range(30):
        op = byte(pc)
        if op == 0xDB:
            if byte(pc + 1) != 0x09:
                raise ValueError("Unexpected input port")
            a = raw
            pc += 2
        elif op == 0xFB:
            pc += 1
        elif op == 0x67:
            h = a
            pc += 1
        elif op == 0xDD:
            ext, offset = byte(pc + 1), byte(pc + 2)
            if ext == 0x6E:
                l = car[offset]
            elif ext == 0x86:
                a, carry, sign = add(a, car[offset])
            elif ext == 0x77:
                if offset != 0x57:
                    raise ValueError("Unexpected original car-state destination")
                return a
            else:
                raise ValueError(f"Unexpected indexed opcode {ext:02X}")
            pc += 3
        elif op == 0x22:
            dest = byte(pc + 1) | (byte(pc + 2) << 8)
            if dest != 0xFFFE:
                raise ValueError("Wrong original X-ROM write port")
            xrom_addr = (h << 8) | l
            pc += 3
        elif op == 0x3A:
            src = byte(pc + 1) | (byte(pc + 2) << 8)
            if src != 0xFFFE:
                raise ValueError("Wrong original X-ROM read port")
            a = xrom[0x20000 + 2 * xrom_addr]
            pc += 3
        elif op in (0x30, 0x38, 0x18):
            d = byte(pc + 1)
            if d >= 128:
                d -= 256
            jump = op == 0x18 or (op == 0x30 and not carry) or (op == 0x38 and carry)
            pc = pc + 2 + d if jump else pc + 2
        elif op == 0xF2:
            target = byte(pc + 1) | byte(pc + 2) << 8
            pc = target if not sign else pc + 3
        elif op == 0x87:
            a, carry, sign = add(a, a)
            pc += 1
        elif op == 0x3E:
            a = byte(pc + 1)
            pc += 2
        elif op == 0xAF:
            a, carry, sign = 0, False, False
            pc += 1
        else:
            raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
    raise ValueError("Original pedal stage exceeded instruction budget")


def parity(master: bytes, xrom: bytes) -> dict:
    if len(master) != 0x90000 or len(xrom) != 0x40000:
        raise ValueError("Original master and X-ROM memory dimensions required")

    multiply_matches = 0
    for raw in range(256):
        for factor in range(256):
            expected = (raw * factor + 128) >> 8
            original = xrom[0x20000 + 2 * ((raw << 8) | factor)]
            if expected != original:
                raise AssertionError(
                    f"X-ROM multiply mismatch {raw}, {factor}: {expected} != {original}")
            multiply_matches += 1

    cases = [(raw, factor, bias)
             for raw in range(256)
             for factor, bias in (
                 (0, 0), (64, 254), (127, 250),
                 (128, 220), (180, 255), (255, 254),
             )]
    generator = random.Random(1109)
    cases.extend((generator.randrange(256), generator.randrange(256),
                  generator.randrange(256)) for _ in range(40000))
    for raw, factor, bias in cases:
        expected = pedal_formula(raw, factor, bias)
        original = execute_original_pedal(master, xrom, raw, factor, bias)
        if expected != original:
            raise AssertionError(
                f"Pedal mismatch raw={raw} gain={factor} bias={bias}: "
                f"formula={expected}, opcode={original}")

    return {
        "result": "complete parity for tested normal pedal-input opcode stage",
        "xrom_multiplication_table_cells": multiply_matches,
        "pedal_opcode_cases": len(cases),
        "mismatches": 0,
        "source": "original 1991 Indy Heat arcade Z80 master $67B5-$67D5",
        "state_written": "IX+$57",
        "not_yet_verified": "poll timeout timing, gain/bias acquisition, car acceleration",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path)
    p.add_argument("xrom", type=Path)
    p.add_argument("--out", type=Path,
                   default=Path("local/recovery/pedal_opcode_parity.json"))
    args = p.parse_args()
    result = parity(args.master.read_bytes(), args.xrom.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
