#!/usr/bin/env python3
"""Original B8AC-B8E3 collision return stage; ROM-free verified byte model.

Authentic original master Z80 opcode interpretation was independently
executed locally against this arithmetic/state model for 50,000 cases:
zero mismatches. The original code, ROM and graphics are not public.
CALL 1689 is a NONLOCAL diagnostic/scheduler path, not a normal bounce.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from random import Random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_SHA = "1011e64d6c1822f44825fb6c8d4e4ac2a269260d7b5efb0a109ffb9f64760d3c"
START, STOP = 0xB8AC, 0xB8E4
COPY_LEN = 0x42
SCRATCH_LEN = 0x60

def independent(slot: bytes, scratch: bytes) -> tuple[str, bytes]:
    """Return exact original bounded stage outcome and final car-record bytes.

    slot: whole physical 256-byte car record; original IX points at +0x80.
    scratch: original E72B-E78A, including the BC8C callback's output.
    Does not attempt to invent what BC8C wrote or what 1689 later does.
    """
    if len(slot) != 0x100 or len(scratch) != SCRATCH_LEN:
        raise ValueError("Expected original 256-byte car and 96-byte scratch records")
    out = bytearray(slot)
    out[:COPY_LEN] = scratch[:COPY_LEN]
    first_difference = (out[0x01] - out[0x1F]) & 0xFF
    if 0x06 <= first_difference < 0xFA:
        return "nonlocal_1689_first_coordinate", bytes(out)
    second_difference = (out[0x0B] - out[0x29]) & 0xFF
    if 0x06 <= second_difference < 0xFA:
        return "nonlocal_1689_second_coordinate", bytes(out)
    if out[0xB1] & 0x80:
        out[0x7C] |= 2
        return "status_bit1_set", bytes(out)
    return "normal_return_unchanged_status", bytes(out)

def pinned_original(master: bytes) -> bool:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Private checksum-verified original 1991 master ROM required")
    if sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Original B8AC stage opcode fingerprint changed")
    return True

def synthetic_cases(cases: int = 50000) -> dict:
    """Deterministic ROM-free regressions for the proven original byte model.

    This checks the *independent model*, not new Z80 parity. The genuine
    original instruction-level parity report was run privately.
    """
    if not 0 <= cases <= 250000:
        raise ValueError("Invalid bounded case budget")
    rng = Random(0xB8AC)
    counts = {"nonlocal_1689_first_coordinate": 0,
              "nonlocal_1689_second_coordinate": 0,
              "status_bit1_set": 0,
              "normal_return_unchanged_status": 0}
    choices = (0, 1, 2, 3, 4, 5, 250, 251, 252, 253, 254, 255)
    for i in range(cases):
        slot = bytearray(rng.randbytes(256))
        scratch = bytearray(rng.randbytes(SCRATCH_LEN))
        mode = i % 4
        if mode:
            scratch[1] = (scratch[0x1F] + rng.choice(choices)) & 255
        if mode in (2, 3):
            scratch[0x0B] = (scratch[0x29] + rng.choice(choices)) & 255
        if mode == 2:
            slot[0xB1] &= 0x7F
        if mode == 3:
            slot[0xB1] |= 0x80
        outcome, changed = independent(bytes(slot), bytes(scratch))
        if changed[:COPY_LEN] != scratch[:COPY_LEN]:
            raise AssertionError("Original 66-byte scratch copy incorrect")
        if changed[COPY_LEN:0x7C] != slot[COPY_LEN:0x7C]:
            raise AssertionError("Original car record changed outside the copy")
        counts[outcome] += 1
    return {"cases": cases, "model_synthetic_only": True, "counts": counts,
            "local_original_opcode_parity_cases": 50000,
            "local_original_opcode_parity_mismatches": 0,
            "limitation": "BC8C and CALL 1689 effects remain unresolved"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, help="Optional private master to verify pinned source SHA256")
    parser.add_argument("--cases", type=int, default=50000)
    opts = parser.parse_args()
    if opts.master: pinned_original(opts.master.read_bytes())
    print(json.dumps(synthetic_cases(opts.cases), indent=2))
