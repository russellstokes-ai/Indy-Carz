#!/usr/bin/env python3
"""Validate original Indy Heat arcade AI pedal output at master $22A2-$22B1.

Original instruction sequence (private arcade ROM) maps per-car state fields
to AI accelerator input. This does NOT reconstruct driving decisions, path
following or the rest of the AI and must not be used as substitute physics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

MASTER_SHA256 = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
START, STOP = 0x22A2, 0x22B2
SIGNATURE = bytes.fromhex("dd7e77cb3f4fdd96bb4779e67edd7757")


def original_ai_input(master: bytes, car_77: int, car_negative_45: int) -> tuple[int, int]:
    """Boundedly execute original Z80 opcodes until first write to IX+$57.

    Returns (AI input byte IX+$57, B scratch register). Exits on unknown opcode.
    """
    if len(master) != 0x90000 or master[START:STOP] != SIGNATURE:
        raise ValueError("Original arcade AI input routine not found at master $22A2")
    if any(not 0 <= v <= 255 for v in (car_77, car_negative_45)):
        raise ValueError("Car state field must be an unsigned byte")
    pc, a, b, c = START, 0, 0, 0
    for _ in range(16):
        op = master[pc]
        if op == 0xDD:
            second, displacement = master[pc + 1:pc + 3]
            if second == 0x7E and displacement == 0x77:  # LD A,(IX+77)
                a = car_77
            elif second == 0x96 and displacement == 0xBB:  # SUB (IX-45h)
                a = (a - car_negative_45) & 0xFF
            elif second == 0x77 and displacement == 0x57:  # LD (IX+57),A
                if pc + 3 != STOP:
                    raise ValueError("Original arcade AI output boundary changed")
                return a, b
            else:
                raise ValueError(f"Unexpected original indexed instruction at {pc:04X}")
            pc += 3
        elif op == 0xCB and master[pc + 1] == 0x3F:  # SRL A
            a >>= 1
            pc += 2
        elif op == 0x4F:  # LD C,A
            c = a
            pc += 1
        elif op == 0x47:  # LD B,A
            b = a
            pc += 1
        elif op == 0x79:  # LD A,C
            a = c
            pc += 1
        elif op == 0xE6 and master[pc + 1] == 0x7E:  # AND 7Eh
            a &= 0x7E
            pc += 2
        else:
            raise ValueError(f"Unexpected original opcode at {pc:04X}")
    raise ValueError("AI control routine exceeded expected opcode budget")


def independent_ai_input(car_77: int, car_negative_45: int) -> tuple[int, int]:
    half = car_77 >> 1
    return half & 0x7E, (half - car_negative_45) & 0xFF


def verify(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA256:
        raise ValueError("Privately reconstructed original Indy Heat master Z80 required")
    checked = 0
    for car_77 in range(256):
        for car_negative_45 in range(256):
            expected = independent_ai_input(car_77, car_negative_45)
            actual = original_ai_input(master, car_77, car_negative_45)
            if actual != expected:
                raise AssertionError(
                    f"AI stage mismatch at state {car_77:02X}/{car_negative_45:02X}"
                )
            checked += 1
    return {
        "source": "1991 arcade Indy Heat master Z80 bank 0 $22A2..$22B1",
        "instruction_cases": checked,
        "mismatches": 0,
        "ai_output_ix_57": "(car[IX+0x77] >> 1) & 0x7E",
        "next_stage_register_b": "((car[IX+0x77] >> 1) - car[IX-0x45]) & 0xFF",
        "scope": "One proven AI input transform only; opponent AI, target speed and physics are NOT recovered",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/ai_input_stage.json"))
    args = parser.parse_args()
    report = verify(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
