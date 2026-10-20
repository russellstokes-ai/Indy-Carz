#!/usr/bin/env python3
"""Recover original arcade second-phase per-car status dispatch.

Inspects the PRIVATE checksum-verified MAME-rotated master Z80 ROM.
This extracts instruction-aligned handler addresses and event branching;
it does not identify the gameplay semantics of individual handlers or
create Godot gameplay. No original ROM or disassembly is shipped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MASTER_HASH = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STATUS_START = 0x3006
STATUS_END = 0x3045
SPATIAL_BRANCH_SIGNATURES = {
    0x2F3D: "3a 7d e6 b7 28 06",
    0x2F43: "cd 3a a6 c3 e4 2f",
    0x2F49: "cd 76 76 cd 3a a6 cd b4 7a",
    0x2F52: "fe 01 da 5c 2f ca e9 2f 18 72",
    0x2F5C: "3a 6c e7 fe 18 da de 2f",
}


def require_bytes(rom: bytes, pc: int, hex_bytes: str) -> None:
    target = bytes.fromhex(hex_bytes)
    if rom[pc:pc + len(target)] != target:
        raise ValueError(f"Original Z80 instruction mismatch at {pc:04X}")


def parse_postevent_handlers(rom: bytes) -> list[dict]:
    """Decode nine sequential BIT n,(IX+d) / CALL NZ,target pairs."""
    pc = STATUS_START
    result = []
    while pc < STATUS_END:
        if rom[pc:pc + 2] != bytes.fromhex("ddcb"):
            raise ValueError(f"Indexed BIT prefix missing at {pc:04X}")
        offset, opcode = rom[pc + 2], rom[pc + 3]
        if opcode & 0xC7 != 0x46:
            raise ValueError(f"Not a Z80 indexed BIT instruction at {pc:04X}")
        if rom[pc + 4] != 0xC4:
            raise ValueError(f"Not an original CALL NZ at {pc + 4:04X}")
        target = int.from_bytes(rom[pc + 5:pc + 7], "little")
        if not 0x2000 <= target < 0xA000:
            raise ValueError(f"Unexpected original callback target {target:04X}")
        result.append({
            "instruction_pc": f"{pc:04X}",
            "state_ix_offset": f"{offset:02X}",
            "state_bit": (opcode >> 3) & 7,
            "condition": "BIT n,(IX+d); CALL NZ,target",
            "target_pc": f"{target:04X}",
            "gameplay_semantics": "NOT YET VERIFIED",
        })
        pc += 7
    if len(result) != 9 or pc != STATUS_END:
        raise ValueError("Nine original event handlers expected")
    require_bytes(rom, 0x3045, "dd 7e 34 e6 30 c4 3b 11")
    require_bytes(rom, 0x304D, "cd 9d 68")
    return result


def parse_spatial_branch(rom: bytes) -> dict:
    for pc, signature in SPATIAL_BRANCH_SIGNATURES.items():
        require_bytes(rom, pc, signature)
    return {
        "phase_gate": "RAM E67D != 0 bypasses course event check",
        "before_event_calls": ["7676", "A63A"],
        "course_event_call": "2F4F -> 7AB4",
        "result_0": "2F5C; read RAM E76C; compare with 0x18",
        "result_1": "2FE9",
        "result_2_or_higher": "2FCE",
        "meaning": "Original branches proven; pit/lap/collision attribution OPEN",
    }


def extract(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_HASH:
        raise ValueError("Checksum-verified original 1991 arcade master ROM required")
    return {
        "source": "Original 1991 Indy Heat arcade master Z80 bank0",
        "per_car_second_callback": "2F1E",
        "spatial_branch": parse_spatial_branch(master),
        "postevent_dispatch_pc": "3006..304C",
        "conditional_state_handlers": parse_postevent_handlers(master),
        "additional_handler": "IX+34 AND 0x30 -> CALL NZ 113B",
        "unconditional_tail_call": "304D -> 689D",
        "confidence": "Instruction-aligned original static flow; runtime behaviour OPEN",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path, help="Private master.mame_runtime.bin")
    p.add_argument("--out", type=Path,
                   default=Path("local/engine-extraction/second_phase_dispatch.json"))
    args = p.parse_args()
    result = extract(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Original event handlers verified: {len(result['conditional_state_handlers'])}")
    print(f"Private report: {args.out}")


if __name__ == "__main__":
    main()
