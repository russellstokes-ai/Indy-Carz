#!/usr/bin/env python3
"""Bounded original arcade Z80 709C–7123: speed-word input correction.

One authenticated original master instruction window is interpreted against a
SEPARATE integer model. The original X-ROM slot1 LOW and slot0 arithmetic were
previously exhaustively identified; unknown slot1 HIGH is *never consumed* on
these paths. Original ROM bytes/track data are inputs and are not distributed.

This is NOT original accelerator sampling, a completed car/frame update,
terrain friction, fuel/turbo behavior, or a replacement gameplay physics law.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

START = 0x709C
STOP = 0x7124
MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "090d9272f4aa39f9d85cd8f5c8f9223399526f9709ea51f3ae16574b7afc6b50"


def signed8(value: int) -> int:
    return value - 256 if value & 128 else value


def slot1_low(high: int, low: int) -> int:
    if not (0 <= high <= 255 and 0 <= low <= 255):
        raise ValueError("8-bit original X-ROM slot1 operands required")
    return (high * low + 128) >> 8


def slot0_word(high: int, low: int) -> int:
    if not (0 <= high <= 255 and 0 <= low <= 255):
        raise ValueError("8-bit original X-ROM slot0 operands required")
    product = 2 * signed8(high) * signed8(low)
    return min(32767, max(-32768, product)) & 65535


def _check_inputs(b: int, e765: int, ix54: int, ix3c: int,
                  ix60: int, ix61: int, original_table: bytes) -> None:
    if not (0 <= b <= 255 and 0 <= e765 <= 65535 and
            all(0 <= v <= 255 for v in (ix54, ix3c, ix60, ix61))):
        raise ValueError("Original register/RAM inputs are out of range")
    if len(original_table) != 256:
        raise ValueError("Original 2000–20FF bank0 ROM lookup required")


def independent(b: int, e765: int, ix54: int, ix3c: int,
                ix60: int, ix61: int, original_table: bytes) -> dict:
    """Arithmetic reconstruction independent of the Z80 opcode interpreter."""
    _check_inputs(b, e765, ix54, ix3c, ix60, ix61, original_table)
    adjusted_b = min(255, slot1_low(b, 0xA6) + ix54)
    prior_high = e765 >> 8
    factor = original_table[(-ix3c) & 255]

    if adjusted_b == prior_high:
        return {"branch": "equal", "b": adjusted_b, "threshold_b": adjusted_b, "e765": e765,
                "factor": factor, "next_pc": STOP}

    if adjusted_b > prior_high:
        doubled = (factor << 1) & 255
        first = slot1_low(doubled, doubled)
        second = slot1_low(adjusted_b, first)
        high = ix60
        if second & 128:
            second >>= 1
            high = (high << 1) & 255
        product = slot0_word(high, second)
        increment = (product >> 1) + (product & 1)
        computed = (e765 + increment) & 65535
        # Z80 ADC HL,DE overflow, after SRL H; RR L of the X-ROM word.
        lhs = product >> 1
        signed_overflow = bool((~(lhs ^ e765) & (lhs ^ computed)) & 0x8000)
        corrected = 0x7FFF if signed_overflow else computed
        return {"branch": "add", "b": adjusted_b, "threshold_b": adjusted_b, "e765": corrected,
                "factor": factor, "next_pc": STOP}

    doubled = (factor << 1) & 255
    first = slot1_low(doubled, doubled)
    second = slot1_low(prior_high - adjusted_b, first)
    high = ix61
    carry = int(bool(factor & 128))  # original 70FA SLA H
    if second & 128:
        second >>= 1
        carry = int(bool(high & 128))  # original 7113 SLA H
        high = (high << 1) & 255
    product = slot0_word(high, second)
    computed = (e765 - product - carry) & 65535
    corrected = 0 if computed & 0x8000 else computed  # CALL M,0AA0
    return {"branch": "subtract", "b": prior_high - adjusted_b,
            "threshold_b": adjusted_b, "e765": corrected,
            "factor": factor, "next_pc": STOP}


def original_opcodes(master: bytes, b: int, e765: int, ix54: int,
                     ix3c: int, ix60: int, ix61: int) -> dict:
    """Execute the actual original 709C–7123 instructions, no invented ops.

    The unclassified X-ROM slot1 high byte is treated as poison. Every actual
    read is followed by an instruction overwriting the H register before use.
    """
    if len(master) != 0x90000:
        raise ValueError("Original 589824-byte master region required")
    if sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Original opcode window fingerprint mismatch")
    table = master[0x2000:0x2100]
    _check_inputs(b, e765, ix54, ix3c, ix60, ix61, table)
    pc = START
    a = h = l = 0
    source_b = b
    de = e765
    carry = zero = parity_overflow = sign = False
    xrom1_address = xrom0_address = 0
    final = None
    consumed_xrom1_high = False
    branch = None
    threshold_b = None

    def unsigned16() -> int:
        return (h << 8) | l

    def byte_at(address: int) -> int:
        return master[address]

    def word_at(address: int) -> int:
        return master[address] | (master[address + 1] << 8)

    for _ in range(100):
        if pc == STOP:
            if final is None or branch is None or consumed_xrom1_high:
                raise ValueError("Uncompleted original speed branch or unknown X-ROM high read")
            return {"branch": branch, "b": source_b,
                    "threshold_b": threshold_b, "e765": final,
                    "factor": table[(-ix3c) & 255], "next_pc": STOP}
        if not START <= pc < STOP:
            raise ValueError(f"Original Z80 escaped 709C–7123: {pc:04X}")
        op = byte_at(pc)
        if op == 0x60:  # LD H,B
            h = source_b
            pc += 1
        elif op == 0x2E:  # LD L,n
            l = byte_at(pc + 1)
            pc += 2
        elif op == 0x26:  # LD H,n
            h = byte_at(pc + 1)
            pc += 2
        elif op == 0x22:  # LD (nn),HL: original X-ROM latches or E765
            address = word_at(pc + 1)
            if address == 0xFFFE:
                xrom1_address = unsigned16()
            elif address == 0xFFFC:
                xrom0_address = unsigned16()
            elif address == 0xE765:
                final = unsigned16()
            else:
                raise ValueError("Unexpected original speed stage word write")
            pc += 3
        elif op == 0x3A:  # LD A,(FFFE): known original slot1 LOW only
            if word_at(pc + 1) != 0xFFFE:
                raise ValueError("Unexpected original byte read")
            a = slot1_low(xrom1_address >> 8, xrom1_address & 255)
            pc += 3
        elif op == 0x2A:  # LD HL,(E765/FFFE/FFFC)
            address = word_at(pc + 1)
            if address == 0xE765:
                value = e765
            elif address == 0xFFFC:
                value = slot0_word(xrom0_address >> 8, xrom0_address & 255)
            elif address == 0xFFFE:
                # The high byte is unknown. It MUST immediately be overwritten.
                if pc + 3 not in (0x70C7, 0x70CE, 0x7103, 0x710A):
                    raise ValueError("Original execution consumes unknown slot1 high")
                value = slot1_low(xrom1_address >> 8, xrom1_address & 255)
            else:
                raise ValueError("Unexpected original word read")
            h, l = value >> 8, value & 255
            pc += 3
        elif op == 0xDD:
            opcode, disp = byte_at(pc + 1), byte_at(pc + 2)
            if opcode == 0x86 and disp == 0x54:  # ADD A,(IX+54)
                raw = a + ix54
                carry = raw > 255
                a = raw & 255
                zero = a == 0
            elif opcode == 0x7E and disp == 0x3C:  # LD A,(IX+3C)
                a = ix3c
            elif opcode == 0x66 and disp in (0xE0, 0xE1):
                h = ix60 if disp == 0xE0 else ix61
            else:
                raise ValueError(f"Unexpected original IX opcode {opcode:02X}/{disp:02X}")
            pc += 3
        elif op == 0xDC:  # CALL C,0A9C: original saturating helper
            if word_at(pc + 1) != 0x0A9C:
                raise ValueError("Unexpected original external CALL")
            if carry:
                a = 255
                carry = zero = False
            pc += 3
        elif op == 0xED:
            suffix = byte_at(pc + 1)
            if suffix == 0x5B and word_at(pc + 2) == 0xE765:
                de = e765
                pc += 4
            elif suffix == 0x44:  # NEG
                carry = a != 0
                a = (-a) & 255
                zero = a == 0
                sign = bool(a & 128)
                pc += 2
            elif suffix in (0x5A, 0x52):  # ADC HL,DE / SBC HL,DE
                lhs = unsigned16()
                amount = int(carry)
                raw = lhs + de + amount if suffix == 0x5A else lhs - de - amount
                computed = raw & 65535
                parity_overflow = bool(
                    (~(lhs ^ de) & (lhs ^ computed) & 0x8000)
                    if suffix == 0x5A else
                    ((lhs ^ de) & (lhs ^ computed) & 0x8000)
                )
                carry = (raw > 65535) if suffix == 0x5A else (raw < 0)
                sign = bool(computed & 0x8000)
                zero = computed == 0
                h, l = computed >> 8, computed & 255
                pc += 2
            else:
                raise ValueError(f"Unexpected ED original Z80 at {pc:04X}")
        elif op == 0x92:  # SUB D
            threshold_b = source_b
            raw = a - (de >> 8)
            carry = raw < 0
            a = raw & 255
            zero = a == 0
            sign = bool(a & 128)
            pc += 1
        elif op in (0x38, 0x28):  # JR C, / JR Z,
            condition = carry if op == 0x38 else zero
            distance = byte_at(pc + 1)
            pc += 2 + ((distance if distance < 128 else distance - 256) if condition else 0)
            if condition and pc == 0x70EE:
                branch = "subtract"
            elif condition and pc == STOP:
                branch = "equal"
                final = e765
        elif op == 0x87:  # ADD A,A
            raw = a + a
            carry = raw > 255
            a = raw & 255
            zero = a == 0
            pc += 1
        elif op == 0x47:  # LD B,A
            source_b = a
            pc += 1
        elif op == 0x67:  # LD H,A
            h = a
            pc += 1
        elif op == 0x6F:  # LD L,A
            l = a
            pc += 1
        elif op == 0x6C:  # LD L,H
            l = h
            pc += 1
        elif op == 0x7E:  # LD A,(HL) at original 0x2000 lookup
            if h != 0x20:
                raise ValueError("Unexpected original lookup table page")
            a = master[unsigned16()]
            pc += 1
        elif op == 0x66:  # LD H,(HL) at original 0x2000 lookup
            if h != 0x20:
                raise ValueError("Unexpected original lookup table page")
            h = master[unsigned16()]
            pc += 1
        elif op == 0xCB:
            suffix = byte_at(pc + 1)
            if suffix == 0x7D:  # BIT 7,L (preserves carry)
                zero = not bool(l & 128)
            elif suffix == 0x3D:  # SRL L
                carry = bool(l & 1)
                l >>= 1
            elif suffix == 0x24:  # SLA H
                carry = bool(h & 128)
                h = (h << 1) & 255
            elif suffix == 0x3C:  # SRL H
                carry = bool(h & 1)
                h >>= 1
            elif suffix == 0x1D:  # RR L
                new_carry = bool(l & 1)
                l = (l >> 1) | (int(carry) << 7)
                carry = new_carry
            else:
                raise ValueError(f"Unexpected original CB opcode {suffix:02X}")
            pc += 2
        elif op == 0xEB:  # EX DE,HL
            prior = unsigned16()
            h, l = de >> 8, de & 255
            de = prior
            pc += 1
        elif op in (0xEC, 0xFC):  # CALL PE,1C88 / CALL M,0AA0
            target = word_at(pc + 1)
            if op == 0xEC and target == 0x1C88:
                if parity_overflow:
                    h, l = 0x7F, 0xFF
            elif op == 0xFC and target == 0x0AA0:
                if sign:
                    h = l = 0
            else:
                raise ValueError("Unexpected original conditional helper")
            pc += 3
        elif op == 0xC3:  # JP 7124
            target = word_at(pc + 1)
            if target != STOP:
                raise ValueError("Unexpected original unconditional jump")
            if branch is None:
                branch = "add" if pc == 0x70EB else "subtract"
            pc = STOP
        else:
            raise ValueError(f"Unsupported original Z80 {op:02X} at {pc:04X}")
    raise ValueError("Original 709C–7123 opcode budget exceeded")


def verify_original(master: bytes, cases: int = 100000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Authenticated original 1991 master Z80 required")
    if not 0 <= cases <= 250000:
        raise ValueError("Invalid original case count")
    table = master[0x2000:0x2100]
    rng = Random(0x709C7123)
    histogram: Counter[str] = Counter()
    for index in range(cases):
        args = (
            rng.choice((0, 1, 63, 127, 128, 191, 255, rng.randrange(256))),
            rng.choice((0, 0x7FFF, 0x8000, 0xFFFF, rng.randrange(65536))),
            rng.choice((0, 1, 127, 128, 255, rng.randrange(256))),
            rng.randrange(256),
            rng.choice((0, 1, 127, 128, 255, rng.randrange(256))),
            rng.choice((0, 1, 127, 128, 255, rng.randrange(256))),
        )
        expected = independent(*args, table)
        observed = original_opcodes(master, *args)
        if observed != expected:
            raise AssertionError(f"Original opcode disagreement at case {index}: {args}, {expected}, {observed}")
        histogram[observed["branch"]] += 1
    return {
        "source": "Original 1991 master bank0 709C–7123",
        "cases": cases,
        "mismatches": 0,
        "original_slot0": "signed saturated two-byte X-ROM arithmetic",
        "original_slot1_low": "exhaustively characterized unsigned rounded product",
        "original_slot1_high": "NOT read by surviving calculation paths",
        "branches": dict(histogram),
        "next_pc": f"{STOP:04X}",
        "scope": "bounded speed E765 update, not original frame/game parity",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_master", type=Path)
    parser.add_argument("--cases", type=int, default=100000)
    arguments = parser.parse_args()
    print(json.dumps(verify_original(arguments.private_master.read_bytes(), arguments.cases), indent=2))
