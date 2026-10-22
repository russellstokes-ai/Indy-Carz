#!/usr/bin/env python3
"""Authentic Z80 7D65–7E35 special-centre/angle/speed smoothing.

Five fixed-point projections use the exhaustively proven signed slot0
X-ROM multiplier, including the second lookup via FFFD high latch. An
independent arithmetic model is checked against private authentic Z80
instructions. Original executable bytes/X-ROM are NOT redistributed.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

from arcade_drive_709c_speed import slot0_word

START, STOP, RETURN_PC = 0x7D65, 0x7E36, 0x7024
MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "520a88bae57f74b059dc1590b17462be31a5ce52714f004362a93c96e205b240"


def _check(ix_y: int, ix_x: int, y: int, x: int,
           e93b: int, e767: int, e769: int, e76b: int, e765: int) -> None:
    if not 0 <= e93b <= 255 or any(not 0 <= v <= 65535 for v in
        (ix_y, ix_x, y, x, e767, e769, e76b, e765)):
        raise ValueError("Original 7D65 inputs must be 16-bit words and E93B byte")


def _project(original_difference: int, factor: int) -> int:
    """Independent two-slot0 reconstruction of the original mixed-word delta."""
    first = slot0_word(original_difference >> 8, factor)
    second_high = slot0_word((original_difference & 255) >> 1, factor) >> 8
    low_sum = (((second_high << 1) & 255) + (first & 255))
    high = ((first >> 8) - int(bool(second_high & 128)) + int(low_sum > 255)) & 255
    return (high << 8) | (low_sum & 255)


def _result(y: int, x: int, e767: int, e76b: int, e765: int) -> dict:
    return {"branch": "smooth_7024", "next_pc": RETURN_PC,
            "y": y, "x": x, "e767": e767, "e769": e767,
            "e76b": e76b, "e765": e765}


def independent(ix_y: int, ix_x: int, y: int, x: int,
                e93b: int, e767: int, e769: int, e76b: int, e765: int) -> dict:
    """Model independent of actual original instruction decoding."""
    _check(ix_y, ix_x, y, x, e93b, e767, e769, e76b, e765)
    y = (y + _project((ix_y - y) & 65535, 0x10)) & 65535
    x = (x + _project((ix_x - x) & 65535, 0x10)) & 65535
    e767 = (e767 + _project(((e93b << 8) - e767) & 65535, 0x0C)) & 65535
    e76b = (e76b - _project(e76b, 0x0C)) & 65535
    e765 = (e765 - _project(e765, 0x0C)) & 65535
    return _result(y, x, e767, e76b, e765)


def original_opcodes(master: bytes, ix_y: int, ix_x: int, y: int, x: int,
                     e93b: int, e767: int, e769: int, e76b: int, e765: int) -> dict:
    """Interpret REAL original bounded 7D65–7E35 Z80 instructions.

    Hardware FFFC/FFFD are emulated as one signed 8×8 doubled X-ROM
    lookup with the actual high-address rewrite and result-high read.
    """
    if len(master) != 0x90000 or sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Authenticated original 7D65 ROM window required")
    _check(ix_y, ix_x, y, x, e93b, e767, e769, e76b, e765)
    state = {0xE72B: y, 0xE735: x, 0xE767: e767,
             0xE769: e769, 0xE76B: e76b, 0xE765: e765}
    indexed = {0x65: ix_y & 255, 0x66: ix_y >> 8,
               0x67: ix_x & 255, 0x68: ix_x >> 8}
    pc = START
    a = h = l = d = e = 0
    carry = zero = False
    xrom_address = 0

    def byte(offset: int = 0) -> int:
        return master[pc + offset]

    def word() -> int:
        return byte(1) | (byte(2) << 8)

    for _ in range(125):
        if not START <= pc < STOP:
            raise ValueError(f"Original smoothing PC escaped: {pc:04X}")
        op = byte()
        if op == 0xDD:  # LD H/L,(IX+disp), preserving non-destination regs
            suffix, disp = byte(1), byte(2)
            if disp not in indexed:
                raise ValueError("Unknown original IX smoothing offset")
            if suffix == 0x66:
                h = indexed[disp]
            elif suffix == 0x6E:
                l = indexed[disp]
            else:
                raise ValueError("Unexpected original IX smoothing opcode")
            pc += 3
        elif op == 0xED:  # LD DE,(nn) or SBC HL,DE
            suffix = byte(1)
            if suffix == 0x5B:
                address = byte(2) | (byte(3) << 8)
                if address not in state:
                    raise ValueError("Unexpected original RAM word source")
                value = state[address]
                d, e = value >> 8, value & 255
                pc += 4
            elif suffix == 0x52:
                raw = ((h << 8) | l) - ((d << 8) | e) - int(carry)
                value = raw & 65535
                h, l = value >> 8, value & 255
                carry, zero = raw < 0, value == 0
                pc += 2
            else:
                raise ValueError("Unknown original ED smoothing instruction")
        elif op == 0xB7:  # OR A: clears carry
            carry, zero = False, a == 0
            pc += 1
        elif op == 0x7D:  # LD A,L
            a = l
            pc += 1
        elif op == 0x2E:  # LD L,n
            l = byte(1)
            pc += 2
        elif op == 0x67:  # LD H,A
            h = a
            pc += 1
        elif op == 0x54:  # LD D,H
            d = h
            pc += 1
        elif op == 0x5D:  # LD E,L
            e = l
            pc += 1
        elif op == 0x22:  # LD (nn),HL
            dest = word()
            value = (h << 8) | l
            if dest == 0xFFFC:
                xrom_address = value
            elif dest in state:
                state[dest] = value
            else:
                raise ValueError("Unknown original RAM destination")
            pc += 3
        elif op == 0x2A:  # LD HL,(nn)
            address = word()
            if address == 0xFFFC:
                value = slot0_word(xrom_address >> 8, xrom_address & 255)
            elif address in state:
                value = state[address]
            else:
                raise ValueError("Unknown original RAM/X-ROM read")
            h, l = value >> 8, value & 255
            pc += 3
        elif op == 0xCB:  # SRL A
            if byte(1) != 0x3F:
                raise ValueError("Unknown CB prefix in original smoothing")
            carry, a = bool(a & 1), a >> 1
            zero = a == 0
            pc += 2
        elif op == 0x32:  # LD (FFFD),A: replace high X-ROM address
            if word() != 0xFFFD:
                raise ValueError("Unknown original byte write")
            xrom_address = (a << 8) | (xrom_address & 255)
            pc += 3
        elif op == 0x3A:  # LD A,(FFFD) or from E93B
            address = word()
            if address == 0xFFFD:
                a = slot0_word(xrom_address >> 8, xrom_address & 255) >> 8
            elif address == 0xE93B:
                a = e93b
            else:
                raise ValueError("Unknown original byte read")
            pc += 3
        elif op == 0x87:  # ADD A,A
            raw = a + a
            a, carry = raw & 255, raw > 255
            zero = a == 0
            pc += 1
        elif op == 0x85:  # ADD A,L
            raw = a + l
            a, carry = raw & 255, raw > 255
            zero = a == 0
            pc += 1
        elif op == 0x30:  # JR NC,+1
            if byte(1) != 1:
                raise ValueError("Unknown original JR NC target")
            pc += 2 + (1 if not carry else 0)
        elif op == 0x25:  # DEC H: flags except carry
            h = (h - 1) & 255
            zero = h == 0
            pc += 1
        elif op == 0x24:  # INC H: flags except carry
            h = (h + 1) & 255
            zero = h == 0
            pc += 1
        elif op == 0x6F:  # LD L,A
            l = a
            pc += 1
        elif op == 0x19:  # ADD HL,DE
            value = ((h << 8) | l) + ((d << 8) | e)
            h, l, carry = (value >> 8) & 255, value & 255, value > 65535
            pc += 1
        elif op == 0xEB:  # EX DE,HL
            d, e, h, l = h, l, d, e
            pc += 1
        elif op == 0xC9:  # Actual RET to caller at 7024
            if pc != 0x7E35:
                raise ValueError("Unexpected original smoothing RET")
            return _result(state[0xE72B], state[0xE735], state[0xE767],
                           state[0xE76B], state[0xE765])
        else:
            raise ValueError(f"Unsupported original 7D65 opcode {op:02X} at {pc:04X}")
    raise ValueError("Original 7D65 exceeded 125 bounded instructions")


def verify_original(master: bytes, cases: int = 100000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Authenticated private master ROM required")
    if not 0 <= cases <= 250000:
        raise ValueError("Invalid original smoothing verification budget")
    random = Random(0x7D657E35)
    parity_count = 0
    for index in range(cases):
        fields = (random.choice((0, 1, 0x7FFF, 0x8000, 0xFFFF, random.randrange(65536))),
                  random.randrange(65536), random.randrange(65536),
                  random.randrange(65536), random.randrange(256),
                  random.randrange(65536), random.randrange(65536),
                  random.choice((0, 1, 0x7FFF, 0x8000, 0xFFFF, random.randrange(65536))),
                  random.randrange(65536))
        actual = original_opcodes(master, *fields)
        expected = independent(*fields)
        if actual != expected:
            raise AssertionError(f"Original 7D65 mismatch {index} {fields}: {actual} != {expected}")
        parity_count += 1
    return {"source": "Original owner Z80 bank0 7D65–7E35",
            "original_z80_cases": parity_count, "mismatches": 0,
            "branches": {"smooth_7024": parity_count},
            "return_continuation": "7024 JP 7572 geometry without 7530 motion",
            "scope": "one original 7D4C call, not a full game frame"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_master", type=Path)
    parser.add_argument("--cases", type=int, default=100000)
    args = parser.parse_args()
    print(json.dumps(verify_original(args.private_master.read_bytes(), args.cases), indent=2))
