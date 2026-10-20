#!/usr/bin/env python3
"""Recover original Indy Heat's 14 course-dependent rectangular event bounds.

Original master Z80 (1991 arcade) at PC 7A98/7AA1 chooses pairs from the
83B6 and 1ACE tables based on RAM E699, storing them at E95B and E642.
The code at 7AB4..7AE2 tests the car's coordinate *high bytes* within both
ranges and an additional six-unit car-relative gate before changing status.
This is a VERIFIED spatial trigger; its game-purpose (pit/lap/etc.) is NOT
verified without live gameplay traces. No original data is committed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
COUNT = 14
AXIS_E72C_TABLE = 0x83B6
AXIS_E736_TABLE = 0x1ACE

SIGNATURES = (
    (0x7A98, "21 b6 83 cd 67 17 22 5b e9"),
    (0x7AA1, "21 ce 1a cd 67 17 22 42 e6"),
    (0x7ABE, "3a 2c e7 dd 96 66 c6 03 fe 06 30 f2"),
    (0x7ACA, "3a 36 e7 2a 42 e6 bc 30 e9 bd 38 e6"),
    (0x7AD6, "3a 2c e7 2a 5b e9 bc 30 dd bd 38 da"),
)


def accept_coordinate(lower: int, upper: int, value: int) -> bool:
    """Original CP H / JR NC / CP L / JR C: lower inclusive, upper exclusive."""
    if any(not 0 <= n <= 255 for n in (lower, upper, value)):
        raise ValueError("Original coordinate comparisons operate on bytes")
    return lower <= value < upper


def accept_spatial_gate(coord_e72c: int, slot_ix_66: int,
                        range_e72c: tuple[int, int],
                        coord_e736: int, range_e736: tuple[int, int]) -> bool:
    """Original PC 7ABE..7AE2 qualification, before bit/status branches."""
    if any(not 0 <= n <= 255 for n in (coord_e72c, slot_ix_66, coord_e736)):
        raise ValueError("Coordinate fields must be bytes")
    # Z80 SUB / ADD wrap at 8 bits, CP 6; no signed comparison.
    offset = (coord_e72c - slot_ix_66 + 3) & 255
    return (offset < 6 and
            accept_coordinate(*range_e736, coord_e736) and
            accept_coordinate(*range_e72c, coord_e72c))


def extract(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != EXPECTED_SHA:
        raise ValueError("Verified original arcade master ROM region required")
    for pc, hex_bytes in SIGNATURES:
        expected = bytes.fromhex(hex_bytes)
        if master[pc:pc+len(expected)] != expected:
            raise ValueError(f"Original course boundary code differs at {pc:04X}")
    rectangles = []
    for course in range(COUNT):
        a = master[AXIS_E72C_TABLE+2*course:AXIS_E72C_TABLE+2*course+2]
        b = master[AXIS_E736_TABLE+2*course:AXIS_E736_TABLE+2*course+2]
        if len(a) != 2 or len(b) != 2 or a[0] >= a[1] or b[0] >= b[1]:
            raise ValueError(f"Original course {course} does not contain ordered bounds")
        rectangles.append({
            "course_internal_index": course,
            "RAM_E95B_comparison_axis_E72C": {"inclusive_min": a[0], "exclusive_max": a[1]},
            "RAM_E642_comparison_axis_E736": {"inclusive_min": b[0], "exclusive_max": b[1]},
        })
    return {
        "source": "Indy Heat 1991 original arcade master Z80",
        "course_selector_ram": "E699",
        "course_count": COUNT,
        "source_tables": ["83B6", "1ACE"],
        "loaded_bound_ram": ["E95B", "E642"],
        "event_check_code": "7AB4..7AE2",
        "additional_condition": "((RAM8[E72C] - car[IX+0x66] + 3) & 255) < 6",
        "course_dependent_spatial_bounds": rectangles,
        "unknown": "What specific event the code is gating; live race observation needed",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path, help="Private arcade master.mame_runtime.bin")
    p.add_argument("--out", type=Path,
                   default=Path("local/recovery/14_course_spatial_gate_bounds.json"))
    a = p.parse_args()
    r = extract(a.master.read_bytes())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print("Decoded", r["course_count"], "original course-linked event rectangles")
    print("Original boundary data is private and must not be committed.")
    print("No pit or lap semantics verified yet.")


if __name__ == "__main__":
    main()
