#!/usr/bin/env python3
"""Verify original 1991 arcade pre-race counter/timestamp routine 2CF9.

Uses a user-owned authentic Z80 ROM locally. Models CPU memory writes and
the original helpers 1783/1775, not full game timing or frame-rate behaviour.
Original ROM, machine-code listings and proprietary data never enter GitHub.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
TABLE = 0x2D41
COUNT_ADDRESSES = (0xED20, 0xED18, 0xED10)
SIGNATURES = (
    (0x2CF9, 0x2CFE, "3223e40e1ed82b128939041498ff36252d9f3aca27d1e58e2ecc8deb99934f95"),
    (0x2CD1, 0x2CF9, "75ab3bb917903898ade228b6da8906c4447a26323ec210e4f11421d1c3090d2d"),
    (0x1783, 0x178D, "8870020766664bfcd4f50d3ec074b7efdfe67570af6de15f5ca389121d686418"),
    (0x1775, 0x1783, "cfc6bafa2799e3ac38a7b52a61645a89fa3549959ab74992a2e9d34fe56ba7fc"),
    (TABLE, TABLE+6, "b3bcdfaa56305fdf6f44195d3f5c7204662529e2977f0a09494d5f704d975ea5"),
)


def _validate(selector: int, timestamp24: int, counter: int,
              linked_address: int, previous_iy: int) -> None:
    if (not 0 <= selector < 3 or not 0 <= timestamp24 < (1 << 24)
            or not 0 <= counter < 65536 or not 0xE000 <= linked_address <= 0xFFE6
            or not 0 <= previous_iy <= 65535):
        raise ValueError("Original selector 0..2, 24-bit timestamp, 16-bit counter and RAM pointer required")


def independent(selector: int, timestamp24: int, counter: int,
                linked_address: int = 0xE900, previous_iy: int = 0) -> dict:
    """Original 2CF9: three linked bytes and saturating-on-overflow counter.

    Counter FFFF is deliberately *not* overwritten with zero: the original
    INC DE / OR D,E / RET Z returns before either store in that case.
    """
    _validate(selector, timestamp24, counter, linked_address, previous_iy)
    new = (counter + 1) & 0xFFFF
    return {
        "linked": list(timestamp24.to_bytes(3, "little")),
        "counter": counter if new == 0 else new,
        "counter_write": new != 0,
        "counter_address": COUNT_ADDRESSES[selector],
        "final_iy": previous_iy,
        "interrupts_enabled": True,  # original DI then unconditional EI
        "original_return_pc": 0x2CF4 if new == 0 else 0x2CF8,
    }


def actual_opcodes(master: bytes, selector: int, timestamp24: int, counter: int,
                   linked_address: int = 0xE900, previous_iy: int = 0) -> dict:
    """Boundedly interpret *actual* original Z80 bytes from 2CF9 and helpers.

    Every instruction is verified against the expected local stage;
    unexpected memory, CALL, pointer or opcode fails closed.
    """
    _validate(selector, timestamp24, counter, linked_address, previous_iy)
    if len(master) != 0x90000:
        raise ValueError("Original master ROM length required")
    ix, iy = 0xE080, previous_iy
    hl = a = d = e = 0
    carry = zero = iff = False
    pc = 0x2CF9
    stack: list[tuple[str, int]] = []
    ram = {ix+0x7C: linked_address & 255, ix+0x7D: linked_address >> 8,
           ix-3: selector}
    ram.update((0xE627+i, x) for i, x in enumerate(timestamp24.to_bytes(3, "little")))
    address = COUNT_ADDRESSES[selector]
    ram[address], ram[address+1] = counter & 255, counter >> 8
    writes: list[tuple[int, int]] = []
    finish = None

    def read(addr: int) -> int:
        if 0 <= addr < 0xE000:
            return master[addr]
        if addr not in ram:
            raise ValueError(f"Unexpected original RAM read at {addr:04X}")
        return ram[addr]

    def write(addr: int, value: int) -> None:
        if not 0xE000 <= addr < 0x10000:
            raise ValueError(f"Unexpected original ROM write at {addr:04X}")
        ram[addr] = value & 255
        writes.append((addr, value & 255))

    for _ in range(110):
        op = master[pc]
        if op == 0x21:       # LD HL,table
            hl = master[pc+1] | (master[pc+2] << 8); pc += 3
        elif op == 0x18:     # JR relative
            rel = master[pc+1]
            pc = (pc+2+(rel if rel < 128 else rel-256)) & 65535
        elif op == 0xE5:     # PUSH HL
            stack.append(("hl", hl)); pc += 1
        elif op == 0xE1:     # POP HL
            tag, hl = stack.pop()
            if tag != "hl": raise ValueError("Unbalanced original HL")
            pc += 1
        elif op == 0xFD:
            sub = master[pc+1]
            if sub == 0xE5:        # PUSH IY
                stack.append(("iy", iy)); pc += 2
            elif sub == 0xE1:      # POP IY, including 1783 PUSH HL/POP IY
                tag, iy = stack.pop()
                if tag not in ("hl", "iy"): raise ValueError("Original IY stack mismatch")
                pc += 2
            elif sub in (0x75, 0x74, 0x77):
                disp = master[pc+2]
                value = (hl & 255) if sub == 0x75 else (hl >> 8) if sub == 0x74 else a
                write((iy+disp) & 65535, value); pc += 3
            else:
                raise ValueError(f"Unexpected original FD opcode at {pc:04X}")
        elif op == 0xDD:
            sub, disp = master[pc+1:pc+3]
            if (sub, disp) not in ((0x66, 0x7D), (0x6E, 0x7C), (0x7E, 0xFD)):
                raise ValueError(f"Unexpected original indexed opcode at {pc:04X}")
            index = (ix + (disp-256 if disp >= 128 else disp)) & 65535
            value = read(index)
            if sub == 0x66: hl = (value << 8) | (hl & 255)
            elif sub == 0x6E: hl = (hl & 0xFF00) | value
            else: a = value
            pc += 3
        elif op == 0xCD:
            target = master[pc+1] | (master[pc+2] << 8)
            if target not in (0x1783, 0x1775):
                raise ValueError("Unverified helper call in original counter")
            stack.append(("ret", pc+3)); pc = target
        elif op in (0xC9, 0xC8):
            if op == 0xC8 and not zero: pc += 1; continue
            if stack:
                tag, pc = stack.pop()
                if tag != "ret": raise ValueError("Original return stack imbalance")
            else:
                finish = pc
                break
        elif op == 0xF3: iff = False; pc += 1
        elif op == 0xFB: iff = True; pc += 1
        elif op == 0x2A:
            addr = master[pc+1] | (master[pc+2] << 8)
            hl = read(addr) | (read(addr+1) << 8); pc += 3
        elif op == 0x3A:
            addr = master[pc+1] | (master[pc+2] << 8)
            a = read(addr); pc += 3
        elif op == 0x87:
            product = a*2; a, carry = product & 255, product > 255; zero = a == 0; pc += 1
        elif op == 0x85:
            result = a + (hl & 255)
            a, carry = result & 255, result > 255
            zero = a == 0; pc += 1
        elif op == 0x6F: hl = (hl & 0xFF00) | a; pc += 1
        elif op == 0x30:
            off = master[pc+1]
            pc += 2 + ((off if off < 128 else off-256) if not carry else 0)
        elif op == 0x24: hl = ((((hl >> 8)+1) & 255) << 8) | (hl & 255); pc += 1
        elif op == 0x7E: a = read(hl); pc += 1
        elif op == 0x23: hl = (hl+1) & 65535; pc += 1
        elif op == 0x66: hl = (read(hl) << 8) | (hl & 255); pc += 1
        elif op == 0x5E: e = read(hl); pc += 1
        elif op == 0x56: d = read(hl); pc += 1
        elif op == 0x13:
            number = (((d << 8) | e)+1) & 65535
            d, e = number >> 8, number & 255
            pc += 1
        elif op == 0x7A: a = d; pc += 1
        elif op == 0xB3: a |= e; zero, carry = a == 0, False; pc += 1
        elif op == 0x72: write(hl, d); pc += 1
        elif op == 0x2B: hl = (hl-1) & 65535; pc += 1
        elif op == 0x73: write(hl, e); pc += 1
        else:
            raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")

    if finish not in (0x2CF4, 0x2CF8):
        raise ValueError("Original routine failed to reach its verified return")
    return {
        "linked": [ram[(linked_address+0x17+i) & 65535] for i in range(3)],
        "counter": ram[address] | (ram[address+1] << 8),
        "counter_write": (address, (counter+1) & 255) in writes,
        "counter_address": address,
        "final_iy": iy, "interrupts_enabled": iff,
        "original_return_pc": finish,
    }


def verify(master: bytes, cases: int = 30000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Authenticated original 1991 arcade master required")
    for start, stop, expected in SIGNATURES:
        if sha256(master[start:stop]).hexdigest() != expected:
            raise ValueError(f"Original stage signature mismatch at {start:04X}")
    if tuple(master[TABLE+2*i] | (master[TABLE+2*i+1] << 8) for i in range(3)) != COUNT_ADDRESSES:
        raise ValueError("Original three-entry counter selection table differs")
    if not 0 <= cases <= 200000: raise ValueError("Case budget out of range")

    rng = Random(0x2CF9)
    counts = Counter()
    for i in range(cases):
        selector = i % 3
        timer = rng.randrange(1 << 24)
        old = rng.choice((0, 1, 0x7FFE, 0x7FFF, 0xFFFE, 0xFFFF, rng.randrange(65536)))
        linked = 0xE900 if i % 4 == 0 else 0xE650
        previous_iy = rng.randrange(65536)
        expected = independent(selector, timer, old, linked, previous_iy)
        actual = actual_opcodes(master, selector, timer, old, linked, previous_iy)
        if expected != actual:
            raise AssertionError(f"Original counter opcode mismatch #{i}: {expected} != {actual}")
        counts["held_at_FFFF" if old == 0xFFFF else "incremented"] += 1
        counts[f"selector_{selector}"] += 1
    return {"original_stage":"master 2CF9; helpers 1783 and 1775",
            "cases":cases,"mismatches":0,"branch_cases":dict(counts),
            "verified_counter_addresses":[f"{x:04X}" for x in COUNT_ADDRESSES],
            "outstanding":"Real original timer units and the linked record's gameplay meaning require emulator runtime"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--cases", type=int, default=30000)
    opts = parser.parse_args()
    print(json.dumps(verify(opts.master.read_bytes(), opts.cases), indent=2))
