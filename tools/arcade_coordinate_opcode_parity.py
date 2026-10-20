#!/usr/bin/env python3
"""Recover exact original Indy Heat arcade two-axis coordinate update.

Master Z80 bank0 PC $7530..$7571 uses 256-step sine/cosine and X-ROM
fixed-point multiplication to update 16-bit RAM accumulators E735/E72B.
This is a bounded *original opcode* check, NOT a complete vehicle engine.
No original code/data is distributed in this file.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

MASTER_HASH = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_HASH = "1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
START, STOP = 0x7530, 0x7572


def signed8(value: int) -> int:
    return value - 256 if value >= 128 else value


def arcade_trig(angle: int, sine: bool) -> int:
    if not 0 <= angle <= 255:
        raise ValueError("Angle must be an 8-bit arcade sample")
    func = math.sin if sine else math.cos
    return max(-128, min(127, round(128 * func(angle * math.tau / 256))))


def axis_step(trig: int, motion: int) -> int:
    """Original slot0 saturating signed multiply, times 4, nearest-byte step."""
    if any(not -128 <= v <= 127 for v in (trig, motion)):
        raise ValueError("Signed operands outside 8-bit range")
    product = min(32767, max(-32768, trig * motion * 2))
    return (product * 4 + 128) // 256


def independent_model(angle: int, motion_byte: int, x: int, y: int) -> tuple[int, int]:
    if not (0 <= motion_byte <= 255 and 0 <= x <= 65535 and 0 <= y <= 65535):
        raise ValueError("Original game fields must be unsigned byte/word values")
    motion = signed8(motion_byte)
    dx = axis_step(arcade_trig(angle, True), motion)
    dy = axis_step(arcade_trig(angle, False), motion)
    return (x + dx) & 65535, (y + dy) & 65535


def original_opcodes(master: bytes, xrom: bytes, angle: int, motion: int,
                     x: int, y: int) -> tuple[int, int]:
    """Run only ORIGINAL Z80 instructions reached inside PC 7530..7571.

    Every unknown instruction, memory location, or call fails closed. X-ROM
    port FFFC is emulated with its bank-0 16-bit table contents.
    """
    if len(master) != 0x90000 or len(xrom) != 0x40000:
        raise ValueError("Original arcade ROM region sizes required")
    a = b = c = d = e = h = l = carry = xr = 0
    pc = START
    ram = {0xE76A: angle, 0xE76C: motion, 0xE735: x, 0xE72B: y}
    for _ in range(65):
        op = master[pc]
        if op == 0x3A:  # LD A,(absolute)
            addr = int.from_bytes(master[pc+1:pc+3], "little")
            a = ram[addr]
            pc += 3
        elif op == 0x6F:  # LD L,A
            l = a; pc += 1
        elif op == 0x26:  # LD H,immediate
            h = master[pc+1]; pc += 2
        elif op == 0x46:  # LD B,(HL)
            b = master[(h << 8) | l]; pc += 1
        elif op == 0x66:  # LD H,(HL)
            h = master[(h << 8) | l]; pc += 1
        elif op == 0x4F:  # LD C,A
            c = a; pc += 1
        elif op == 0x22:  # LD (absolute),HL
            address = int.from_bytes(master[pc+1:pc+3], "little")
            if address not in (0xFFFC, 0xE735, 0xE72B):
                raise ValueError(f"Unexpected memory write at {pc:04X}")
            value = h << 8 | l
            if address == 0xFFFC:
                xr = value
            else:
                ram[address] = value
            pc += 3
        elif op == 0x2A:  # LD HL,(absolute)
            address = int.from_bytes(master[pc+1:pc+3], "little")
            if address == 0xFFFC:
                value = xrom[2*xr] | xrom[2*xr+1] << 8
            else:
                value = ram[address]
            h, l = value >> 8, value & 255
            pc += 3
        elif op == 0xAF:  # XOR A
            a = carry = 0
            pc += 1
        elif op == 0x29:  # ADD HL,HL
            value = ((h << 8) | l) * 2
            carry = int(value > 65535)
            value &= 65535
            h, l = value >> 8, value & 255
            pc += 1
        elif op == 0x9F:  # SBC A,A
            a = 255 if carry else 0; pc += 1
        elif op == 0x17:  # RLA
            previous = a
            a = ((a << 1) | carry) & 255
            carry = int(bool(previous & 128))
            pc += 1
        elif op == 0x5C:  # LD E,H
            e = h; pc += 1
        elif op == 0x57:  # LD D,A
            d = a; pc += 1
        elif op == 0xCB and master[pc + 1] == 0x25:  # SLA L
            carry = int(bool(l & 128))
            l = (l << 1) & 255
            pc += 2
        elif op == 0x30:  # JR NC
            displacement = signed8(master[pc+1])
            pc = pc + 2 + displacement if not carry else pc + 2
        elif op == 0x13:  # INC DE
            value = ((d << 8) | e) + 1
            d, e = (value >> 8) & 255, value & 255
            pc += 1
        elif op == 0x19:  # ADD HL,DE
            value = ((h << 8) | l) + ((d << 8) | e)
            carry = int(value > 65535)
            value &= 65535
            h, l = value >> 8, value & 255
            pc += 1
        elif op == 0xED and master[pc+1:pc+4] == bytes.fromhex("43 fc ff"):
            xr = b << 8 | c  # LD (FFFC),BC
            pc += 4
        else:
            raise ValueError(f"Unexpected original opcode at {pc:04X}: {op:02X}")
        if pc == STOP:
            return ram[0xE735], ram[0xE72B]
        if not START <= pc <= STOP:
            raise ValueError(f"Original control flow departed the bounded stage: {pc:04X}")
    raise ValueError("Original coordinate stage exceeded execution limit")


def verify(master: bytes, xrom: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_HASH:
        raise ValueError("Must supply verified original master arcade ROM region")
    if len(xrom) != 0x40000 or hashlib.sha256(xrom).hexdigest() != XROM_HASH:
        raise ValueError("Must supply verified original arcade X-ROM region")
    for angle in range(256):
        for sine, base in ((False, 0xA200), (True, 0xA500)):
            observed = signed8(master[base + angle])
            expected = arcade_trig(angle, sine)
            if observed != expected:
                raise AssertionError(f"Trigonometric table discrepancy at {base+angle:04X}")
    cases = 0
    for angle in range(256):
        for motion in range(256):
            x, y = (angle << 8) | motion, (motion << 8) | angle
            expected = independent_model(angle, motion, x, y)
            actual = original_opcodes(master, xrom, angle, motion, x, y)
            if actual != expected:
                raise AssertionError(f"Coordinate stage mismatch angle={angle}, motion={motion}")
            cases += 1
    return {
        "original": "1991 Indy Heat arcade master Z80, bank0 PC 7530..7571",
        "exact_8bit_trig_samples": 512,
        "coordinate_opcode_cases": cases,
        "mismatches": 0,
        "source_registers": ["RAM[E76A] 8-bit angular sample", "RAM[E76C] 8-bit signed motion input"],
        "updates": ["RAM[E735] 16-bit signed-sine-derived axis", "RAM[E72B] 16-bit signed-cosine-derived axis"],
        "math": "round_signed((clamp(signed8(trig)*signed8(motion)*2,-32768,32767)*4)/256)",
        "scope": "exact bounded two-axis update; complete car movement/track collision still outstanding",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path, help="Private master.mame_runtime.bin")
    parser.add_argument("xrom", type=Path, help="Private xrom.mame_runtime.bin")
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/arcade_coordinate_opcode_parity.json"))
    args = parser.parse_args()
    result = verify(args.master.read_bytes(), args.xrom.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
