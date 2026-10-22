#!/usr/bin/env python3
"""Verify original Indy Heat 7039/709C drive-byte stages, local ROM only.

Reconstructs original Z80 instructions for two bounded X-ROM arithmetic
stages without shipping ROM data. Neither stage constitutes complete vehicle
physics and no collision/speed model is assumed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

MASTER_BYTES = 0x90000
XROM_BYTES = 0x40000


def original_flagged_lookup(master: bytes, xrom: bytes, value: int) -> int:
    # Excludes the preceding IX-$1D counter update at 7036.
    expected = bytes.fromhex("60 2e 60 22 fe ff 3a fe ff 47")
    if master[0x7039:0x7043] != expected:
        raise ValueError("Original 7039 branch opcode signature mismatch")
    return xrom[0x20000 + 2 * ((value << 8) | 0x60)]


def original_weighted_stage(master: bytes, xrom: bytes, value: int, field_54: int) -> int:
    pc, a, b, h, l, carry = 0x709C, 0, value, 0, 0, False
    for _ in range(12):
        op = master[pc]
        if op == 0x60:  # LD H,B
            h = b
            pc += 1
        elif op == 0x2E:  # LD L,0xa6
            l = master[pc + 1]
            pc += 2
        elif op == 0x22:  # LD (0xfffe),HL, X-ROM slot 1 address
            dest = master[pc + 1] | (master[pc + 2] << 8)
            if dest != 0xFFFE:
                raise ValueError("Unexpected X-ROM address register")
            pc += 3
        elif op == 0x3A:  # LD A,(0xfffe), X-ROM slot 1 low byte
            dest = master[pc + 1] | (master[pc + 2] << 8)
            if dest != 0xFFFE:
                raise ValueError("Unexpected X-ROM value register")
            a = xrom[0x20000 + 2 * ((h << 8) | l)]
            pc += 3
        elif op == 0xDD:
            if master[pc + 1:pc + 3] != bytes.fromhex("86 54"):
                raise ValueError("Unexpected indexed Z80 addition")
            total = a + field_54
            a, carry = total & 255, total > 255
            pc += 3
        elif op == 0xDC:  # CALL C,0x0A9C
            dest = master[pc + 1] | (master[pc + 2] << 8)
            if dest != 0x0A9C:
                raise ValueError("Unexpected saturation helper")
            if carry:
                if master[dest:dest + 4] != bytes.fromhex("3E FF B7 C9"):
                    raise ValueError("Saturation helper opcode mismatch")
                a, carry = 0xFF, False
            pc += 3
        elif op == 0x47:  # LD B,A
            return a
        else:
            raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")
    raise ValueError("Original Z80 stage exceeded instruction budget")


def verify(master: bytes, xrom: bytes) -> dict:
    if len(master) != MASTER_BYTES or len(xrom) != XROM_BYTES:
        raise ValueError("Original MAME-rotated arcade memory images required")
    checks = 0
    for value in range(256):
        original = original_flagged_lookup(master, xrom, value)
        expected = ((value * 0x60) + 128) >> 8
        if original != expected:
            raise AssertionError(f"7039 input {value}: {original} != {expected}")
        checks += 1
    for value in range(256):
        for field in range(256):
            original = original_weighted_stage(master, xrom, value, field)
            expected = min(255, ((value * 0xA6 + 128) >> 8) + field)
            if original != expected:
                raise AssertionError(
                    f"709C value={value} IX+54={field}: {original} != {expected}"
                )
            checks += 1
    return {
        "status": "Verified original Z80 input branch and saturation opcode stages",
        "original_z80_opcode_checks": checks,
        "mismatches": 0,
        "stages": ["master bank 0, address 7039", "master bank 0, address 709C"],
        "scope": "Unsigned drive-byte arithmetic; no car movement or AI is implied",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("xrom", type=Path)
    parser.add_argument("--out", type=Path,
                        default=Path("local/recovery/drive_opcode_parity.json"))
    args = parser.parse_args()
    report = verify(args.master.read_bytes(), args.xrom.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
