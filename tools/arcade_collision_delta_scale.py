#!/usr/bin/env python3
"""Recover Indy Heat original two-axis collision separation quantisation.

Original fixed master Z80 $B3C2..$B3DB receives signed 16-bit pair
differences in DE and HL, returns rounded signed /8 low bytes in B and C.
Requires the private original ROM for opcode-level parity. Does NOT
reconstruct the rest of narrow-phase contact physics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
START, STOP = 0xB3C2, 0xB3DC
INSTRUCTION_SIGNATURE = bytes.fromhex(
    "cb 2a 7b 1f cb 2a 1f cb 2a 1f ce 00 47 "
    "cb 2c 7d 1f cb 2c 1f cb 2c 1f ce 00 4f"
)


def signed16(value: int) -> int:
    if not 0 <= value <= 65535:
        raise ValueError("Collision separation must be an unsigned 16-bit word")
    return value - 65536 if value >= 32768 else value


def independent_axis(value: int) -> int:
    """Z80 arithmetic signed rounding; output is wrapped to 8 bits."""
    return ((signed16(value) + 4) >> 3) & 255


def original_z80_stage(master: bytes, delta_de: int, delta_hl: int) -> tuple[int, int]:
    """Bounded original instruction interpreter, NO guessed operations."""
    if len(master) != 0x90000 or master[START:STOP] != INSTRUCTION_SIGNATURE:
        raise ValueError("Original arcade collision separation instructions unavailable")
    signed16(delta_de)
    signed16(delta_hl)
    d, e = delta_de >> 8, delta_de & 255
    h, l = delta_hl >> 8, delta_hl & 255
    a = b = c = carry = 0
    pc = START
    for _ in range(24):
        opcode = master[pc]
        if opcode == 0xCB:
            extended = master[pc + 1]
            if extended == 0x2A:  # SRA D
                carry = d & 1
                d = (d >> 1) | (d & 128)
            elif extended == 0x2C:  # SRA H
                carry = h & 1
                h = (h >> 1) | (h & 128)
            else:
                raise ValueError(f"Unexpected Z80 shift at {pc:04X}")
            pc += 2
        elif opcode == 0x7B:  # LD A,E
            a = e
            pc += 1
        elif opcode == 0x7D:  # LD A,L
            a = l
            pc += 1
        elif opcode == 0x1F:  # RRA
            old = a
            a = (carry << 7) | (a >> 1)
            carry = old & 1
            pc += 1
        elif opcode == 0xCE and master[pc + 1] == 0:  # ADC A,0
            result = a + carry
            a, carry = result & 255, int(result > 255)
            pc += 2
        elif opcode == 0x47:  # LD B,A
            b = a
            pc += 1
        elif opcode == 0x4F:  # LD C,A
            c = a
            pc += 1
        else:
            raise ValueError(f"Unexpected collision opcode {opcode:02X} at {pc:04X}")
        if pc == STOP:
            return b, c
    raise ValueError("Original collision rounding stage exceeded instruction budget")


def verify(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Checksum-verified original 1991 arcade master ROM is required")
    if master[START:STOP] != INSTRUCTION_SIGNATURE:
        raise ValueError("Original arcade collision scaling instruction signature changed")
    # Every possible input to each axis, same input on both axes: 131,072
    # independently verified original byte outputs. No cross-axis coupling
    # occurs in this bounded instruction sequence.
    for word in range(65536):
        observed = original_z80_stage(master, word, word)
        expected = independent_axis(word)
        if observed != (expected, expected):
            raise AssertionError(f"Original collision stage mismatch at {word:04X}")
    return {
        "original_cpu": "Indy Heat 1991 arcade master Z80 fixed ROM",
        "start_pc": f"{START:04X}",
        "end_pc_exclusive": f"{STOP:04X}",
        "distinct_16bit_axis_inputs": 65536,
        "original_opcode_executions": 65536,
        "byte_outputs_compared": 131072,
        "mismatches": 0,
        "formula": "uint8(floor((signed16(input_word)+4)/8))",
        "original_registers": "DE->B, HL->C",
        "scope": "Signed relative-separation scaling only; detailed contact thresholds and impulse response OPEN",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("master", type=Path, help="PRIVATE MAME-rotated master region")
    ap.add_argument("--out", type=Path,
                    default=Path("local/recovery/collision_separation_scale.json"))
    args = ap.parse_args()
    results = verify(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print("Checked", results["byte_outputs_compared"],
          "original arcade collision-axis outputs; mismatches:", results["mismatches"])


if __name__ == "__main__":
    main()
