#!/usr/bin/env python3
"""Original Indy Heat master B6ED-B727 contact-projection classification parity.

Uses a user-supplied, checksum-verified ROM only at local verification time.
The public model is independent integer arithmetic, with an instruction-level
bounded Z80 verifier. It does NOT implement full collision or driving physics.
Original ROM files, derived tables, sprites and disassembly must stay private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from random import Random

MASTER_HASH = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_HASH = "1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
START, STOP = 0xB6ED, 0xB728
STAGE_HASH = "26c2518291bc6c7c30213890de48ef122aac164c519e5f90aa9a1fabad0ef215"
TABLE_BASE, TABLE_COUNT = 0xBC5C, 24
# Live original MAME found E919 low-five-bit categories 24,25,27 and 30.
# The genuine Z80 indexed helper has NO guard: categories 24..31 read
# eight pairs of original ROM bytes following the 24-record table, which
# are adjacent instruction bytes. It is a real arcade behaviour/quirk.
# Rejecting indices 24..31 was a reverse-engineering fidelity bug.
ORIGINAL_CATEGORY_COUNT = 32
TABLE_SHA = "09b4dbd06e58a99a71a19b963e093603d70403d77370f25f399aea5ed2408c49"
ORIGINAL_LOOKUP_WINDOW_SHA = "36a264d9f24ae68a3a48c1269af60ba6d13143ee5e2b378730b37debe60dabb5"
HELPER_LOOKUP_SHA = "4f7f30e081e5e2f5c619823771e06b1f890771c9211435bca09f3bca9c4dd63d"
HELPER_OVERFLOW_SHA = "f41853782747fdc939c855044f587ca6ee57cc759abae23d038b1d0d554cfa08"


def signed8(value: int) -> int:
    return value - 256 if value & 128 else value


def trig8(angle: int, cosine: bool) -> int:
    function = math.cos if cosine else math.sin
    return max(-128, min(127, round(128 * function((angle & 255) * math.tau / 256)))) & 255


def xrom_hi_math(a: int, b: int) -> int:
    product = signed8(a) * signed8(b) * 2
    return (max(-32768, min(32767, product)) >> 8) & 255


def lookup_original_indexed_byte(master: bytes, e919: int) -> int:
    """Model genuine unguarded original Z80 indexed-ROM byte access.

    Only the first 24 records are a structured contact table. The other
    eight reachable indices read the actual adjacent original CPU ROM
    instruction bytes. Never invent fallback data or reject them.
    """
    if len(master) != 0x90000 or not 0 <= e919 <= 255:
        raise ValueError("Original master ROM and 8-bit E919 category required")
    return master[TABLE_BASE + 2 * (e919 & 31)]


def model(table_byte: int, iy_state_3d: int, d: int, e: int) -> tuple[int, int, str]:
    """Independent integer model: (E925, projected signed byte, next PC).

    This model uses one table byte supplied privately at verification time;
    no original proprietary contact table is reproduced in public code.
    """
    if any(not 0 <= x <= 255 for x in (table_byte, iy_state_3d, d, e)):
        raise ValueError("Original event, orientation and projection operands must be bytes")
    angle = ((table_byte & 0xC0) + iy_state_3d) & 255
    first = signed8(xrom_hi_math(d, trig8(angle, True)))
    second = signed8(xrom_hi_math(e, trig8(angle, False)))
    summed = max(-128, min(127, first + second + 1))
    dest = 0xB86C if summed < 0 else 0xB778 if summed < 4 else STOP
    return table_byte & 0x33, summed & 255, f"{dest:04X}"


def execute_original(master: bytes, xrom: bytes, e919: int,
                     iy_state_3d: int, d_input: int, e_input: int
                     ) -> tuple[int, int, str]:
    """Execute real bounded master Z80 instructions and both short helpers.

    Every opcode, branch, memory source and expected stage exit is checked.
    All unrecognised control flows stop with an error instead of guessing.
    """
    if len(master) != 0x90000 or len(xrom) != 0x40000:
        raise ValueError("Original master and X-ROM dimensions required")
    if any(not 0 <= x <= 255 for x in (e919, iy_state_3d, d_input, e_input)):
        raise ValueError("Original inputs must be unsigned 8-bit values")

    a = b = c = h = l = 0
    d, e = d_input, e_input
    carry = zero = sign = overflow = False
    xrom_address = 0
    ram = {0xE919: e919}
    stack: list[int] = []
    pc = START

    for _ in range(100):
        op = master[pc]
        if op == 0x3A:  # LD A,(absolute)
            address = master[pc+1] | master[pc+2] << 8
            if address == 0xE919:
                a = ram[address]
            elif address == 0xFFFD:
                a = xrom[2*xrom_address + 1]
            else:
                raise ValueError(f"Unexpected original byte read {address:04X}")
            pc += 3
        elif op == 0xE6:  # AND immediate
            a &= master[pc+1]
            carry, zero, sign, overflow = False, (a == 0), bool(a & 128), False
            pc += 2
        elif op == 0x87:  # ADD A,A
            previous = a
            value = a * 2
            carry, a = value > 255, value & 255
            zero, sign = (a == 0), bool(a & 128)
            overflow = bool((previous ^ a) & 128)
            pc += 1
        elif op == 0x21:  # LD HL,immediate
            l, h = master[pc+1:pc+3]
            pc += 3
        elif op == 0xCD:  # CALL original indexed-table lookup
            address = master[pc+1] | master[pc+2] << 8
            if address != 0x1747:
                raise ValueError(f"Unexpected original CALL {address:04X}")
            stack.append(pc+3)
            pc = address
        elif op == 0x85:  # ADD A,L in helper
            old = a
            value = a + l
            carry, a = value > 255, value & 255
            zero, sign = (a == 0), bool(a & 128)
            overflow = bool((old ^ a) & (l ^ a) & 128)
            pc += 1
        elif op == 0x6F:
            l = a
            pc += 1
        elif op == 0x30:  # JR NC
            delta = signed8(master[pc+1])
            pc += 2 + (delta if not carry else 0)
        elif op == 0x24:
            h = (h + 1) & 255  # INC H does not modify previous carry
            pc += 1
        elif op == 0x7E:
            address = (h << 8) | l
            if not TABLE_BASE <= address < TABLE_BASE + 2*ORIGINAL_CATEGORY_COUNT:
                raise ValueError(f"Unexpected original indexed ROM address {address:04X}")
            a = master[address]
            pc += 1
        elif op == 0xC9:
            if not stack:
                raise ValueError("Unexpected original RET without a call")
            pc = stack.pop()
        elif op == 0x67:
            h = a
            pc += 1
        elif op == 0x32:  # LD (E925),A
            address = master[pc+1] | master[pc+2] << 8
            if address != 0xE925:
                raise ValueError(f"Unexpected original RAM write {address:04X}")
            ram[address] = a
            pc += 3
        elif op == 0x7C:
            a = h
            pc += 1
        elif op == 0xFD:  # ADD A,(IY-$43), original slot offset +$3D
            if master[pc+1:pc+3] != bytes.fromhex("86bd"):
                raise ValueError(f"Unexpected original IY opcode at {pc:04X}")
            previous = a
            value = a + iy_state_3d
            carry, a = value > 255, value & 255
            zero, sign = (a == 0), bool(a & 128)
            overflow = bool((~(previous ^ iy_state_3d) & (previous ^ a) & 128))
            pc += 3
        elif op == 0x26:
            h = master[pc+1]
            pc += 2
        elif op in (0x46, 0x4E):  # LD B/C,(HL)
            address = (h << 8) | l
            if not (0xA200 <= address < 0xA300 or 0xA500 <= address < 0xA600):
                raise ValueError(f"Unexpected original trigonometric table {address:04X}")
            if op == 0x46:
                b = master[address]
            else:
                c = master[address]
            pc += 1
        elif op == 0x62:
            h = d
            pc += 1
        elif op == 0x68:
            l = b
            pc += 1
        elif op == 0x63:
            h = e
            pc += 1
        elif op == 0x69:
            l = c
            pc += 1
        elif op == 0x22:  # LD (FFFC),HL: original X-ROM address latch
            address = master[pc+1] | master[pc+2] << 8
            if address != 0xFFFC:
                raise ValueError("Unexpected original X-ROM address write")
            xrom_address = (h << 8) | l
            pc += 3
        elif op == 0x2A:  # LD HL,(FFFC): original X-ROM result
            address = master[pc+1] | master[pc+2] << 8
            if address != 0xFFFC:
                raise ValueError("Unexpected original X-ROM word read")
            product = xrom[2*xrom_address] | xrom[2*xrom_address+1] << 8
            h, l = product >> 8, product & 255
            pc += 3
        elif op == 0x37:  # SCF
            carry = True
            pc += 1
        elif op == 0x8C:  # ADC A,H, original signed overflow flags
            previous = a
            value = a + h + int(carry)
            carry, a = value > 255, value & 255
            zero, sign = (a == 0), bool(a & 128)
            overflow = bool((~(previous ^ h) & (previous ^ a) & 128))
            pc += 1
        elif op == 0xEC:  # CALL PE original signed saturation helper
            address = master[pc+1] | master[pc+2] << 8
            if address != 0x0B3E:
                raise ValueError("Unexpected original overflow helper")
            pc += 3
            if overflow:
                stack.append(pc)
                pc = address
        elif op == 0xF2:  # JP P in signed saturation helper
            address = master[pc+1] | master[pc+2] << 8
            if address != 0x0B45:
                raise ValueError("Unexpected original saturation return target")
            pc = address if not sign else pc+3
        elif op == 0x3E:
            a = master[pc+1]
            pc += 2
        elif op == 0xB7:  # OR A in signed saturation helper
            zero, sign, overflow, carry = (a == 0), bool(a & 128), False, False
            pc += 1
        elif op == 0xFA:  # JP M to alternate original contact path
            address = master[pc+1] | master[pc+2] << 8
            if address != 0xB86C:
                raise ValueError("Unexpected original negative-projection path")
            pc = address if sign else pc+3
        elif op == 0xFE:  # CP immediate
            limit = master[pc+1]
            if limit != 4:
                raise ValueError("Unexpected original contact projection threshold")
            diff = a-limit
            carry, zero, sign = (diff < 0), (diff == 0), bool(diff & 128)
            pc += 2
        elif op == 0x38:  # JR C to original low-projection path
            delta = signed8(master[pc+1])
            pc += 2 + (delta if carry else 0)
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")

        if pc in (STOP, 0xB778, 0xB86C):
            if stack or 0xE925 not in ram:
                raise ValueError("Original stage exited with incomplete state/call stack")
            return ram[0xE925], a, f"{pc:04X}"
        if not (START <= pc < STOP or 0x1747 <= pc <= 0x174D
                or 0x0B3E <= pc <= 0x0B48):
            raise ValueError(f"Original code left verified stage at {pc:04X}")
    raise ValueError("Original Z80 stage exceeded bounded instruction budget")


def verify(master: bytes, xrom: bytes, cases: int = 100000) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_HASH:
        raise ValueError("Private original verified master required")
    if len(xrom) != 0x40000 or hashlib.sha256(xrom).hexdigest() != XROM_HASH:
        raise ValueError("Private original verified X-ROM required")
    signatures = [
        (START, STOP, STAGE_HASH),
        (0x1747, 0x174E, HELPER_LOOKUP_SHA),
        (0x0B3E, 0x0B4A, HELPER_OVERFLOW_SHA),
        (TABLE_BASE, TABLE_BASE+2*TABLE_COUNT, TABLE_SHA),
        (TABLE_BASE, TABLE_BASE+2*ORIGINAL_CATEGORY_COUNT, ORIGINAL_LOOKUP_WINDOW_SHA),
    ]
    for first, last, expected in signatures:
        if hashlib.sha256(master[first:last]).hexdigest() != expected:
            raise ValueError(f"Original stage/table {first:04X} checksum mismatch")
    if not 0 <= cases <= 500000:
        raise ValueError("Invalid bounded verification count")

    for heading in range(256):
        for cosine, page in ((True, 0xA200), (False, 0xA500)):
            if master[page+heading] != trig8(heading, cosine):
                raise ValueError(f"Original trig sample mismatch at heading {heading}")
    for a in range(256):
        for b in range(256):
            address = (a << 8) | b
            if xrom[2*address+1] != xrom_hi_math(a, b):
                raise ValueError(f"Original X-ROM high-byte mismatch: {a},{b}")

    rng = Random(0xB6ED)
    branches = {"B728": 0, "B778": 0, "B86C": 0}
    adjacent_rom_case_count = 0
    source_categories = set()
    for i in range(cases):
        # Deterministic full 0..31 coverage with all upper E919 bits
        # exercised. Codes 24..31 are VALID real arcade ROM reads.
        contact = (i % ORIGINAL_CATEGORY_COUNT) | (rng.randrange(8) << 5)
        source_categories.add(contact & 31)
        adjacent_rom_case_count += (contact & 31) >= TABLE_COUNT
        source_table_byte = lookup_original_indexed_byte(master, contact)
        orientation = rng.randrange(256) if i%4 else (i//4)%256
        d = rng.randrange(256) if i%5 else (i//5)%256
        e = rng.randrange(256) if i%6 else (i//6)%256
        reference = model(source_table_byte, orientation, d, e)
        machine = execute_original(master, xrom, contact, orientation, d, e)
        if reference != machine:
            raise AssertionError(f"Original B6ED collision projection mismatch {i}: "
                                 f"model={reference} machine={machine}")
        branches[machine[2]] += 1

    return {
        "source": "original 1991 arcade master Z80 B6ED-B727",
        "cases": cases,
        "mismatches": 0,
        "original_next_pc_branches": branches,
        "original_defined_contact_records": TABLE_COUNT,
        "original_live_reachable_category_indices": ORIGINAL_CATEGORY_COUNT,
        "categories_verified": sorted(source_categories),
        "adjacent_program_byte_lookup_cases": adjacent_rom_case_count,
        "adjacent_program_byte_indices": list(range(TABLE_COUNT, ORIGINAL_CATEGORY_COUNT)),
        "original_trigonometry_bytes_checked": 512,
        "original_xrom_high_bytes_checked": 65536,
        "original_stage_sha256": STAGE_HASH,
        "scope": "exact original 0..31 ROM lookup, including genuine 24..31 instruction-adjacent reads; projected branch only, not full collision physics",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("xrom", type=Path)
    parser.add_argument("--cases", type=int, default=100000)
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/contact_projection_b6ed.json"))
    args = parser.parse_args()
    report = verify(args.master.read_bytes(), args.xrom.read_bytes(), args.cases)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
