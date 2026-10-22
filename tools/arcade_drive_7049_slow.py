#!/usr/bin/env python3
"""Original 1991 Z80 slow-drive 7049–709B; stop before opaque CALLs.

Actual owner-ROM instructions are independently interpreted against an
integer model. The unknown X-ROM slot1 HIGH is never used by this path:
the CPU overwrites H at 7066, or starts 709C with LD H,B. The known
slot1 LOW multiplication is exact; original ROM bytes stay private.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

from arcade_drive_709c_speed import slot1_low

START = 0x7049
STOP = 0x709C
MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "c96cdfcf07c85b7c0456e31589dcf44fa7860be2cf65ec31736c63dfb3577925"


def _check(b: int, e765: int, ix3b: int, ix39: int,
           ix3a: int, ix31: int, ix_minus3: int, e94d_low: int) -> None:
    if not 0 <= e765 <= 65535 or any(not 0 <= v <= 255 for v in
        (b, ix3b, ix39, ix3a, ix31, ix_minus3, e94d_low)):
        raise ValueError("Original 7049 Z80 bytes and E765 word required")


def _result(branch: str, next_pc: int, b: int, e765: int,
            ix39: int, ix3a: int, ix31: int, subtrahend: int) -> dict:
    return {
        "branch": branch, "next_pc": next_pc, "complete": next_pc == STOP,
        "b": b, "e765": e765, "ix39": ix39, "ix3a": ix3a,
        "ix31": ix31, "subtrahend": subtrahend,
    }


def independent(b: int, e765: int, ix3b: int, ix39: int,
                ix3a: int, ix31: int, ix_minus3: int, e94d_low: int) -> dict:
    """Instruction-independent fixed-point reconstruction of proven paths."""
    _check(b, e765, ix3b, ix39, ix3a, ix31, ix_minus3, e94d_low)
    doubled_high = ((e765 * 2) & 65535) >> 8
    first = slot1_low(doubled_high, doubled_high)
    scale = (first // 2) + (first % 2) + 0x20  # SRL A; ADC A,20
    corrected_b = min(255, b + 128)           # ADD A,80; CALL C,0A9C
    second = slot1_low(scale, corrected_b)
    subtrahend = slot1_low(ix3b, second)

    updated_low = (ix39 - subtrahend) & 255
    if ix39 >= subtrahend:
        return _result("fast_709c", STOP, b, e765,
                       updated_low, ix3a, ix31, subtrahend)

    updated_high = (ix3a - 1) & 255
    if updated_high == 0:
        ix31 |= 0x10
    if updated_high < e94d_low:
        # 708E CALL 7E5E: unknown side effects, stop BEFORE executing.
        return _result("external_7e5e", 0x7E5E, b, e765,
                       updated_low, updated_high, ix31, subtrahend)
    if ix_minus3 < 3:
        # 7098 CALL C,2AD1 is similarly not replaced by a fake return.
        return _result("external_2ad1", 0x2AD1, b, e765,
                       updated_low, updated_high, ix31, subtrahend)
    return _result("fast_709c", STOP, b, e765,
                   updated_low, updated_high, ix31, subtrahend)


def original_opcodes(master: bytes, b: int, e765: int, ix3b: int,
                     ix39: int, ix3a: int, ix31: int, ix_minus3: int,
                     e94d_low: int) -> dict:
    """Execute authenticated original instructions, including real JR/JP gates.

    FFFE exposes only its independently proven LOW byte. Any unknown H
    value is poisoned and rejected if consumed by an instruction.
    """
    if len(master) != 0x90000 or sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Authenticated original 7049 ROM window required")
    _check(b, e765, ix3b, ix39, ix3a, ix31, ix_minus3, e94d_low)
    pc = START
    a = h = l = 0
    carry = zero = False
    xrom_address = 0
    subtrahend = None

    def byte(offset: int = 0) -> int:
        return master[pc + offset]

    def word() -> int:
        return byte(1) | (byte(2) << 8)

    for _ in range(50):
        if pc == STOP:
            if subtrahend is None:
                raise ValueError("Original 7049 terminated without X-ROM subtract")
            return _result("fast_709c", STOP, b, e765, ix39, ix3a, ix31, subtrahend)
        if not START <= pc < STOP:
            raise ValueError(f"Original slow-drive PC escaped window: {pc:04X}")
        op = byte()
        if op == 0x2A:  # LD HL,(nn)
            address = word()
            if address == 0xE765:
                h, l = e765 >> 8, e765 & 255
            elif address == 0xE94D:
                h, l = 0, e94d_low  # original E94D high is unused
            elif address == 0xFFFE:
                h, l = None, slot1_low(xrom_address >> 8, xrom_address & 255)
            else:
                raise ValueError("Original slow-drive read unknown word")
            pc += 3
        elif op == 0x29:  # ADD HL,HL
            if h is None:
                raise ValueError("Unknown X-ROM high consumed")
            value = ((h << 8) | l) * 2
            h, l, carry = (value >> 8) & 255, value & 255, value > 65535
            pc += 1
        elif op == 0x6C:  # LD L,H
            if h is None:
                raise ValueError("Unknown X-ROM high consumed")
            l = h
            pc += 1
        elif op == 0x22:  # LD (FFFE),HL: X-ROM slot1 latch
            if word() != 0xFFFE or h is None:
                raise ValueError("Original X-ROM latch consumed unknown high")
            xrom_address = (h << 8) | l
            pc += 3
        elif op == 0x3A:  # LD A,(FFFE): slot1 LOW only
            if word() != 0xFFFE:
                raise ValueError("Unexpected original byte load")
            a = slot1_low(xrom_address >> 8, xrom_address & 255)
            pc += 3
        elif op == 0xCB:  # SRL A
            if byte(1) != 0x3F:
                raise ValueError("Unexpected original CB opcode")
            carry, a = bool(a & 1), a >> 1
            zero = a == 0
            pc += 2
        elif op == 0xCE:  # ADC A,20
            if byte(1) != 0x20:
                raise ValueError("Unexpected original ADC operand")
            raw = a + 0x20 + int(carry)
            a, carry = raw & 255, raw > 255
            zero = a == 0
            pc += 2
        elif op == 0x67:  # LD H,A
            h = a
            pc += 1
        elif op == 0x78:  # LD A,B
            a = b
            pc += 1
        elif op == 0xC6:  # ADD A,80
            if byte(1) != 0x80:
                raise ValueError("Unexpected original ADD operand")
            raw = a + 0x80
            a, carry = raw & 255, raw > 255
            zero = a == 0
            pc += 2
        elif op == 0xDC:  # CALL C,0A9C or unresolved CALL C,2AD1
            target = word()
            if target == 0x0A9C:
                if carry:
                    a, carry, zero = 255, False, False
                pc += 3
            elif target == 0x2AD1:
                if carry:
                    if subtrahend is None:
                        raise ValueError("External CALL before X-ROM subtraction")
                    return _result("external_2ad1", 0x2AD1, b, e765,
                                   ix39, ix3a, ix31, subtrahend)
                pc += 3
            else:
                raise ValueError("Unexpected original conditional call")
        elif op == 0x6F:  # LD L,A
            l = a
            pc += 1
        elif op == 0xDD:  # indexed original RAM instructions
            subop, disp = byte(1), byte(2)
            if subop == 0x66 and disp == 0x3B:  # LD H,(IX+3B)
                h = ix3b
            elif subop == 0x7E and disp == 0x39:  # LD A,(IX+39)
                a = ix39
            elif subop == 0x77 and disp == 0x39:  # LD (IX+39),A
                ix39 = a
            elif subop == 0x7E and disp == 0x3A:  # LD A,(IX+3A)
                a = ix3a
            elif subop == 0x77 and disp == 0x3A:  # LD (IX+3A),A
                ix3a = a
            elif subop == 0x7E and disp == 0xFD:  # LD A,(IX-03)
                a = ix_minus3
            elif subop == 0xCB and disp == 0x31 and byte(3) == 0xE6:
                ix31 |= 0x10  # SET 4,(IX+31)
                pc += 4
                continue
            else:
                raise ValueError(f"Unrecognized original DD at {pc:04X}")
            pc += 3
        elif op == 0x95:  # SUB L
            raw = a - l
            a, carry = raw & 255, raw < 0
            zero = a == 0
            subtrahend = l
            pc += 1
        elif op == 0xD2:  # JP NC,709C
            if word() != STOP:
                raise ValueError("Unexpected original JP target")
            pc = STOP if not carry else pc + 3
        elif op == 0xDE:  # SBC A,00
            if byte(1) != 0:
                raise ValueError("Unexpected original SBC operand")
            raw = a - int(carry)
            a, carry = raw & 255, raw < 0
            zero = a == 0
            pc += 2
        elif op in (0x20, 0x30):  # JR NZ,7087 / JR NC,7092
            expected = (0x20, 0x04) if op == 0x20 else (0x30, 0x05)
            if (op, byte(1)) != expected:
                raise ValueError("Unexpected original JR offset")
            active = not zero if op == 0x20 else not carry
            pc += 2 + (byte(1) if active else 0)
        elif op == 0xBD:  # CP L
            raw = a - l
            carry, zero = raw < 0, (raw & 255) == 0
            pc += 1
        elif op == 0xC5 or op == 0xC1:  # PUSH/POP BC; B is preserved
            pc += 1
        elif op == 0xCD:  # unresolved CALL 7E5E, stop before effects
            if word() != 0x7E5E or subtrahend is None:
                raise ValueError("Unexpected original external CALL")
            return _result("external_7e5e", 0x7E5E, b, e765,
                           ix39, ix3a, ix31, subtrahend)
        elif op == 0xFE:  # CP 03
            if byte(1) != 3:
                raise ValueError("Unexpected original CP operand")
            carry, zero = a < 3, a == 3
            pc += 2
        else:
            raise ValueError(f"Unknown original 7049 opcode {op:02X} at {pc:04X}")
    raise ValueError("Original 7049 interpreter exceeded 50-instruction budget")


def verify_original(master: bytes, cases: int = 100000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Owner-supplied authenticated original master required")
    if not 0 <= cases <= 250000:
        raise ValueError("Out-of-range verification count")
    random = Random(0x7049709B)
    tally: Counter[str] = Counter()
    for index in range(cases):
        # Broad random state plus deliberately forcing all original gates.
        fields = (random.choice((0, 1, 127, 128, 255, random.randrange(256))),
                  random.choice((0, 1, 0x7FFF, 0xFFFF, random.randrange(65536))),
                  random.choice((0, 64, 127, 255, random.randrange(256))),
                  random.randrange(256), random.randrange(256),
                  random.randrange(256), random.randrange(256),
                  random.randrange(256))
        actual = original_opcodes(master, *fields)
        expected = independent(*fields)
        if actual != expected:
            raise AssertionError(f"Original Z80 7049 mismatch case {index} {fields}: "
                                 f"{actual} != {expected}")
        tally[actual["branch"]] += 1
    return {"source": "Owner original Z80 bank0 7049–709B",
            "original_z80_cases": cases, "mismatches": 0,
            "branches": dict(tally),
            "opaque_calls": ["7E5E", "2AD1"],
            "scope": "bounded control/decrement, not full arcade frame"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_master", type=Path)
    parser.add_argument("--cases", type=int, default=100000)
    options = parser.parse_args()
    print(json.dumps(verify_original(options.private_master.read_bytes(), options.cases), indent=2))
