#!/usr/bin/env python3
"""Recover the authentic 14 x 5 Indy Heat arcade starting-grid records.

Original 1991 arcade master Z80: E699 course index resolves a table at
CPU 6382 (14 pointers); IX+69 is the grid slot within that course.
Each record is 5 bytes: little-endian position stored at E72B, then
little-endian position stored at E735, then heading MSB written into
E767/E769 as an angle with low byte 0.

Extracted ORIGINAL position bytes remain local/private. The public GitHub
repo contains the extractor and ROM-free structural tests, not original data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
COURSE_POINTER_TABLE = 0x6382
COURSES = 14
GRID_SLOTS = 5
RECORD_BYTES = 5


def u16(data: bytes, address: int) -> int:
    return data[address] | data[address+1] << 8


def confirm_routine(master: bytes) -> None:
    # 1767: read E699 and multiply by 2 to index pointer table.
    checks = (
        (0x1767, "3a 99 e6 87 85 6f"),
        # 608F: table 6382, helper 1767, (IX+69) selects 5-byte record.
        (0x608F, "21 82 63 cd 67 17 dd 7e 69 4f 87 87 81"),
        # 60A4..60B3: first two words into shared per-car accumulators.
        (0x60A4, "fd 66 01 fd 6e 00 22 2b e7"),
        (0x60AD, "fd 66 03 fd 6e 02 22 35 e7"),
        # 60B6..60C0: the angle byte is extended with 0 low byte.
        (0x60B6, "fd 66 04 2e 00 22 67 e7 22 69 e7"),
    )
    for addr, expected in checks:
        raw = bytes.fromhex(expected)
        if master[addr:addr + len(raw)] != raw:
            raise ValueError(f"Original grid-recovery instruction mismatch at {addr:04X}")



def decode_championship_order(master: bytes) -> dict:
    """Recover original 15-round sequence and exact 0x0F wrap boundary."""
    # Master bank0 race selector $2941, bank3 wrap/switch routine $62B4.
    if master[0x2941:0x294D] != bytes.fromhex(
        "3a 9b e6 21 bf 1a cd 47 17 32 99 e6"
    ):
        raise ValueError("Original race-index table selector missing")
    bank3_offset = 0x28000 + 0x62B4 - 0x2000
    signature = bytes.fromhex(
        "fe 0f 20 01 af 32 9b e6 21 bf 1a cd 47 17 32 99 e6"
    )
    if master[bank3_offset:bank3_offset+len(signature)] != signature:
        raise ValueError("Original fifteen-round championship wrap logic missing")
    course_indices = list(master[0x1ABF:0x1ABF+15])
    if sorted(set(course_indices)) != list(range(COURSES)):
        raise ValueError("Original championship must reference all 14 unique courses")
    repetitions = [c for c in set(course_indices) if course_indices.count(c) > 1]
    if len(repetitions) != 1 or course_indices.count(repetitions[0]) != 2:
        raise ValueError("Original championship repeat layout changed")
    return {
        "rounds": 15,
        "distinct_courses": COURSES,
        "course_internal_index_per_round": course_indices,
        "repeated_course_internal_index": repetitions[0],
        "table_cpu_address": "1ABF",
        "counter_ram": "E69B",
        "selected_course_ram": "E699",
        "wraps_at_counter": 15,
    }

def decode_course_grid(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Original checksum-verified 1991 arcade master ROM required")
    confirm_routine(master)
    championship = decode_championship_order(master)
    pointers = [u16(master, COURSE_POINTER_TABLE + 2*i) for i in range(COURSES)]
    if pointers[0] != COURSE_POINTER_TABLE + COURSES*2:
        raise ValueError("Original first grid table pointer unexpected")
    if any(b - a != GRID_SLOTS*RECORD_BYTES for a, b in zip(pointers, pointers[1:])):
        raise ValueError("Original course grid pointers not uniformly five records apart")
    if pointers[-1] + GRID_SLOTS*RECORD_BYTES > 0xA000:
        raise ValueError("Original grid table crosses ROM boundary")
    courses = []
    for n, start in enumerate(pointers):
        slots = []
        for slot in range(GRID_SLOTS):
            pos = start + slot*RECORD_BYTES
            slots.append({
                "car_grid_index": slot,
                "state_E72B": u16(master, pos),
                "state_E735": u16(master, pos+2),
                "heading_byte_E768_and_E76A": master[pos+4],
            })
        courses.append({
            "source_course_index": n, "source_cpu_pointer": f"{start:04X}",
            "starting_grid": slots,
        })
    raw = master[pointers[0]:pointers[-1]+GRID_SLOTS*RECORD_BYTES]
    return {
        "source": "indyheat 1991 arcade master ROM; original table starts at CPU $6382",
        "course_selector_ram": "E699",
        "grid_selector_field": "IX+0x69",
        "course_count": len(courses),
        "grid_slots_per_course": GRID_SLOTS,
        "total_records": COURSES*GRID_SLOTS,
        "source_data_digest_sha256": hashlib.sha256(raw).hexdigest(),
        "original_championship": championship,
        "original_course_grids": courses,
        "limitations": "Starting grids only; NOT track boundaries, walls, lap gates, AI routes or full maps",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path, help="Private original MAME-rotated master.bin")
    p.add_argument("--out", type=Path,
                   default=Path("local/recovery/14_original_start_grids.json"))
    args = p.parse_args()
    info = decode_course_grid(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"Recovered {info['course_count']} original circuit starting grids")
    print(f"Recovered {info['total_records']} original five-byte car starting positions")
    print("Output is private original game data; do NOT commit it.")
    print("Track geometry, walls, collisions and AI still require recovery.")


if __name__ == "__main__":
    main()
