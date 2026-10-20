#!/usr/bin/env python3
"""Recover original 1991 Indy Heat Z80 callback targets and continuation logic.

Static ORIGINAL executable signatures from a user-supplied private ROM image.
No game binaries, original assets, or copied disassembly go into this repo.
Not a gameplay port; real runtime execution and switchable bank contexts
still require debugger-enabled MAME.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_SHA256 = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
BANK0 = 0x02000
BANK3 = 0x28000
PHASES = (("first", 0x2D87, 0x94, 0x2EAF),
          ("second", 0x2E0E, 0x96, 0x2F1E))


def mapped(master: bytes, offset: int) -> bytes:
    if len(master) != 0x90000 or offset + 0x8000 > len(master):
        raise ValueError("Expected full 1991 MAME-rotated arcade master Z80 memory")
    result = bytearray(master[:0xA000])
    result[0x2000:0xA000] = master[offset:offset+0x8000]
    return bytes(result)


def check(image: bytes, addr: int, hex_bytes: str) -> None:
    expected = bytes.fromhex(hex_bytes)
    if image[addr:addr + len(expected)] != expected:
        raise ValueError(f"Original arcade instruction mismatch at {addr:04X}")


def inspect_initializers(b0: bytes) -> dict:
    # Master bank0 code in the shared initialisation routine at 0x601E.
    check(b0, 0x611D, "21 af 2e dd 74 15 dd 75 14")
    check(b0, 0x6126, "21 1e 2f dd 74 17 dd 75 16")
    return {"initialisation_routine": "601E",
            "first_default_callback": "2EAF",
            "second_default_callback": "2F1E",
            "first_slot_pointer_offsets": ["94", "95"],
            "second_slot_pointer_offsets": ["96", "97"]}


def inspect_passes(b0: bytes) -> list[dict]:
    check(b0, 0x18C0, "e9")  # JP (HL)
    check(b0, 0x2D65, "3a 7d e6 b7 28 1c fe 02 ca 0e 2e")
    result = []
    for name, base_pc, offset, default in PHASES:
        for slot in range(6):
            base = 0xE000 + 0x100*slot
            ix = base + 0x80
            ptr = base + offset
            pc = base_pc + slot*22
            # LD HL,slot; CALL 61CE; LD IX,slot+80; LD HL,(slot+offset);
            # CALL 18C0; LD HL,slot+60; CALL 629A.
            check(b0, pc, f"21 {base&255:02x} {base>>8:02x} cd ce 61 "
                  f"dd 21 {ix&255:02x} {ix>>8:02x} "
                  f"2a {ptr&255:02x} {ptr>>8:02x} cd c0 18 "
                  f"21 {(base+0x60)&255:02x} {(base+0x60)>>8:02x} cd 9a 62")
            result.append({"phase": name, "slot": slot,
                           "original_dispatch_pc": f"{pc:04X}",
                           "pointer_ram": f"{ptr:04X}",
                           "default_target": f"{default:04X}"})
    return result


def inspect_continuations(b3: bytes) -> dict:
    # POP HL ; LD (IX+15),H ; LD (IX+14),L ; RET.
    # POP consumes the return address from CALL 77BE. RET then unwinds one
    # more level while saving continuation PC as the next first callback.
    check(b3, 0x77BE, "e1 dd 74 15 dd 75 14 c9")
    replacement = []
    for pc in (0x756B, 0x7594):
        check(b3, pc, "dd 36 15 74 dd 36 14 c9")
        replacement.append({"bank": 3, "at_pc": f"{pc:04X}",
                            "forced_callback_target": "74C9"})
    signature = bytes.fromhex("cd be 77")
    candidates = []
    current = 0x2000
    while True:
        pc = b3.find(signature, current, 0xA000)
        if pc < 0:
            break
        candidates.append({"bank": 3, "call_pc": f"{pc:04X}",
                           "saved_continuation_pc": f"{pc+3:04X}"})
        current = pc+1
    if len(candidates) != 34:
        raise ValueError("Unexpected number of static continuation signatures")
    return {"original_yield_helper": "77BE in bank 3",
            "semantics": "POP saved CALL return PC; store into slot+94; RET to enclosing caller",
            "signature_matched_yield_sites": candidates,
            "site_count": len(candidates),
            "explicit_callback_redirects": replacement,
            "execution_coverage": "NOT VERIFIED; signatures are static candidates"}


def scan_pointer_writes(master: bytes) -> list[dict]:
    bank_offsets = (0x02000,0x18000,0x20000,0x28000,0x30000,0x38000,
                    0x40000,0x48000,0x50000,0x58000,0x60000,0x68000,
                    0x70000,0x78000,0x80000,0x88000)
    results = []
    for bank, region_offset in enumerate(bank_offsets):
        img = mapped(master, region_offset)
        for pc in range(0x2000, 0x9FFC):
            if (img[pc] == 0xDD and img[pc+1] in (0x36,0x70,0x71,0x72,
                                                  0x73,0x74,0x75,0x77)
                    and img[pc+2] in (0x14,0x15,0x16,0x17)):
                results.append({"bank": bank, "candidate_pc": f"{pc:04X}",
                                "ix_offset": f"{img[pc+2]:02X}"})
    return results


def inspect(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Original verified Indy Heat 1991 MAME-rotated master required")
    b0, b3 = mapped(master, BANK0), mapped(master, BANK3)
    return {
        "set": "indyheat (1991 arcade)",
        "status": "callback initialisation, static flow and coroutine mechanism verified",
        "callback_initialisation": inspect_initializers(b0),
        "two_six_slot_dispatch_passes": inspect_passes(b0),
        "first_pass_gate": "E67D zero enters first phase; other values conditionally skip/decrement",
        "three_player_bank3_callback_reads": [
            f"{pc:04X}" for pc in (0x2A8B,0x2A98,0x6253,0x6260,0x626D,
                                  0x6BE0,0x6BF0,0x6C00)
        ],
        "continuations": inspect_continuations(b3),
        "direct_ix_callback_write_candidates": scan_pointer_writes(master),
        "limitations": [
            "34 CALL-site signatures not all proven reachable",
            "Indirect pointer writes and runtime bank changes can add call targets",
            "Actual callback phase timing and bank3 execution require live MAME traces",
            "No complete motion, pit, track collision or opponent logic is implied",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path, help="PRIVATE master.mame_runtime.bin")
    parser.add_argument("--out", type=Path,
                        default=Path("local/recovery/arcade_callbacks.json"))
    args = parser.parse_args()
    info = inspect(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(info, indent=2) + "\n")
    print("Two default callbacks:", info["callback_initialisation"]["first_default_callback"],
          info["callback_initialisation"]["second_default_callback"])
    print("Verified call dispatches:", len(info["two_six_slot_dispatch_passes"]))
    print("Candidate yield sites:", info["continuations"]["site_count"])
    print("No complete game engine or live runtime parity claimed.")


if __name__ == "__main__":
    main()
