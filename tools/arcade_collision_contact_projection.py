#!/usr/bin/env python3
"""Recover original Indy Heat oriented car-to-car proximity projections.

Original master Z80 fixed ROM $B45A..$B4A2 uses trigonometric lookup
bytes and the original signed saturated multiplication X-ROM to test two
rotated contact axes. Executes original bounded instructions; independent
model uses analytical trig and integer operations. Contact consequences
AFTER $B4A3, crash/damage and gameplay parity remain unverified.

Original ROM/X-ROM data are private inputs, never included in this repository.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA = "1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
START, STOP = 0xB45A, 0xB4A3
STAGE_SHA = "c4c5162ebfe131089805abbc976ed004292df1be2f1de35034aa720aa2f7bce7"


def s8(x: int) -> int:
    return x - 256 if x >= 128 else x


def trig8(angle: int) -> tuple[int, int]:
    if not 0 <= angle <= 255:
        raise ValueError("Original angle is one byte")
    rad = angle * math.tau / 256
    co = max(-128, min(127, round(128 * math.cos(rad)))) & 255
    si = max(-128, min(127, round(128 * math.sin(rad)))) & 255
    return co, si


def mul_hi(left: int, right: int) -> int:
    if any(not 0 <= x <= 255 for x in (left, right)):
        raise ValueError("Signed multiplier operands must be 8-bit")
    result = max(-32768, min(32767, s8(left) * s8(right) * 2)) & 65535
    return result >> 8


def independent_projection(angle: int, b: int, c: int) -> str:
    """Original *oriented contact test*, not impact response."""
    if any(not 0 <= x <= 255 for x in (b, c)):
        raise ValueError("Original signed separation bytes expected")
    cosine, sine = trig8(angle)
    first, second = mul_hi(c, cosine), mul_hi(b, sine)
    val = (first - second) & 255
    if ((first ^ second) & (first ^ val) & 128):
        return "axis0_overflow"
    value = ((s8(val & 0xF8) >> 3) + 9) & 255
    if value >= 18:
        return "axis0_range"
    first, second = mul_hi(b, cosine), mul_hi(c, sine)
    val = (first + second + 1) & 255
    if ((~(first ^ second)) & (first ^ val) & 128):
        return "axis1_overflow"
    value = ((s8(val & 0xF8) >> 3) + 12) & 255
    if value >= 24:
        return "axis1_range"
    return "passes_projection"


def original_projection(master: bytes, xrom: bytes,
                        angle: int, b: int, c: int) -> str:
    """Execute only encountered original Z80 opcodes until RET or PC B4A3."""
    if len(master) != 0x90000 or len(xrom) != 0x40000:
        raise ValueError("Original MAME-rotated arcade master and X-ROM expected")
    cosine, sine = trig8(angle)
    if master[0xA200+angle] != cosine or master[0xA500+angle] != sine:
        raise ValueError("Original 256-step trigonometric table differs")
    pc = START
    a = h = l = d = e = carry = overflow = 0
    xr = 0
    alt = (0, 0, 0)
    for _ in range(75):
        op = master[pc]
        if op == 0x26:  # LD H,n
            h = master[pc+1]
            pc += 2
        elif master[pc:pc+3] == bytes.fromhex("dd 6e bd"):  # LD L,(IX-43h)
            l = angle
            pc += 3
        elif op == 0x56:  # LD D,(HL) - cosine
            d = master[(h << 8) | l]
            pc += 1
        elif op == 0x5E:  # LD E,(HL) - sine
            e = master[(h << 8) | l]
            pc += 1
        elif op == 0x61:  # LD H,C
            h = c
            pc += 1
        elif op == 0x60:  # LD H,B
            h = b
            pc += 1
        elif op == 0x6A:  # LD L,D
            l = d
            pc += 1
        elif op == 0x6B:  # LD L,E
            l = e
            pc += 1
        elif op == 0x22 and master[pc+1:pc+3] == bytes.fromhex("fc ff"):
            xr = h << 8 | l
            pc += 3
        elif op == 0x3A and master[pc+1:pc+3] == bytes.fromhex("fd ff"):
            a = xrom[2*xr+1]  # original XROM slot0 high byte
            pc += 3
        elif op == 0x2A and master[pc+1:pc+3] == bytes.fromhex("fc ff"):
            v = xrom[2*xr] | xrom[2*xr+1] << 8
            h, l = v >> 8, v & 255
            pc += 3
        elif op == 0x94:  # SUB H
            before = a
            a = (before - h) & 255
            carry = int(before < h)
            overflow = int(bool((before ^ h) & (before ^ a) & 128))
            pc += 1
        elif op == 0x8C:  # ADC A,H
            before = a
            result = before + h + carry
            a, carry = result & 255, int(result > 255)
            overflow = int(bool((~(before ^ h)) & (before ^ a) & 128))
            pc += 1
        elif op == 0xE8:  # RET PE, signed overflow
            if overflow:
                return "axis0_overflow" if pc < 0xB482 else "axis1_overflow"
            pc += 1
        elif op == 0xE6 and master[pc+1] == 0xF8:  # AND F8
            a &= 0xF8
            carry = overflow = 0
            pc += 2
        elif op == 0xCB and master[pc+1] == 0x2F:  # SRA A
            carry = a & 1
            a = (a >> 1) | (a & 128)
            pc += 2
        elif op == 0xC6:  # ADD A,imm
            imm = master[pc+1]
            total = a + imm
            nexta = total & 255
            overflow = int(bool((~(a ^ imm)) & (a ^ nexta) & 128))
            a, carry = nexta, int(total > 255)
            pc += 2
        elif op == 0xFE:  # CP imm
            carry = int(a < master[pc+1])
            pc += 2
        elif op == 0xD0:  # RET NC
            if not carry:
                return "axis0_range" if pc < 0xB482 else "axis1_range"
            pc += 1
        elif op == 0x08:  # EX AF,AF'
            a, carry, overflow, alt = (*alt, (a, carry, overflow))
            pc += 1
        elif op == 0x37:  # SCF for second projection's ADC
            carry = 1
            pc += 1
        else:
            raise ValueError(f"Unexpected arcade contact opcode {op:02X} at {pc:04X}")
        if pc == STOP:
            return "passes_projection"
        if not START <= pc <= STOP:
            raise ValueError(f"Original contact routine left bounded PC window: {pc:04X}")
    raise ValueError("Original rotated projection exceeded instruction budget")


def verify(master: bytes, xrom: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Original checksum-matched arcade master ROM required")
    if len(xrom) != 0x40000 or hashlib.sha256(xrom).hexdigest() != XROM_SHA:
        raise ValueError("Original checksum-matched arcade X-ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Original contact projection stage differs")
    for angle in range(256):
        cosine, sine = trig8(angle)
        if (master[0xA200+angle], master[0xA500+angle]) != (cosine, sine):
            raise ValueError(f"Original sine/cosine differs at angle {angle}")
    rng = random.Random(0xC01115)
    counts: Counter[str] = Counter()
    for angle in range(256):
        cases = [(0,0), (128,128), (127,127), (255,255)]
        cases += [(rng.randrange(256), rng.randrange(256)) for _ in range(250)]
        for b, c in cases:
            independent = independent_projection(angle, b, c)
            actual = original_projection(master, xrom, angle, b, c)
            if independent != actual:
                raise AssertionError(f"Original rotated contact disagreement at {angle},{b},{c}")
            counts[actual] += 1
    return {
        "game": "original 1991 arcade Indy Heat",
        "master_fixed_cpu_range": "B45A..B4A2",
        "orientation_field": "car IX-0x43",
        "input": "signed 8-bit relative separation B,C from original collision scaling",
        "source_trig": "original 256-entry sine and cosine ROM arrays",
        "source_multiplier": "original signed saturated 8x8 X-ROM slot0",
        "first": "SUB with overflow check; AND F8 then SRA×3; offset+9 must be <18",
        "second": "ADC with incoming carry1 and overflow check; AND F8 then SRA×3; offset+12 must be <24",
        "cases": sum(counts.values()),
        "outcomes": dict(counts),
        "mismatches": 0,
        "scope": "Two rotated-contact proximity tests only; later lookup and impulse/damage results UNVERIFIED",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("master", type=Path, help="PRIVATE master.mame_runtime.bin")
    ap.add_argument("xrom", type=Path, help="PRIVATE xrom.mame_runtime.bin")
    ap.add_argument("--out", type=Path, default=Path("local/recovery/contact_projection.json"))
    args = ap.parse_args()
    report = verify(args.master.read_bytes(), args.xrom.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Original contact projection parity cases:", report["cases"])
    print("Mismatches:", report["mismatches"])


if __name__ == "__main__":
    main()
