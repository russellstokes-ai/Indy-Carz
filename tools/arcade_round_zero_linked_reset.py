#!/usr/bin/env python3
"""Original 1991 arcade first-round linked-state clearing: 2953-2989.

Independent six-slot CPU-bus model and bounded authentic Z80 opcode verifier.
This is NOT proof that the pointed-to addresses represent specific car,
graphics, money, damage or other gameplay state: their physical runtime
mapping requires live MAME investigation. Original ROM stays private.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from random import Random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
START, STOP = 0x2953, 0x298A
HELPER, HELPER_STOP = 0x1783, 0x178D
STAGE_SHA = "97d3392c5641407474fe604b1392a88e6b3c64331f84b2b0665466fc40c0c45c"
HELPER_SHA = "8870020766664bfcd4f50d3ec074b7efdfe67570af6de15f5ca389121d686418"
SLOTS = (0xE580, 0xE480, 0xE380, 0xE280, 0xE180, 0xE080)
CLEARED_OFFSETS = (1, 3, 2, 4, 5, 9, 3, 2, 12)


def validate(pointers: tuple[int, ...]) -> None:
    if len(pointers) != 6 or any(not 0 <= p <= 65535 for p in pointers):
        raise ValueError("Six 16-bit original linked-state pointers required")


def independent(pointers: tuple[int, ...]) -> dict:
    """54 ordered original bus writes, six original car/auxiliary slot visits."""
    validate(pointers)
    writes = [((ptr + off) & 65535, 0)
              for ptr in pointers for off in CLEARED_OFFSETS]
    return {
        "writes": writes, "slot_visits": list(SLOTS),
        "final_ix": 0xDF80, "final_b": 0xFF,
        "last_iy": pointers[-1], "destinations_per_slot": 9,
        "stop_pc": 0x2989,
    }


def opcode(master: bytes, pointers: tuple[int, ...]) -> dict:
    """Interpret original 2953-2989 and helper 1783; stop at original RET.

    The Z80 uses IX=E580 then decrements IX by 0x100 while DEC B stays
    *sign-clear*: B starts at 5, so this runs SIX times, not five.
    The pointer adapter reads (IX+7C,+7D) into ordinary H,L and POPs IY.
    """
    validate(pointers)
    if len(master) != 0x90000:
        raise ValueError("Private reconstructed master size must be 0x90000")
    pointer_ram = {}
    for start, ptr in zip(SLOTS, pointers):
        pointer_ram[start+0x7C] = ptr & 255
        pointer_ram[start+0x7D] = ptr >> 8
    ix = iy = de = h = l = b = 0
    sign = False
    writes = []
    visits = []
    stack = []
    pc = START
    for _ in range(150):
        op = master[pc]
        if op == 0xDD:
            ext = master[pc+1]
            if ext == 0x21:  # LD IX,nn
                ix = master[pc+2] | (master[pc+3] << 8)
                pc += 4
            elif ext in (0x66, 0x6E):  # LD H/L,(IX+d), ordinary H/L
                displacement = master[pc+2]
                if displacement & 128:
                    displacement -= 256
                address = (ix+displacement) & 65535
                if address not in pointer_ram:
                    raise ValueError("Original IX indexed pointer escaped slot")
                if ext == 0x66:
                    h = pointer_ram[address]
                else:
                    l = pointer_ram[address]
                pc += 3
            elif ext == 0x19:  # ADD IX,DE
                ix = (ix+de) & 65535
                pc += 2
            else:
                raise ValueError(f"Unexpected original IX opcode at {pc:04X}")
        elif op == 0xFD:
            ext = master[pc+1]
            if ext == 0xE1:  # POP IY from original PUSH HL
                if not stack:
                    raise ValueError("Original pointer stack underflow")
                iy = stack.pop()
                pc += 2
            elif ext == 0x36:  # LD (IY+d),00
                disp, value = master[pc+2:pc+4]
                if disp not in CLEARED_OFFSETS or value != 0:
                    raise ValueError("Unrecognised original linked-state byte write")
                if disp >= 128:
                    disp -= 256
                writes.append(((iy+disp) & 65535, value))
                pc += 4
            else:
                raise ValueError(f"Unexpected original IY opcode at {pc:04X}")
        elif op == 0x06:
            b = master[pc+1]
            if b != 5:
                raise ValueError("Original DEC B loop count changed")
            pc += 2
        elif op == 0x11:
            de = master[pc+1] | (master[pc+2] << 8)
            if de != 0xFF00:
                raise ValueError("Original IX record step changed")
            pc += 3
        elif op == 0xCD:  # CALL 1783 original pointer adapter
            target = master[pc+1] | (master[pc+2] << 8)
            if target != HELPER:
                raise ValueError("Unexpected original pointer helper")
            visits.append(ix)
            stack.append(pc+3)
            pc = HELPER
        elif op == 0xE5:  # PUSH HL
            stack.append((h << 8) | l)
            pc += 1
        elif op == 0xC9:  # original RET
            if pc == HELPER_STOP-1:
                if not stack:
                    raise ValueError("Original helper return stack empty")
                pc = stack.pop()
            elif pc == STOP-1:
                if stack or len(writes) != 54 or len(visits) != 6:
                    raise ValueError("Original linked-state loop incomplete")
                return {
                    "writes": writes, "slot_visits": visits,
                    "final_ix": ix, "final_b": b, "last_iy": iy,
                    "destinations_per_slot": 9, "stop_pc": pc,
                }
            else:
                raise ValueError("Unexpected original RET")
        elif op == 0x05:  # DEC B sets original sign flag
            b = (b-1) & 255
            sign = bool(b & 128)
            pc += 1
        elif op == 0xF2:  # JP P,295C, sign-clear loops
            target = master[pc+1] | (master[pc+2] << 8)
            if target != 0x295C:
                raise ValueError("Unexpected original six-slot loop target")
            pc = target if not sign else pc+3
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")
        if not (START <= pc < STOP or HELPER <= pc < HELPER_STOP):
            raise ValueError("Original loop jumped outside bounded stage")
    raise ValueError("Original linked-slot opcode budget exceeded")


def verify(master: bytes, cases: int = 12000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Authentic checksum-verified arcade master ROM required")
    for start, end, expected in ((START, STOP, STAGE_SHA),
                                 (HELPER, HELPER_STOP, HELPER_SHA)):
        if sha256(master[start:end]).hexdigest() != expected:
            raise ValueError("Original state-reset instruction fingerprint changed")
    if not 0 <= cases <= 120000:
        raise ValueError("Invalid original instruction test budget")
    rng = Random(0x2953)
    wrapped = aliases = 0
    for index in range(cases):
        ptrs = tuple(rng.choice((rng.randrange(65536), 0xFFFD, 0xFFFF,
                                 0, 0xE6F5, 0xCFFB)) for _ in range(6))
        wrapped += any(ptr & 255 >= 0xF5 for ptr in ptrs)
        aliases += len(set(ptrs)) != 6
        expected = independent(ptrs)
        actual = opcode(master, ptrs)
        if actual != expected:
            wrong = next(k for k in expected if expected[k] != actual[k])
            raise AssertionError(f"Original reset mismatch case {index}, field {wrong}")
    return {
        "source": "Original arcade master 2953-2989, helper 1783",
        "cases": cases, "mismatches": 0,
        "six_record_visits": 6, "bus_writes_per_case": 54,
        "clear_offsets": sorted(set(CLEARED_OFFSETS)),
        "high_byte_wrap_scenarios": wrapped,
        "pointer_alias_scenarios": aliases,
        "limitation": "These are CPU write events; live physical memory mapping remains unknown",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--cases", type=int, default=12000)
    args = parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(), args.cases), indent=2))
