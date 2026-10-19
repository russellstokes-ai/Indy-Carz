#!/usr/bin/env python3
"""Inspect original 1991 Indy Heat arcade executable for verified control data.

Input: locally reconstructed MAME master Z80 memory image (never commit ROMs).
Output: recovered 32-entry steering table, 5 player/car state slots, and
cross-bank callsite addresses. No original ROM data is distributed here.
Static inspection is not a substitute for runtime instruction traces.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

STEERING_CODE = 0x0D6A
STEERING_LUT = 0x0DCD
BANK_TRAMPOLINES = {0x145F: 2, 0x1490: 3, 0x14C1: 4}
CAR_RECORDS = [0xE080 + 0x100 * i for i in range(5)]


def steering_table(master: bytes) -> list[int]:
    if len(master) != 0x90000:
        raise ValueError("Expected 0x90000-byte MAME-rotated master region")
    # SUB L; AND $1f; LD HL,$0dcd
    if master[STEERING_CODE:STEERING_CODE + 6] != bytes.fromhex(
        "95 e6 1f 21 cd 0d"
    ):
        raise ValueError("Original arcade steering-code signature not found")
    return list(master[STEERING_LUT:STEERING_LUT + 32])


def mame_dial_encode(current: int, last_input: int, last_encoded: int) -> int:
    """MAME dial-encoder behaviour feeding the original arcade Z80 routine.

    Separately reconstructed from leland_m.cpp's dial_compute_value.
    This handles the *hardware* input; it does not calculate vehicle yaw.
    """
    delta = (current & 255) - (last_input & 255)
    result = last_encoded & 0x80
    if delta > 128:
        delta -= 256
    elif delta < -128:
        delta += 256
    if delta < 0:
        result = 0x80
        delta = -delta
    elif delta > 0:
        result = 0
    delta = min(delta, 31)
    return result | ((last_encoded + delta) & 31)


def game_steering_input(encoded: int, prior_phase: int, lookup: list[int]) -> tuple[int, int]:
    """Reimplementation of original $0d6a steering-lookup transform.

    Returns (new 5-bit wheel phase, signed 8-bit response for car-state
    field IX+$7a). Does not infer the *downstream* yaw/physics formula.
    """
    if len(lookup) != 32:
        raise ValueError("Steering lookup must contain 32 values")
    phase = encoded & 31
    diff = (phase - (prior_phase & 31)) & 31
    response = lookup[diff] if encoded & 0x80 else -lookup[diff]
    response &= 0xFF
    return phase, (response - 256 if response & 0x80 else response)


def far_calls(master: bytes) -> list[dict]:
    """Parse fixed-code bank-switch wrappers and their inline DW target words.

    Original trampoline at $145f/$1490/$14c1 consumes the two bytes after
    each CALL as a target in bank 2/3/4, then restores the caller bank.
    Signature matches are *candidates* pending dynamic execution coverage.
    """
    if len(master) != 0x90000:
        raise ValueError("Expected 0x90000-byte master region")
    calls = []
    for pc in range(0x1FFC):
        if master[pc] != 0xCD:
            continue
        wrapper = master[pc + 1] | (master[pc + 2] << 8)
        if wrapper not in BANK_TRAMPOLINES:
            continue
        dest = master[pc + 3] | (master[pc + 4] << 8)
        if 0x2000 <= dest < 0xA000:
            calls.append({
                "callsite": f"{pc:04X}", "bank": BANK_TRAMPOLINES[wrapper],
                "target": f"{dest:04X}", "resume": f"{pc + 5:04X}",
            })
    return calls


def inspect(master: bytes) -> dict:
    return {
        "status": "Verified static ROM signatures; physics/AI runtime parity unverified",
        "steering": {
            "routine": "0D6A", "table_address": "0DCD",
            "lookup": steering_table(master),
            "meaning": "Input response, NOT car heading or acceleration",
        },
        "car_state": {
            "five_records": [f"{addr:04X}" for addr in CAR_RECORDS],
            "record_stride": 256,
            "primary_steering_offset": 121,
            "sample_steering_offset": 122,
        },
        "three_player_input_dispatch": "0C4A",
        "banked_call_sites": far_calls(master),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master_runtime", type=Path)
    parser.add_argument("--out", type=Path,
                        default=Path("local/recovery/arcade_logic_probe.json"))
    args = parser.parse_args()
    result = inspect(args.master_runtime.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Recovered %d fixed-code banked callsites and 32 steering steps." %
          len(result["banked_call_sites"]))
    print("Private result: %s" % args.out)


if __name__ == "__main__":
    main()
