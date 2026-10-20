#!/usr/bin/env python3
"""Original Indy Heat 1991 arcade race countdown and three-slot transition gate.

Master bank 3:
  6218-6227: original 16-bit countdown seed, 0x0084 or 0x00C6.
  627C-62A8: 3-slot status gate vs a decrementing 16-bit countdown.

The source Z80 opcodes are verified privately against an independent state
model. The meaning of the status bits and tick duration are NOT confirmed.
No original proprietary ROM, art, sounds or original assembly is published.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
BANK3_BASE = 0x28000
TIMER_START, TIMER_STOP = 0x6218, 0x6228
GATE_START, GATE_STOP = 0x627C, 0x62A9
TIMER_SHA = "c55937c143164b0e6a973e09924534208f2d409673925845ecd07d490b02f0bb"
GATE_SHA = "d73e8d48910d49932afae247f88d35cf3cf1edc61dbd218c63d5c25712d07138"


def independent_timer(round_index: int) -> int:
    if not 0 <= round_index < 15:
        raise ValueError("Original fifteen-round index must be 0..14")
    return 0x00C6 if round_index == 14 else 0x0084


def independent_gate(e603: int, slot_bytes: tuple[tuple[int, int], ...],
                     e7d2: int) -> dict:
    """Each pair is physical original slot bytes (+B1,+77), in slot order.

    Original E603 nonzero forces the countdown. When zero, each of
    the FIRST THREE state slots passes if either of its two fields
    has bit 0 set. No gameplay semantics are assigned to these flags.
    """
    if not (0 <= e603 <= 255 and 0 <= e7d2 <= 65535 and len(slot_bytes) == 3
            and all(len(pair) == 2 and all(0 <= x <= 255 for x in pair)
                    for pair in slot_bytes)):
        raise ValueError("E603 byte, three original status pairs and E7D2 word required")
    if e603 == 0 and all(((x | y) & 1) != 0 for x, y in slot_bytes):
        return {
            "e7d2": e7d2, "next_pc": 0x62A9,
            "readiness_gate": True, "countdown_decremented": False,
        }
    countdown = (e7d2 - 1) & 65535
    return {
        "e7d2": countdown, "next_pc": 0x62A9 if countdown == 0 else 0x624C,
        "readiness_gate": False, "countdown_decremented": True,
    }


def bank_view(master: bytes) -> bytes:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Authentic checksum-verified 1991 original master ROM required")
    m = bytearray(master[:0xE000])
    m[0x2000:0xA000] = master[BANK3_BASE:BANK3_BASE+0x8000]
    return bytes(m)


def check_original(master: bytes) -> None:
    m = bank_view(master)
    if sha256(m[TIMER_START:TIMER_STOP]).hexdigest() != TIMER_SHA:
        raise ValueError("Original championship countdown seed opcode changed")
    if sha256(m[GATE_START:GATE_STOP]).hexdigest() != GATE_SHA:
        raise ValueError("Original three-slot event gate opcode changed")


def opcode_timer(master: bytes, round_index: int) -> int:
    """Execute the ORIGINAL bank3 countdown setup using Z80 instructions."""
    independent_timer(round_index)
    m = bank_view(master)
    a = h = l = 0
    zero = False
    saved = None
    pc = TIMER_START
    for _ in range(14):
        op = m[pc]
        if op == 0x21:  # LD HL,nn
            l, h = m[pc+1:pc+3]
            pc += 3
        elif op == 0x3A:  # LD A,(E69B)
            address = m[pc+1] | (m[pc+2] << 8)
            if address != 0xE69B:
                raise ValueError("Unexpected original round source")
            a = round_index
            pc += 3
        elif op == 0xFE:  # CP 0E, Z flag
            if m[pc+1] != 0x0E:
                raise ValueError("Original final round index threshold changed")
            zero = (a == 14)
            pc += 2
        elif op == 0x20:  # JR NZ
            displacement = m[pc+1]
            if displacement >= 128:
                displacement -= 256
            pc += 2 + (displacement if not zero else 0)
        elif op == 0x22:  # LD (E7D2),HL
            address = m[pc+1] | (m[pc+2] << 8)
            if address != 0xE7D2:
                raise ValueError("Original countdown store address changed")
            saved = (h << 8) | l
            pc += 3
        else:
            raise ValueError(f"Unexpected original timer instruction {op:02X} at {pc:04X}")
        if pc == TIMER_STOP:
            if saved is None:
                raise ValueError("Original countdown timer store missing")
            return saved
        if not TIMER_START <= pc < TIMER_STOP:
            raise ValueError("Original timer seed escaped bounded stage")
    raise ValueError("Original timer instruction budget exceeded")


def opcode_gate(master: bytes, e603: int,
                slot_bytes: tuple[tuple[int, int], ...], e7d2: int) -> dict:
    """Execute original bank3 627C–62A8 including indexed BIT/DJNZ/JR.

    Returns before either external main-update loop 624C or round
    selection 62A9; neither of those subsequent routines is simulated.
    """
    independent_gate(e603, slot_bytes, e7d2)  # domain check
    m = bank_view(master)
    memory = {0xE603: e603, 0xE7D2: e7d2 & 255, 0xE7D3: e7d2 >> 8}
    ix = b = d = e = h = l = a = 0
    zero = False
    pc = GATE_START
    ready = decrement = False
    for _ in range(80):
        op = m[pc]
        if op == 0x3A:  # LD A,(E603)
            address = m[pc+1] | (m[pc+2] << 8)
            if address != 0xE603:
                raise ValueError("Unexpected original gate RAM read")
            a = memory[address]
            pc += 3
        elif op == 0xB7:  # OR A
            zero = (a == 0)
            pc += 1
        elif op == 0x20:  # JR NZ
            displacement = m[pc+1]
            if displacement >= 128:
                displacement -= 256
            pc += 2 + (displacement if not zero else 0)
        elif op == 0xDD:
            ext = m[pc+1]
            if ext == 0x21:  # LD IX,E080
                ix = m[pc+2] | (m[pc+3] << 8)
                pc += 4
            elif ext == 0xCB:  # BIT 0,(IX+31) or BIT 0,(IX-09)
                displacement, ext_bit = m[pc+2:pc+4]
                if ext_bit != 0x46 or displacement not in (0x31, 0xF7):
                    raise ValueError("Unexpected original indexed status test")
                if ix not in (0xE080, 0xE180, 0xE280):
                    raise ValueError("Original indexed slot escaped first three records")
                pair = slot_bytes[(ix-0xE080)//0x100]
                original_byte = pair[0 if displacement == 0x31 else 1]
                zero = not bool(original_byte & 1)
                pc += 4
            elif ext == 0x19:  # ADD IX,DE
                ix = (ix + ((d << 8) | e)) & 65535
                pc += 2
            else:
                raise ValueError(f"Unexpected original IX instruction {ext:02X}")
        elif op == 0x06:  # LD B,3
            b = m[pc+1]
            if b != 3:
                raise ValueError("Original three-slot check count changed")
            pc += 2
        elif op == 0x11:  # LD DE,0100
            e, d = m[pc+1:pc+3]
            if ((d << 8) | e) != 0x0100:
                raise ValueError("Original three-slot pointer step changed")
            pc += 3
        elif op == 0x28:  # JR Z
            displacement = m[pc+1]
            if displacement >= 128:
                displacement -= 256
            pc += 2 + (displacement if zero else 0)
        elif op == 0x10:  # DJNZ
            displacement = m[pc+1]
            if displacement >= 128:
                displacement -= 256
            b = (b-1) & 255
            pc += 2 + (displacement if b else 0)
        elif op == 0xC3:  # JP 62A9, bypass countdown
            address = m[pc+1] | (m[pc+2] << 8)
            if address != 0x62A9:
                raise ValueError("Original transition target changed")
            ready = True
            pc = address
        elif op == 0x2A:  # LD HL,(E7D2)
            address = m[pc+1] | (m[pc+2] << 8)
            if address != 0xE7D2:
                raise ValueError("Unexpected original countdown source")
            l, h = memory[address], memory[address+1]
            pc += 3
        elif op == 0x2B:  # DEC HL
            result = ((h << 8) | l)-1
            result &= 65535
            h, l = result >> 8, result & 255
            decrement = True
            pc += 1
        elif op == 0x22:  # LD (E7D2),HL
            address = m[pc+1] | (m[pc+2] << 8)
            if address != 0xE7D2:
                raise ValueError("Unexpected original countdown store")
            memory[address], memory[address+1] = l, h
            pc += 3
        elif op == 0x7C:  # LD A,H
            a = h
            pc += 1
        elif op == 0xB5:  # OR L, zero flag
            a |= l
            zero = a == 0
            pc += 1
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")

        if pc in (0x624C, 0x62A9):
            return {
                "e7d2": memory[0xE7D2] | (memory[0xE7D3] << 8),
                "next_pc": pc, "readiness_gate": ready,
                "countdown_decremented": decrement,
            }
        if not GATE_START <= pc < GATE_STOP:
            raise ValueError("Original three-slot gate left bounded region")
    raise ValueError("Original gate instruction budget exceeded")


def verify(master: bytes, cases: int = 60000) -> dict:
    check_original(master)
    for event in range(15):
        if opcode_timer(master, event) != independent_timer(event):
            raise AssertionError(f"Original timer seed mismatch event {event}")
    if not 0 <= cases <= 250000:
        raise ValueError("Invalid original instruction parity case budget")
    rng = Random(0x62A9)
    outcomes = Counter()
    for i in range(cases):
        global_byte = rng.choice((0, 0, 0, 0, 1, 255, rng.randrange(256)))
        pairs = tuple((rng.randrange(256), rng.randrange(256)) for _ in range(3))
        prior_counter = rng.choice((0, 1, 2, 0x84, 0xC6, 65535,
                                    rng.randrange(65536)))
        expected = independent_gate(global_byte, pairs, prior_counter)
        actual = opcode_gate(master, global_byte, pairs, prior_counter)
        if expected != actual:
            raise AssertionError(
                f"Original transition parity mismatch case {i}: model={expected}, "
                f"machine={actual}"
            )
        outcomes[(actual["next_pc"], actual["readiness_gate"])] += 1
    return {
        "source": "Original 1991 arcade master Z80 bank3 6218-6227 and 627C-62A8",
        "seed_rounds_verified": 15,
        "gate_cases": cases,
        "mismatches": 0,
        "ordinary_seed_counter": 132,
        "last_round_seed_counter": 198,
        "outcome_counts": {str(k): v for k, v in sorted(outcomes.items())},
        "limitations": "Real time per tick, meaning of gate flags, downstream original race flow OPEN",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--cases", type=int, default=60000)
    args = parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(), args.cases), indent=2))
