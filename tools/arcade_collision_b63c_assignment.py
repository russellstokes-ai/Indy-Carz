#!/usr/bin/env python3
"""Indy Heat original two-car correction assignment, fixed Z80 B63C-B67D.

Consumes the two exact signed words (BC, DE) from B5C9-B63B and decides how
to apply them to the two original car-state records. Depends on the already
recovered B985/BA20 10-word geometry translators, including their guarded
nonlocal CALL 1689 path and carry from the *last* word addition.

This is an original-ROM-based bounded routine verifier, not a complete
vehicle impulse/damage model or Godot game. Never publish ROM inputs/assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from random import Random

from arcade_collision_geometry_push import model as translate_slot, u16

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
START, END = 0xB63C, 0xB67E
STAGE_SHA = "26ded78ff150d95cb1669636a0a00b230400264a21007953288ff9bddb186c13"


def independent(first: bytes, second: bytes, bc: int, de: int) -> tuple[str, bytes, bytes]:
    """Equivalent original car-selection/translation, preserving Z80 borrow.

    Original slot bit1 at offset +7C diverts which correction routines run.
    Both set delegates to B4EE; this is NOT an assumption of no contact.
    Exceptional geometry translation CALL 1689 is a nonlocal scheduler
    transfer; stop rather than assuming its outcome.
    """
    if len(first) != 256 or len(second) != 256 or not 0 <= bc < 65536 or not 0 <= de < 65536:
        raise ValueError("Expected two original 256-byte slots and 16-bit BC,DE")
    if first[0x7C] & 2:
        if second[0x7C] & 2:
            return "delegated_B4EE", first, second
        result, changed = translate_slot(second, (2*bc) & 65535, (2*de) & 65535)
        return "IY:" + result, first, changed
    if second[0x7C] & 2:
        result, changed = translate_slot(first, (2*bc) & 65535, (2*de) & 65535)
        return "IX:" + result, changed, second

    first_result, changed_first = translate_slot(first, bc, de)
    if first_result != "applied":
        return "IX:" + first_result, first, second

    # The verified original B985 translator leaves carry from its final
    # ADD HL,DE on the tenth (slot+12) translated word. A new LD HL,0
    # does not change carry. SBC HL,BC consumes it.
    carry_from_first = int(u16(first, 0x12) + de > 65535)
    reverse_bc = (-bc - carry_from_first) & 65535
    # Carry (borrow) of 0 - BC - carry_from_first affects the next SBC HL,DE.
    next_carry = int(bc + carry_from_first > 0)
    reverse_de = (-de - next_carry) & 65535

    second_result, changed_second = translate_slot(second, reverse_bc, reverse_de)
    return "IY:" + second_result, changed_first, changed_second


def execute_original(master: bytes, first: bytes, second: bytes,
                     bc: int, de: int) -> tuple[str, bytes, bytes]:
    """Execute actual original Z80 opcode/control flow at fixed B63C-B67D.

    Calls to the separately verified B985/BA20 routines use their independent
    helper models; original transfer targets B4EE/1689 are not emulated.
    """
    if len(master) != 0x90000 or len(first) != 256 or len(second) != 256:
        raise ValueError("Original arcade master and two original car slots required")
    if not (0 <= bc <= 65535 and 0 <= de <= 65535):
        raise ValueError("Original vector inputs are 16-bit words")

    ix, iy = bytes(first), bytes(second)
    b, c = bc >> 8, bc & 255
    d, e = de >> 8, de & 255
    h = l = carry = 0
    zero = False
    pc = START

    for _ in range(75):
        op = master[pc]
        if op in (0xDD, 0xFD):  # BIT 1,(IX-4) / BIT 1,(IY-4)
            if master[pc+1:pc+4] != bytes.fromhex("cbfc4e"):
                raise ValueError(f"Unexpected original status test at {pc:04X}")
            slot = ix if op == 0xDD else iy
            zero = not bool(slot[0x7C] & 2)
            pc += 4
        elif op == 0x20:  # JR NZ,relative
            delta = master[pc+1]
            if delta >= 128: delta -= 256
            pc += 2 + (delta if not zero else 0)
        elif op == 0xC2:  # JP NZ,B4EE
            target = u16(master, pc+1)
            if target != 0xB4EE:
                raise ValueError(f"Unexpected original contact diversion {target:04X}")
            if not zero:
                return "delegated_B4EE", ix, iy
            pc += 3
        elif op == 0xCD:  # CALL one of the independently verified translators
            target = u16(master, pc+1)
            if target not in (0xB985, 0xBA20):
                raise ValueError(f"Unexpected original geometry target {target:04X}")
            current = ix if target == 0xB985 else iy
            displacement_bc, displacement_de = (b << 8) | c, (d << 8) | e
            result, changed = translate_slot(current, displacement_bc, displacement_de)
            if result != "applied":
                return ("IX" if target == 0xB985 else "IY") + ":" + result, ix, iy
            carry = int(u16(current, 0x12) + displacement_de > 65535)
            if target == 0xB985:
                ix = changed
            else:
                iy = changed
            pc += 3
        elif op == 0x21:  # LD HL,0000
            l, h = master[pc+1:pc+3]
            pc += 3
        elif op == 0xED:  # SBC HL,BC or SBC HL,DE, preserving carry
            suffix = master[pc+1]
            if suffix not in (0x42, 0x52):
                raise ValueError(f"Unexpected original 16-bit subtraction at {pc:04X}")
            amount = (b << 8) | c if suffix == 0x42 else (d << 8) | e
            answer = ((h << 8) | l) - amount - carry
            carry = int(answer < 0)
            answer &= 65535
            h, l = answer >> 8, answer & 255
            pc += 2
        elif op == 0x44:
            b = h; pc += 1
        elif op == 0x4D:
            c = l; pc += 1
        elif op == 0xEB:
            h, l, d, e = d, e, h, l
            pc += 1
        elif op == 0xCB:  # SLA C / RL B / SLA E / RL D
            ext = master[pc+1]
            if ext == 0x21:
                carry, c = (c >> 7) & 1, (c << 1) & 255
            elif ext == 0x10:
                old = b
                b, carry = ((b << 1) | carry) & 255, (old >> 7) & 1
            elif ext == 0x23:
                carry, e = (e >> 7) & 1, (e << 1) & 255
            elif ext == 0x12:
                old = d
                d, carry = ((d << 1) | carry) & 255, (old >> 7) & 1
            else:
                raise ValueError(f"Unexpected original bit-shift at {pc:04X}")
            pc += 2
        elif op == 0xC3:  # JP B67E
            if u16(master, pc+1) != END:
                raise ValueError(f"Unexpected contact tail jump at {pc:04X}")
            pc = END
        else:
            raise ValueError(f"Unexpected original contact-assignment opcode {op:02X} at {pc:04X}")

        if pc == END:
            if first[0x7C] & 2:
                label = "IY:applied"
            elif second[0x7C] & 2:
                label = "IX:applied"
            else:
                label = "IY:applied"
            return label, ix, iy
        if not START <= pc < END:
            raise ValueError(f"Original contact assignment departed fixed routine {pc:04X}")
    raise ValueError("Original collision-assignment instruction budget exceeded")


def verify(master: bytes, cases: int = 40000) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Private checksum-verified original 1991 arcade master ROM required")
    if hashlib.sha256(master[START:END]).hexdigest() != STAGE_SHA:
        raise ValueError("Original B63C-B67D assignment instructions changed")
    if not 0 <= cases <= 200000:
        raise ValueError("Invalid bounded parity test count")

    rng = Random(0xB63C)
    counts: Counter[str] = Counter()
    for i in range(cases):
        left, right = bytearray(rng.randbytes(256)), bytearray(rng.randbytes(256))
        for which, slot in enumerate((left, right)):
            # Exercise all four car bit1 combinations in a deterministic loop.
            status_bit = (i // 4) % 4
            if (status_bit >> which) & 1:
                slot[0x7C] |= 2
            else:
                slot[0x7C] &= ~2
        bc = rng.choice((rng.randrange(1300), (65536 - rng.randrange(1300)) & 65535))
        de = rng.choice((rng.randrange(1300), (65536 - rng.randrange(1300)) & 65535))
        expected = independent(bytes(left), bytes(right), bc, de)
        observed = execute_original(master, bytes(left), bytes(right), bc, de)
        if observed != expected:
            raise AssertionError(f"Original two-car correction mismatch case {i}: "
                                 f"model={expected[0]}, machine={observed[0]}")
        counts[expected[0]] += 1

    return {
        "source": "original 1991 Indy Heat fixed master Z80 B63C-B67D",
        "stage_sha256": STAGE_SHA, "cases": cases, "mismatches": 0,
        "branches": dict(counts),
        "first_car_bit1": "slot+7C controls whether first car can be translated",
        "second_car_bit1": "slot+7C controls whether second car can be translated",
        "both_bit1_set": "nonlocal original branch B4EE; not assumed to be no collision",
        "exact_one_car_case": "double 16-bit BC and DE before translating eligible slot",
        "both_car_case": "first translation carry and subtraction borrow affect reverse second-car correction",
        "scope": "correction application only; B67E effects and full motion/damage still OPEN",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--cases", type=int, default=40000)
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/contact_car_assignment_b63c.json"))
    args = parser.parse_args()
    report = verify(args.master.read_bytes(), args.cases)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
