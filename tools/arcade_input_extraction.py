#!/usr/bin/env python3
"""Extract Indy Heat arcade human-input steering data from private Z80 ROM images.

This analyses verified 1991 arcade program memory; it is NOT a physics
implementation and distributes neither ROMs nor original disassembly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MASTER_SHA256 = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA256 = "1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
WHEEL_TABLE_PC = 0x0DCD
WHEEL_TABLE_SIZE = 32
CAR_BASES = tuple(0xE080 + 0x100 * i for i in range(5))

# CPU addresses in currently fixed/bank-zero mapped master Z80 code.
# Only tiny instruction prefixes are used for sanity checking.
INPUT_SITES = {
    "p1_wheel": (0x0C5F, "db00"),
    "p2_wheel": (0x0C7F, "db01"),
    "p3_wheel": (0x0C9F, "db02"),
    "p1_button": (0x0C4E, "db0d"),
    "p2_button": (0x0C6E, "db0e"),
    "p3_button": (0x0C8E, "db0f"),
    "pedal_channel_select": (0x679E, "d30b"),
    "pedal_sample": (0x67B5, "db09"),
    "steering_transform": (0x0D6A, "95e61f"),
    "steering_table_pointer": (0x0D6D, "21cd0d"),
    "human_ai_dispatch": (0x6793, "ddcb3146"),
    "ai_control_entry": (0x2263, "ddcb334e"),
    "pedal_output": (0x67D2, "dd7757"),
}


def check_image(data: bytes, length: int, digest: str, label: str) -> None:
    if len(data) != length:
        raise ValueError(f"{label} has wrong length (expected {length})")
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"{label} SHA256 differs from verified original arcade region")


def wheel_response(encoded: int, previous: int, table: bytes) -> int:
    """ROM 0x0D6A: unsigned five-bit dial difference → signed shaped sample.

    MAME dial encoder produces a cumulative 5-bit counter with a separate
    bit7 direction. Negative if bit7 clear, positive if bit7 set.
    """
    if len(table) != WHEEL_TABLE_SIZE:
        raise ValueError("Steering table must contain 32 samples")
    if not (0 <= encoded <= 255 and 0 <= previous <= 255):
        raise ValueError("Wheel values must be bytes")
    index = ((encoded & 0x1F) - (previous & 0x1F)) & 0x1F
    magnitude = table[index]
    signed = magnitude if (encoded & 0x80) else (-magnitude & 0xFF)
    return signed - 256 if signed >= 128 else signed


def pedal_output(lookup_byte: int, calibration: int) -> int:
    """Directly reproduce original post-XROM Z80 ADD/carry/saturation sequence.

    Important: values of (IX+58) and (IX+59) still need runtime recovery.
    This is NOT a complete pedal or acceleration model.
    """
    if not (0 <= lookup_byte < 256 and 0 <= calibration < 256):
        raise ValueError("Pedal input/calibration must be bytes")
    total = lookup_byte + calibration
    if total < 256:
        return 0
    doubled = (total & 0xFF) << 1
    if doubled > 255 or doubled & 0x80:
        return 0x7E
    return doubled


def pedal_sample(xrom: bytes, analog: int, base_offset: int, calibration: int) -> int:
    """ROM 0x67B5: index XROM slot1 by (analog << 8) | (IX+58)."""
    if len(xrom) != 0x40000:
        raise ValueError("Wrong XROM image length")
    if any(v < 0 or v > 255 for v in (analog, base_offset, calibration)):
        raise ValueError("Pedal address parameters must be bytes")
    idx = 0x10000 | (analog << 8) | base_offset
    return pedal_output(xrom[idx], calibration)


def extract(master: bytes, xrom: bytes) -> dict:
    check_image(master, 0x90000, MASTER_SHA256, "master")
    check_image(xrom, 0x40000, XROM_SHA256, "xrom")
    for name, (pc, opcode) in INPUT_SITES.items():
        signature = bytes.fromhex(opcode)
        if master[pc:pc + len(signature)] != signature:
            raise ValueError(f"{name}: unexpected master instruction at PC 0x{pc:04X}")
    table = master[WHEEL_TABLE_PC:WHEEL_TABLE_PC + WHEEL_TABLE_SIZE]
    return {
        "source": "indyheat 1991 arcade ROM, MAME-rotated Z80 master + XROM",
        "status": "static input logic extracted; complete physics not recovered",
        "master_instruction_sites": {
            name: f"0x{pc:04X}" for name, (pc, _) in INPUT_SITES.items()
        },
        "five_car_state_bases": [f"0x{p:04X}" for p in CAR_BASES],
        "wheel": {
            "count": WHEEL_TABLE_SIZE,
            "source_cpu_address": f"0x{WHEEL_TABLE_PC:04X}",
            "shaping_lookup_0_to_31": list(table),
            "index": "(encoded_counter - previous_counter) & 31",
            "direction": "bit 7 set -> positive; clear -> negative",
            "destination": "IX+0x7A and conditionally IX+0x79",
        },
        "accelerator": {
            "hardware": "OUT 0x0B channel selector; IN 0x09 reads sampled pedal",
            "xrom_index": "0x10000 | (raw_pedal << 8) | (IX+0x58)",
            "calibration": "IX+0x59 (unknown per-car runtime value)",
            "destination": "IX+0x57",
            "confidence": "static formula verified, actual car configuration unknown",
        },
        "computer_input": {
            "entry": "master CPU 0x2263",
            "selection": "first three driver slots conditionally dispatch human or AI",
            "full_ai_algorithm": "NOT YET EXTRACTED",
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--master", type=Path, required=True)
    p.add_argument("--xrom", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("local/engine-extraction/input_map.json"))
    a = p.parse_args()
    info = extract(a.master.read_bytes(), a.xrom.read_bytes())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(INPUT_SITES)} CPU input sites and {WHEEL_TABLE_SIZE} lookup entries")
    print(f"Private report: {a.out}")
    print("Full vehicle physics/AI remains unverified.")


if __name__ == "__main__":
    main()
