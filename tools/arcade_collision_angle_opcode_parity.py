#!/usr/bin/env python3
"""Original 1991 Indy Heat collision-response angle conversion ($A600).

The fixed-ROM Z80 routine at $A600..$A639 normalises signed B/C inputs,
uses an 8-bit atan-like table in the fixed $A000..$A1FF ROM window, and
applies signed quadrant corrections. This checker verifies a separate
arithmetic model against bounded ORIGINAL Z80 opcode execution for all
65,536 signed-input combinations.

Private user-provided original arcade ROM is a local analysis input only.
No original tables, graphics, executable data or disassembly are committed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
CODE_SHA = "5c536e8347cce91cca7e3a0e7b5ad784c55ac13a769a17a684afa3d10151684b"
TABLE_SHA = "60959ac9359a5c5aa9da0b39e9fc18c4be48e08e2e7a9d588c6f019c7db12f93"
CODE_BEGIN, CODE_END = 0xA600, 0xA63A
TABLE_BEGIN, TABLE_END = 0xA000, 0xA200


def arithmetic_shift_byte(value: int) -> int:
    """Z80 SRA: retain sign bit and shift others right."""
    return ((value >> 1) | (value & 0x80)) & 255


def independent_angle(table: bytes, b: int, c: int) -> tuple[int, int]:
    """Recover exact index and quadrant transformation without emulating opcodes."""
    if len(table) != 512 or any(not 0 <= n <= 255 for n in (b, c)):
        raise ValueError("Expected 512-byte original table and two input bytes")
    negative_c = bool(c & 128)
    a = (~c & 255) if negative_c else c
    while a >= 16:
        a >>= 1
        b = arithmetic_shift_byte(b)
    c = a
    negative_b = bool(b & 128)
    a = (~b & 255) if negative_b else b
    while a >= 16:
        a >>= 1
        c = arithmetic_shift_byte(c)
    if not (0 <= c < 16 and 0 <= a < 16):
        raise AssertionError("Original normalisation did not converge")
    index = (c << 4) | a
    result = table[index * 2]
    if negative_b:
        result = ((~result & 255) + 0x81) & 255
    if negative_c:
        result = (-result) & 255
    return result, index


def independent_angle_with_carry(table: bytes, b: int, c: int) -> tuple[int, int, int]:
    """Also preserve original Z80 carry flag on RET (used by later SBC HL,DE).

    The simple 8-bit direction result alone is insufficient for exact
    collision response. NEG sets carry for nonzero input; ADD 81 can carry
    in the alternate signed quadrant; the direct table path returns with
    carry clear from the final ADC A,0 high-page calculation.
    """
    if len(table) != 512 or any(not 0 <= n <= 255 for n in (b, c)):
        raise ValueError("Expected original angle table and input bytes")
    negative_c = bool(c & 128)
    a = (~c & 255) if negative_c else c
    while a >= 16:
        a >>= 1
        b = arithmetic_shift_byte(b)
    c = a
    negative_b = bool(b & 128)
    a = (~b & 255) if negative_b else b
    while a >= 16:
        a >>= 1
        c = arithmetic_shift_byte(c)
    index = (c << 4) | a
    result = table[2*index]
    carry = 0
    if negative_b:
        total = ((~result & 255) + 0x81)
        result, carry = total & 255, int(total > 255)
    if negative_c:
        before = result
        result, carry = (-result) & 255, int(before != 0)
    return result, index, carry


def execute_original(master: bytes, b: int, c: int, *, include_flags: bool = False) -> tuple:
    """Execute the original A600 routine until outer RET; unknown opcodes fail."""
    if len(master) != 0x90000 or any(not 0 <= n <= 255 for n in (b, c)):
        raise ValueError("Arcade master memory/inputs not valid")
    a = h = l = carry = sign = 0
    pc = CODE_BEGIN
    stack: list[int] = []

    def signed_disp(byte: int) -> int:
        return byte - 256 if byte >= 128 else byte

    for step in range(128):
        op = master[pc]
        if op == 0x79:  # LD A,C
            a = c
            pc += 1
        elif op == 0xB7:  # OR A
            sign, carry = a >> 7, 0
            pc += 1
        elif op == 0xF2:  # JP P,nn
            addr = int.from_bytes(master[pc+1:pc+3], "little")
            pc = addr if not sign else pc+3
        elif op == 0x2F:  # CPL
            a ^= 0xFF
            pc += 1
        elif op == 0xCD:  # CALL nn
            stack.append(pc+3)
            pc = int.from_bytes(master[pc+1:pc+3], "little")
        elif op == 0xED and master[pc+1] == 0x44:  # NEG
            before = a
            a = (-a) & 255
            sign, carry = a >> 7, int(before != 0)
            pc += 2
        elif op == 0xC9:  # RET
            if stack:
                pc = stack.pop()
            else:
                if include_flags:
                    return a, ((h << 8) | l), step+1, carry
                return a, ((h << 8) | l), step+1
        elif op == 0xCB and master[pc+1] == 0x3F:  # SRL A
            carry = a & 1
            a >>= 1
            sign = 0
            pc += 2
        elif op == 0xCB and master[pc+1] == 0x28:  # SRA B
            carry = b & 1
            b = arithmetic_shift_byte(b)
            sign = b >> 7
            pc += 2
        elif op == 0xCB and master[pc+1] == 0x29:  # SRA C
            carry = c & 1
            c = arithmetic_shift_byte(c)
            sign = c >> 7
            pc += 2
        elif op == 0xFE:  # CP n
            right = master[pc+1]
            carry = int(a < right)
            sign = ((a-right) & 255) >> 7
            pc += 2
        elif op == 0x30:  # JR NC
            pc = pc+2+signed_disp(master[pc+1]) if not carry else pc+2
        elif op == 0x4F:  # LD C,A
            c = a
            pc += 1
        elif op == 0x78:  # LD A,B
            a = b
            pc += 1
        elif op == 0xC6:  # ADD A,n
            value = a+master[pc+1]
            a, carry = value & 255, int(value > 255)
            sign = a >> 7
            pc += 2
        elif op == 0x6F:  # LD L,A
            l = a
            pc += 1
        elif op == 0x87:  # ADD A,A
            value = a*2
            a, carry = value & 255, int(value > 255)
            sign = a >> 7
            pc += 1
        elif op == 0xB5:  # OR L
            a |= l
            carry, sign = 0, a >> 7
            pc += 1
        elif op == 0x3E:  # LD A,n (flags unchanged)
            a = master[pc+1]
            pc += 2
        elif op == 0xCE:  # ADC A,n
            value = a+master[pc+1]+carry
            a, carry = value & 255, int(value > 255)
            sign = a >> 7
            pc += 2
        elif op == 0x67:  # LD H,A
            h = a
            pc += 1
        elif op == 0x7E:  # LD A,(HL)
            addr = (h << 8) | l
            if not TABLE_BEGIN <= addr < TABLE_END:
                raise ValueError("Original angle lookup jumped outside ROM table")
            a = master[addr]
            pc += 1
        else:
            raise ValueError(f"Unrecognised original angle opcode {op:02X} at {pc:04X}")
        if not CODE_BEGIN <= pc < CODE_END:
            raise ValueError(f"Original Z80 angle path left bounded routine at {pc:04X}")
    raise ValueError("Original angle routine exceeded instruction budget")


def verify(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Privately reconstructed, verified 1991 arcade master ROM required")
    if hashlib.sha256(master[CODE_BEGIN:CODE_END]).hexdigest() != CODE_SHA:
        raise ValueError("Original fixed A600 angle routine changed")
    table = master[TABLE_BEGIN:TABLE_END]
    if hashlib.sha256(table).hexdigest() != TABLE_SHA:
        raise ValueError("Original A000 angle table changed")
    outputs = Counter()
    checks = 0
    max_opcodes = 0
    for b in range(256):
        for c in range(256):
            expected, index = independent_angle(table, b, c)
            actual, addr, steps, carry = execute_original(master, b, c, include_flags=True)
            modeled_value, modeled_index, modeled_carry = independent_angle_with_carry(table, b, c)
            if ((actual, carry) != (expected, modeled_carry)
                    or modeled_value != expected or modeled_index != index
                    or addr != TABLE_BEGIN + index*2):
                raise AssertionError(f"Original angle disagreement B={b} C={c}")
            checks += 1
            outputs[actual] += 1
            max_opcodes = max(max_opcodes, steps)
    return {
        "source": "Indy Heat 1991 arcade master fixed $A600..$A639",
        "original_lookup_address": "A000..A1FF; 256 entries, two-byte stride",
        "original_table_sha256": TABLE_SHA,
        "original_routine_sha256": CODE_SHA,
        "inputs": "signed 8-bit B and C",
        "model": "signed quadrant reduction, repeated integer 2:1 scaling, 16x16 table, quadrant corrections",
        "original_opcode_cases": checks,
        "mismatches": 0,
        "distinct_8bit_return_values": len(outputs),
        "carry_flag_checked": "all 65536 inputs; required by following B51F SBC HL,DE",
        "maximum_instructions_per_call": max_opcodes,
        "scope": "Original direction calculation only; impact response and full physics remain OPEN",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path, help="PRIVATE master.mame_runtime.bin")
    p.add_argument("--out", type=Path,
                   default=Path("local/recovery/original_collision_angle.json"))
    args = p.parse_args()
    r = verify(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
