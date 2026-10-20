#!/usr/bin/env python3
"""Verify original Indy Heat arcade eight-corner vehicle-geometry stage.

Master bank0 PC 7572..75F1 calculates eight 16-bit coordinates using original
angle tables and XROM-free signed byte arithmetic. This stage is a candidate
rotated car footprint; actual collision detection/response remain unverified.
Requires local private master ROM data; no original code or assets are shipped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from arcade_coordinate_opcode_parity import arcade_trig

EXPECTED_MASTER = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
START, RETURN = 0x7572, 0x75F1
CORNERS = (0xE72D, 0xE72F, 0xE731, 0xE733, 0xE737, 0xE739, 0xE73B, 0xE73D)


def model_corners(angle: int, x: int, y: int) -> dict[int, int]:
    if not (0 <= angle < 256 and 0 <= x < 65536 and 0 <= y < 65536):
        raise ValueError("Original angle/coordinates outside byte/word limits")
    sine = arcade_trig(angle, True)
    cosine = arcade_trig(angle, False)
    return {
        0xE73D: (x + 3*sine - 2*cosine) & 0xFFFF,
        0xE737: (x - 3*sine + 2*cosine) & 0xFFFF,
        0xE73B: (x + 3*sine + 2*cosine) & 0xFFFF,
        0xE739: (x - 3*sine - 2*cosine) & 0xFFFF,
        0xE733: (y + 3*cosine + 2*sine) & 0xFFFF,
        0xE72D: (y - 3*cosine - 2*sine) & 0xFFFF,
        0xE731: (y + 3*cosine - 2*sine) & 0xFFFF,
        0xE72F: (y - 3*cosine + 2*sine) & 0xFFFF,
    }


def execute_original(master: bytes, angle: int, x: int, y: int) -> dict[int, int]:
    """Bounded Z80 execution, all unknown opcodes/memory fail closed."""
    if len(master) != 0x90000:
        raise ValueError("Original MAME-rotated master ROM region required")
    pc = START
    a = b = c = d = e = h = l = carry = 0
    stack: list[int] = []
    ram = {0xE768: angle, 0xE735: x, 0xE72B: y}
    for _ in range(150):
        op = master[pc]
        if op == 0x3A:  # LD A,(nn)
            address = master[pc+1] | (master[pc+2] << 8)
            a = ram[address]; pc += 3
        elif op == 0x6F:
            l = a; pc += 1
        elif op == 0x26:
            h = master[pc+1]; pc += 2
        elif op == 0x4E:  # LD C,(HL)
            c = master[(h << 8) | l]; pc += 1
        elif op == 0x5E:  # LD E,(HL)
            e = master[(h << 8) | l]; pc += 1
        elif op == 0xAF:
            a = carry = 0; pc += 1
        elif op == 0x9F:  # SBC A,A
            a = 255 if carry else 0; pc += 1
        elif op == 0x47:
            b = a; pc += 1
        elif op == 0x57:
            d = a; pc += 1
        elif op == 0x60:
            h = b; pc += 1
        elif op == 0x69:
            l = c; pc += 1
        elif op == 0x62:
            h = d; pc += 1
        elif op == 0x6B:
            l = e; pc += 1
        elif op == 0xCB:
            extra = master[pc+1]
            if extra in (0x21, 0x23):  # SLA C or SLA E
                previous = c if extra == 0x21 else e
                carry, changed = int(bool(previous & 128)), (previous << 1) & 255
                if extra == 0x21:
                    c = changed
                else:
                    e = changed
            elif extra == 0x2C:  # SRA H
                carry, h = h & 1, (h >> 1) | (h & 128)
            elif extra == 0x1D:  # RR L
                previous = l
                l, carry = (l >> 1) | (carry << 7), previous & 1
            else:
                raise ValueError(f"Unexpected CB prefix {extra:02X} at {pc:04X}")
            pc += 2
        elif op == 0xED:
            extra = master[pc+1]
            hl = h << 8 | l
            if extra in (0x4A, 0x42):
                operand = b << 8 | c
            elif extra in (0x5A, 0x52):
                operand = d << 8 | e
            else:
                raise ValueError(f"Unexpected ED prefix {extra:02X} at {pc:04X}")
            if extra in (0x4A, 0x5A):  # ADC HL, BC or DE
                result = hl + operand + carry
                carry = int(result > 65535)
            else:  # SBC HL, BC or DE
                result = hl - operand - carry
                carry = int(result < 0)
            result &= 0xFFFF
            h, l = result >> 8, result & 255
            pc += 2
        elif op == 0x22:  # LD (nn),HL
            address = master[pc+1] | (master[pc+2] << 8)
            ram[address] = h << 8 | l
            pc += 3
        elif op == 0x2A:  # LD HL,(nn)
            address = master[pc+1] | (master[pc+2] << 8)
            value = ram[address]
            h, l = value >> 8, value & 255
            pc += 3
        elif op in (0x19, 0x09):  # ADD HL,DE or BC
            operand = (d << 8 | e) if op == 0x19 else (b << 8 | c)
            result = (h << 8 | l) + operand
            carry = int(result > 65535)
            result &= 65535
            h, l = result >> 8, result & 255
            pc += 1
        elif op == 0xEB:  # EX DE,HL
            h, l, d, e = d, e, h, l
            pc += 1
        elif op == 0xE5:
            stack.append(h << 8 | l); pc += 1
        elif op == 0xD1:
            value = stack.pop()
            d, e = value >> 8, value & 255
            pc += 1
        elif op == 0xB7:  # OR A clears carry
            carry = 0; pc += 1
        elif op == 0xC9:
            if pc != RETURN or stack:
                raise ValueError("Unexpected original return or unbalanced stack")
            return {address: ram[address] for address in CORNERS}
        else:
            raise ValueError(f"Unexpected Z80 opcode {op:02X} at PC {pc:04X}")
        if not START <= pc <= RETURN:
            raise ValueError("Original code left the bounded geometry stage")
    raise ValueError("Original geometry update exceeded opcode budget")


def verify(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != EXPECTED_MASTER:
        raise ValueError("Original privately reconstructed 1991 arcade master ROM required")
    cases = 0
    for angle in range(256):
        for sample in range(256):
            x, y = (angle << 8) | sample, (sample << 8) | angle
            expected = model_corners(angle, x, y)
            observed = execute_original(master, angle, x, y)
            if expected != observed:
                raise AssertionError(f"Original corner disagreement angle={angle} sample={sample}")
            cases += 1
    return {
        "original": "1991 arcade Indy Heat master Z80 bank0 PC 7572..75F1",
        "unique_angles_checked": 256,
        "original_opcode_cases": cases,
        "sixteen_bit_coordinates_compared": cases * len(CORNERS),
        "mismatches": 0,
        "coordinate_input": ["E768: high byte of 16-bit E767 angular state",
                             "E735: first 16-bit position-like accumulator",
                             "E72B: second 16-bit position-like accumulator"],
        "formula": "four symmetric 16-bit coordinate pairs, offsets 3*sin±2*cos and 3*cos±2*sin",
        "status": "geometry stage recovered; collision checks and impact response remain outstanding",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path, help="Private master.mame_runtime.bin")
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/arcade_geometry_opcode_parity.json"))
    args = parser.parse_args()
    result = verify(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
