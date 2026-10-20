#!/usr/bin/env python3
"""Recover Indy Heat arcade's per-racer 96-byte working-state serialization.

Original master bank0 Z80:
  $61CE-$6299 copies 48 words from a 0x100-byte racer slot into E72B..E789.
  $629A-$6365 copies the same 48 working words back into that racer slot.
These routines temporarily borrow the CPU stack pointer, DI/EI around the
transfer, and restore the original stack afterwards.

This validates source opcode patterns against the privately reconstructed ROM.
It does NOT claim full collision, AI, fuel or race-rule extraction.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_MASTER = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
WORDS = 48
SCRATCH_FIRST = 0xE72B
SCRATCH_LAST = SCRATCH_FIRST + (WORDS - 1) * 2
LOAD_BODY = 0x61D4
SAVE_BODY = 0x62A0
SLOT_STRIDE = 0x100
SLOTS = 6


def parse_block(master: bytes, body: int, loading: bool) -> list[int]:
    """Verify exact 48 original POP/LD or LD/PUSH instruction pairs."""
    pc = body
    found = []
    for i in range(WORDS):
        address = (SCRATCH_FIRST + 2*i if loading
                   else SCRATCH_LAST - 2*i)
        if loading:
            # POP HL ; LD (nn),HL
            expected = bytes([0xE1, 0x22, address & 255, address >> 8])
        else:
            # LD HL,(nn) ; PUSH HL
            expected = bytes([0x2A, address & 255, address >> 8, 0xE5])
        if master[pc:pc+4] != expected:
            raise ValueError(f"Original {'load' if loading else 'save'} opcode discrepancy at {pc:04X}")
        found.append(address)
        pc += 4
    if pc != (0x6294 if loading else 0x6360):
        raise ValueError("Wrong original block length")
    return found


def validate_routine_wrappers(master: bytes) -> None:
    # DI / LD (E92F),SP / LD SP,HL; end restores SP, enables IRQ, returns.
    header = bytes.fromhex("F3 ED 73 2F E9 F9")
    footer = bytes.fromhex("ED 7B 2F E9 FB C9")
    for entry, end in ((0x61CE, 0x6294), (0x629A, 0x6360)):
        if master[entry:entry+6] != header:
            raise ValueError(f"Unexpected transfer prologue at {entry:04X}")
        if master[end:end+6] != footer:
            raise ValueError(f"Unexpected transfer epilogue at {end:04X}")


def validate_six_car_loop(master: bytes) -> list[dict]:
    """Original PC $5EA1..$5F13 loads, processes and saves six slots."""
    records = []
    for i in range(SLOTS):
        offset = 0x5EA1 + i*19
        start, end = 0xE000+i*SLOT_STRIDE, 0xE060+i*SLOT_STRIDE
        ix = 0xE080+i*SLOT_STRIDE
        expected = bytes([
            0x21, start & 255, start >> 8,
            0xCD, 0xCE, 0x61,
            0xDD, 0x21, ix & 255, ix >> 8,
            0xCD, 0x1E, 0x60,
            0x21, end & 255, end >> 8,
            0xCD, 0x9A, 0x62,
        ])
        if master[offset:offset+len(expected)] != expected:
            raise ValueError(f"Car {i} load/processor/save sequence mismatch at {offset:04X}")
        records.append({
            "car_slot": i,
            "slot_address": f"{start:04X}",
            "snapshot_bytes": WORDS*2,
            "IX_base": f"{ix:04X}",
            "snapshot_end_stack_pointer": f"{end:04X}",
            "original_loop_pc": f"{offset:04X}",
            "processing_call": "601E",
        })
    return records


def candidate_calls(master: bytes, target: int) -> list[int]:
    signature = bytes([0xCD, target & 255, target >> 8])
    return [pc for pc in range(0x2000, 0xA000-2) if master[pc:pc+3] == signature]


def inspect(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != EXPECTED_MASTER:
        raise ValueError("Original 1991 arcade master region required (private)")
    validate_routine_wrappers(master)
    forward = parse_block(master, LOAD_BODY, True)
    reverse = parse_block(master, SAVE_BODY, False)
    if reverse != list(reversed(forward)):
        raise AssertionError("Original state word transfer ordering does not roundtrip")
    records = validate_six_car_loop(master)
    loads = candidate_calls(master, 0x61CE)
    saves = candidate_calls(master, 0x629A)
    return {
        "original": "1991 Indy Heat arcade, Z80 master bank0",
        "load_routine": "61CE..6299",
        "save_routine": "629A..6365",
        "scratch_ram_first_word": f"{SCRATCH_FIRST:04X}",
        "scratch_ram_last_word": f"{SCRATCH_LAST:04X}",
        "working_state_bytes_per_slot": WORDS*2,
        "working_state_words_per_slot": WORDS,
        "independent_slots": records,
        "main_six_slot_pass": "5EA1..5F12",
        "static_load_calls_found": len(loads),
        "static_save_calls_found": len(saves),
        "verified_call_locations_load": [f"{a:04X}" for a in loads],
        "verified_call_locations_save": [f"{a:04X}" for a in saves],
        "known_other_passes": [
            "2D87..2E0B uses each slot's +0x94 field with CALL 18C0",
            "2E0E..2E92 uses each slot's +0x96 field with CALL 18C0",
        ],
        "unknown": [
            "sixth slot's precise gameplay purpose",
            "semantics of all 48 fields",
            "whole-frame scheduling/timing and collision consumers",
        ],
        "status": "Exact car-state stack serializer verified statically; whole game still unresolved",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/car_state_serialization.json"))
    args = parser.parse_args()
    report = inspect(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
