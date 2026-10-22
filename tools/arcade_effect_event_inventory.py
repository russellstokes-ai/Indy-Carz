#!/usr/bin/env python3
"""Classify original Indy Heat nine events against the original effect pool.

This is static ROM-backed evidence. Eight handlers reach the original
priority allocator ($8659); the ninth accesses a previously allocated E8xx
record. Also identifies effects updater and audio command hardware path.
Does NOT establish each event's gameplay cause or complete animation/audio.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from arcade_second_phase_dispatch import parse_postevent_handlers

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
ALLOCATOR_SHA = "ccd8beabde765d10314d9859b94562ed7d759988c45745a44ffb9fd284ae66da"
UPDATE_SHA = "2e6fda2e6cc01fa3f33e0ae0c6da8e6d9f4545470a45a857840708afa6607a9e"
SOUND_GATE_SHA = "76d0877a71b3afe76de1ce2b828f99192316311bbaa5f6356904f3fbee6963ce"

# Original direct calls: two of these status entries share a downstream call.
EFFECT_PATHS = {
    0x6C1C: [0x6C2A],
    0x6DFA: [0x6E12],  # jumps to the shared 6E0F path
    0x6E06: [0x6E12],  # falls into that same 6E0F path
    0x6EA6: [0x6EB1],
    0x6A18: [0x6A1E, 0x6A2D],
    0x6A3A: [0x6A46],
    0x6B61: [0x6B8F],
    0x6BA2: [],         # existing effect pointer from IX+30
    0x6A51: [0x6A69],
}
SOUND_PATHS = {
    0x6C1C: [(0x6C4D, "0BA6")],
    0x6EA6: [(0x6EAC, "0B98")],
    0x6A51: [(0x6A5C, "0BA6")],
}

def insist(master: bytes, pc: int, opcode: str) -> None:
    b = bytes.fromhex(opcode)
    if master[pc:pc+len(b)] != b:
        raise ValueError(f"Original opcode mismatch at master {pc:04X}")

def inventory(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Verified original 1991 Indy Heat arcade master is required")
    for begin, end, digest in (
        (0x8659, 0x8694, ALLOCATOR_SHA),
        (0x8694, 0x86F5, UPDATE_SHA),
        (0x0B98, 0x0BC9, SOUND_GATE_SHA),
    ):
        if hashlib.sha256(master[begin:end]).hexdigest() != digest:
            raise ValueError(f"Original effect/sound stage differs at {begin:04X}")
    # The allocator scans E800, steps 0x10 through 16 records, and rejects
    # a new effect unless its requested B priority exceeds the lowest one.
    insist(master, 0x8659, "21 00 E8 0E 10")
    insist(master, 0x8689, "F6 FF C9")
    # Updater dispatch: A=status, status<2 frees, status==2 fixed render,
    # status>=3 uses a per-slot callback via CALL 18C0 (JP HL).
    insist(master, 0x8694, "21 00 E8 7E FE 02 30 11")
    insist(master, 0x86AD, "20 28")
    insist(master, 0x86E7, "CD C0 18")
    insist(master, 0x8700, "FD 36 00 00")
    # Two incoming event paths share one allocator call site.
    insist(master, 0x6E03, "C3 0F 6E")
    insist(master, 0x6E0F, "F5")
    # One status handler reuses a previously stored E8xx pointer.
    insist(master, 0x6BA2, "26 E8 DD 6E 30 E5 FD E1")
    # Original bank-switches into sound command dispatch and returns.
    insist(master, 0x0BBC, "D3 F4 CD 00 20")
    insist(master, 0x0BC2, "32 08 E6 D3 F4")
    # Sound command is written via Ataxx-era 80186 high/low ports.
    b3 = 0x28000
    def bank3(cpu_pc: int, opcode: str) -> None:
        raw = bytes.fromhex(opcode)
        begin = b3 + cpu_pc - 0x2000
        if master[begin:begin+len(raw)] != raw:
            raise ValueError(f"Original sound gateway changed at bank3 {cpu_pc:04X}")
    bank3(0x2000, "F5 D5 E5 78")
    bank3(0x20B7, "79 D3 05")
    bank3(0x20BF, "E6 7F B3 D3 06")

    original = parse_postevent_handlers(master)
    observed = {int(r["target_pc"],16) for r in original}
    if observed != set(EFFECT_PATHS):
        raise ValueError("Nine original event handler targets no longer match")
    for handlers in EFFECT_PATHS.values():
        for pc in handlers:
            insist(master, pc, "CD 59 86")
    for handler, calls in SOUND_PATHS.items():
        for pc, dest in calls:
            insist(master, pc, "CD " + dest[2:] + " " + dest[:2])
    # Note that indirect/nested sound calls also exist, not exhaustively traced.
    rows = []
    for r in original:
        target = int(r["target_pc"], 16)
        rows.append({
            "condition_pc": r["instruction_pc"],
            "field": r["state_ix_offset"], "bit": r["state_bit"],
            "handler_pc": r["target_pc"],
            "original_allocator_calls": [f"{pc:04X}" for pc in EFFECT_PATHS[target]],
            "effect_behavior": "allocates or replaces" if EFFECT_PATHS[target] else "updates existing record",
            "direct_audio_command_calls": [
                {"cpu_pc": f"{pc:04X}", "destination_pc": dest}
                for pc, dest in SOUND_PATHS.get(target, [])
            ],
            "gameplay_cause": "UNVERIFIED",
        })
    return {
        "set": "original 1991 Indy Heat arcade",
        "events": rows,
        "allocating_handlers": sum(bool(x) for x in EFFECT_PATHS.values()),
        "existing_record_handlers": 1,
        "distinct_allocator_call_sites": len({n for x in EFFECT_PATHS.values() for n in x}),
        "pool": {
            "master_allocator": "8659..8693",
            "master_update_loop": "8694..86F4",
            "effect_record_region": "E800..E8FF", "effect_record_size": 16,
            "number_of_records": 16,
            "status_byte": "+00", "priority_and_tick_byte": "+01",
            "animation_callback_address": "+02/+03 for status>=3",
            "expired_record_clear_routine": "8700",
            "update_branch_types": {
                "status<2": "cleanup and mark empty",
                "status=2": "fixed payload/output command path",
                "status>=3": "per-effect callback via 18C0",
            },
        },
        "audio": {
            "master_wrapper": "0BA6",
            "conditional_wrapper": "0B98",
            "selected_master_bank": "03 via port F4",
            "bank3_dispatch": "2000",
            "bank3_80186_ports": ["05 command_hi", "06 command_lo"],
            "scope": "audio command transport verified; samples and event meanings unverified",
        },
        "limitations": [
            "Instruction signatures/static call graph are not original runtime traces",
            "Handlers may also change car status, sound or gameplay state",
            "Effect type/payload formats and the D958 video command still need tracing",
            "No original handling, collision or race engine parity is implied",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path)
    p.add_argument("--out", type=Path,
                   default=Path("local/engine-extraction/effect_event_inventory.json"))
    args = p.parse_args()
    report = inventory(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Original event handlers:", len(report["events"]))
    print("Allocating handlers:", report["allocating_handlers"])
    print("Existing-effect update handlers:", report["existing_record_handlers"])
    print("Private report:", args.out)


if __name__ == "__main__":
    main()
