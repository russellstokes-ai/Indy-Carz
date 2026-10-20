#!/usr/bin/env python3
"""Verify Indy Heat's original 16-slot effect allocator via bounded Z80 opcodes.

Original arcade Z80 master bank0 $8659..$8693. Checks independent allocator
model against the ORIGINAL instruction sequence from a private ROM image.
Does not port/render arcade assets or imply complete physics/AI parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import random
from pathlib import Path

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "ccd8beabde765d10314d9859b94562ed7d759988c45745a44ffb9fd284ae66da"
START, END = 0x8659, 0x8694
POOL_BASE, SLOTS, STRIDE = 0xE800, 16, 16


def independent_allocator(pool: bytes | bytearray, priority: int) -> tuple[int, int | None, bytes]:
    """Result A, selected slot (or None), modified 256-byte pool."""
    if len(pool) != 256 or not 0 <= priority <= 255:
        raise ValueError("Expected 256-byte effect pool and 8-bit requested priority")
    state = bytearray(pool)
    for slot in range(SLOTS):
        if state[slot * STRIDE] == 0:
            state[slot * STRIDE + 1] = priority
            return 1, slot, bytes(state)
    values = [state[slot * STRIDE + 1] for slot in range(SLOTS)]
    minimum = min(values)
    if priority <= minimum:
        return 255, None, bytes(state)
    slot = values.index(minimum)  # original CP C/JP NC retains earlier ties
    state[slot * STRIDE + 1] = priority
    return 0, slot, bytes(state)


def original_opcodes(master: bytes, pool: bytes | bytearray, priority: int) -> tuple[int, int | None, bytes, int]:
    """Fail-closed interpreter for the ORIGINAL master $8659..$8693 sequence."""
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Verified original 1991 arcade master image required")
    if hashlib.sha256(master[START:END]).hexdigest() != STAGE_SHA:
        raise ValueError("Original effect allocator opcode signature changed")
    if len(pool) != 256 or not 0 <= priority <= 255:
        raise ValueError("Unexpected arcade effect pool/priority")
    state = bytearray(pool)
    pc = START
    a = c = d = h = l = 0
    b = priority
    carry = z = False
    iy = None
    stack: list[int] = []
    for step in range(512):
        op = master[pc]
        if op == 0x21:  # LD HL,nn
            l, h = master[pc + 1:pc + 3]
            pc += 3
        elif op == 0x0E:  # LD C,n
            c = master[pc + 1]
            pc += 2
        elif op == 0x7E:  # LD A,(HL)
            if h != 0xE8:
                raise ValueError("Unexpected master RAM pool address")
            a = state[l]
            pc += 1
        elif op == 0xB7:  # OR A
            z, carry = a == 0, False
            pc += 1
        elif op in (0x28, 0x30):  # JR Z / JR NC
            taken = z if op == 0x28 else not carry
            d8 = master[pc + 1]
            pc += 2 + ((d8 - 256 if d8 >= 128 else d8) if taken else 0)
        elif op == 0x7D:  # LD A,L
            a = l
            pc += 1
        elif op in (0x81, 0xC6):  # ADD A,C / ADD A,immediate
            right = c if op == 0x81 else master[pc + 1]
            value = a + right
            a, carry = value & 255, value > 255
            z = a == 0
            pc += 1 if op == 0x81 else 2
        elif op == 0x6F:  # LD L,A
            l = a
            pc += 1
        elif op == 0xD2:  # JP NC,nn
            address = master[pc + 1] | master[pc + 2] << 8
            pc = address if not carry else pc + 3
        elif op == 0x48:  # LD C,B
            c = b
            pc += 1
        elif op == 0xB9:  # CP C
            carry, z = a < c, a == c
            pc += 1
        elif op == 0x4F:  # LD C,A
            c = a
            pc += 1
        elif op == 0x55:  # LD D,L
            d = l
            pc += 1
        elif op == 0x78:  # LD A,B
            a = b
            pc += 1
        elif op == 0x6A:  # LD L,D
            l = d
            pc += 1
        elif op == 0x2D:  # DEC L (carry unchanged)
            l = (l - 1) & 255
            z = l == 0
            pc += 1
        elif op == 0x26:  # LD H,n
            h = master[pc + 1]
            pc += 2
        elif op == 0xE5:  # PUSH HL
            stack.append(h << 8 | l)
            pc += 1
        elif op == 0xFD and master[pc + 1] == 0xE1:  # POP IY
            iy = stack.pop()
            pc += 2
        elif op == 0xFD and master[pc + 1:pc + 3] == bytes.fromhex("7001"):
            if iy is None or (iy & 0xFF00) != POOL_BASE:
                raise ValueError("Unexpected effect slot pointer")
            state[(iy & 255) + 1] = b
            pc += 3
        elif op == 0xAF:  # XOR A
            a, z, carry = 0, True, False
            pc += 1
        elif op == 0xF6:  # OR immediate
            a |= master[pc + 1]
            z, carry = a == 0, False
            pc += 2
        elif op == 0x3C:  # INC A (carry unchanged)
            a = (a + 1) & 255
            z = a == 0
            pc += 1
        elif op == 0xC9:  # RET
            if stack:
                raise ValueError("Unbalanced original effect allocator stack")
            slot = None if iy is None else (iy - POOL_BASE) // STRIDE
            return a, slot, bytes(state), step + 1
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")
        if not START <= pc < END:
            raise ValueError(f"Original effect allocator jumped outside bounded stage: {pc:04X}")
    raise ValueError("Original effect allocator instruction budget exceeded")


def verify(master: bytes, random_cases: int = 16000) -> dict:
    if random_cases < 0 or random_cases > 100000:
        raise ValueError("Invalid bounded random test count")
    rng = random.Random(0x1D17)
    counts = {"free": 0, "replace": 0, "reject": 0}
    comparisons = 0

    def check(pool: bytearray, priority: int) -> None:
        nonlocal comparisons
        expected = independent_allocator(pool, priority)
        observed = original_opcodes(master, pool, priority)
        if observed[:3] != expected:
            raise AssertionError(f"Original arcade effect allocation mismatch for priority {priority}")
        counts[{1: "free", 0: "replace", 255: "reject"}[observed[0]]] += 1
        comparisons += 1

    for requested in range(256):
        for vacancy in (0, 1, 7, 15):
            pool = bytearray(256)
            for i in range(SLOTS):
                pool[STRIDE*i] = 3
                pool[STRIDE*i + 1] = (19*i + 7*requested) & 255
            pool[STRIDE*vacancy] = 0
            check(pool, requested)
        pool = bytearray(256)
        for i in range(SLOTS):
            pool[STRIDE*i] = 3
            pool[STRIDE*i + 1] = requested
        check(pool, requested)
        check(pool, (requested + 1) & 255)
    for iteration in range(random_cases):
        pool = bytearray(rng.randbytes(256))
        for slot in range(SLOTS):
            if iteration % 3 == 1 and rng.randrange(10) == 0:
                pool[slot*STRIDE] = 0
            elif iteration % 3 == 2:
                pool[slot*STRIDE] = 2
                pool[slot*STRIDE + 1] = rng.randrange(4)
            else:
                pool[slot*STRIDE] = rng.randint(1, 255)
        check(pool, rng.randrange(256))
    return {
        "source": "1991 Indy Heat arcade master Z80 bank0 8659..8693",
        "source_stage_sha256": STAGE_SHA,
        "slots": SLOTS, "bytes_per_slot": STRIDE, "pool": "E800..E8FF",
        "parity_cases": comparisons, "mismatches": 0,
        "outcomes": counts, "request": "priority in B",
        "returns": "A=1 free slot; A=0 replaced lowest lower-priority; A=255 rejected; IY=selected slot",
        "scope": "allocator only; complete effect rendering, sound, collision and gameplay semantics remain open",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path, help="Private master.mame_runtime.bin")
    parser.add_argument("--cases", type=int, default=16000)
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/effect_allocator_opcode_parity.json"))
    args = parser.parse_args()
    result = verify(args.master.read_bytes(), args.cases)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
