#!/usr/bin/env python3
"""Bounded opcode parity test for two original Indy Heat steering stages.

Runs the original verified 1991 arcade Z80 instruction bytes from private
local reconstructed images. No ROM/disassembly data is included in GitHub.
Stops at the FIRST write to indexed car-state offset $7B. Does NOT emulate
collision callbacks, whole vehicle physics, MAME video or AI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from arcade_logic_probe import steering_table
from arcade_steering_xrom import xrom_steering_sample


def model_stage(mode: int, signed_steer: int, state: int, xrom: bytes) -> tuple[int, bool]:
    """Independent arithmetic reconstruction of $341E or bank-3 $7519."""
    if mode == 0:
        xrom_hi = xrom_steering_sample(xrom, signed_steer)["xrom_high_byte"]
        drive, bias = (xrom_hi * 2) & 255, 4
    elif mode == 3:
        drive, bias = (signed_steer * 2) & 255, 8
    else:
        raise ValueError("Only the two identified arcade paths are implemented")
    summed = drive + state
    result, carry = summed & 255, summed > 255
    negative = bool(drive & 0x80)
    overflow_branch = (negative and not carry) or (not negative and carry)
    if overflow_branch:
        return result ^ 0x80, True
    return ((result - bias) if result & 0x80 else (result + bias)) & 255, False


def execute_original(master: bytes, xrom: bytes,
                     mode: int, steer: int, state: int) -> tuple[int, bool]:
    """Emulate only actual encountered Z80 instructions, fail closed otherwise."""
    if mode == 0:
        pc, base, car = 0x341E, 0x2000, {0x7A: steer & 255, 0x7B: state}
    elif mode == 3:
        pc, base, car = 0x7519, 0x28000, {0x79: steer & 255, 0x7B: state}
    else:
        raise ValueError(mode)
    a = h = l = b = xrom_address = 0
    sign = carry = False

    def read(addr: int) -> int:
        return master[addr if addr < 0x2000 else base + addr - 0x2000]

    def add(x: int, y: int) -> tuple[int, bool, bool]:
        value = x + y
        return value & 255, value > 255, bool(value & 0x80)

    for _ in range(40):
        op = read(pc)
        if op == 0xDD:
            ext, offset = read(pc + 1), read(pc + 2)
            if ext == 0x66:
                h = car[offset]
            elif ext == 0x7E:
                a = car[offset]
            elif ext == 0x86:
                a, carry, sign = add(a, car[offset])
            elif ext == 0x77:
                car[offset] = a
                if offset == 0x7B:
                    return a, (pc in (0x344B, 0x753A, 0x754D))
            else:
                raise ValueError(f"Unexpected indexed opcode {ext:02X} at {pc:04X}")
            pc += 3
        elif op == 0x2E:
            l = read(pc + 1)
            pc += 2
        elif op == 0x22:
            dest = read(pc + 1) | read(pc + 2) << 8
            if dest != 0xFFFC:
                raise ValueError(f"Unexpected X-ROM write {dest:04X}")
            xrom_address = (h << 8) | l
            pc += 3
        elif op == 0x3A:
            source = read(pc + 1) | read(pc + 2) << 8
            if source != 0xFFFD:
                raise ValueError(f"Unexpected X-ROM read {source:04X}")
            a = xrom[xrom_address * 2 + 1]
            pc += 3
        elif op == 0x87:
            a, carry, sign = add(a, a)
            pc += 1
        elif op == 0x06:
            b = read(pc + 1)
            pc += 2
        elif op == 0xC6:
            a, carry, sign = add(a, read(pc + 1))
            pc += 2
        elif op == 0xD6:
            operand = read(pc + 1)
            carry = a < operand
            a = (a - operand) & 255
            sign = bool(a & 128)
            pc += 2
        elif op == 0xEE:
            a ^= read(pc + 1)
            carry = False
            sign = bool(a & 128)
            pc += 2
        elif op in (0xFA, 0xF2):
            target = read(pc + 1) | read(pc + 2) << 8
            pc = target if (sign if op == 0xFA else not sign) else pc + 3
        elif op in (0x18, 0x38, 0x30):
            displacement = read(pc + 1)
            if displacement > 127:
                displacement -= 256
            taken = op == 0x18 or (op == 0x38 and carry) or (op == 0x30 and not carry)
            pc = pc + 2 + displacement if taken else pc + 2
        else:
            raise ValueError(f"Opcode {op:02X} not implemented at {pc:04X}")
    raise ValueError(f"Runaway original stage: mode={mode} pc={pc:04X}")


def parity(master: bytes, xrom: bytes) -> dict:
    if len(master) != 0x90000 or len(xrom) != 0x40000:
        raise ValueError("Original MAME runtime region dimensions not matched")
    lookup = steering_table(master)
    signed_samples = sorted(set([-n for n in lookup] + lookup))
    checks = boundary = 0
    for mode in (0, 3):
        for sample in signed_samples:
            for state in range(256):
                expected = model_stage(mode, sample, state, xrom)
                actual = execute_original(master, xrom, mode, sample, state)
                if expected != actual:
                    raise AssertionError(
                        f"Mismatch mode={mode}, input={sample}, state={state}: "
                        f"expected={expected}, opcode={actual}")
                checks += 1
                boundary += actual[1]
    return {
        "status": "Matched original opcode execution to arithmetic reconstruction",
        "cases": checks, "mismatches": 0,
        "boundary_branch_cases": boundary,
        "signed_samples": len(signed_samples),
        "paths": ["master bank0 $341E", "master bank3 $7519"],
        "scope": "First write to IX+$7B only; not full vehicle or collision simulation",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path)
    p.add_argument("xrom", type=Path)
    p.add_argument("--out", type=Path,
                   default=Path("local/recovery/steering_opcode_parity.json"))
    args = p.parse_args()
    results = parity(args.master.read_bytes(), args.xrom.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
