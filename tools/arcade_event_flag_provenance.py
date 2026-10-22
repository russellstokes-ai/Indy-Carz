#!/usr/bin/env python3
"""Trace *candidate* original event-flag producers back into banked Z80 code.

For each verified original nine event-consumer flags, identify SET sites
with correct master Z80 ROM bank mapping. Source instructions are backed by
exact arcade ROM hash, but not yet confirmed executed under all race states.
No gameplay meaning, collision interpretation or full decompilation inferred.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from arcade_second_phase_dispatch import parse_postevent_handlers

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
BANK_OFFSETS = (0x02000, 0x18000, 0x20000, 0x28000, 0x30000, 0x38000,
                0x40000, 0x48000, 0x50000, 0x58000, 0x60000, 0x68000,
                0x70000, 0x78000, 0x80000, 0x88000)
# Sites in decoded instruction-aligned original code. Not an exhaustive
# proof of all possible producers: direct register stores can set bits too.
KNOWN_SET_SITES = {
    (0x32,5): ((1,0x3B89), (1,0x454E), (1,0x5697)),
    (0x32,3): ((1,0x50F7),),
    (0x32,4): ((1,0x526A),),
    (0x31,5): ((0,0x2AB8),),
    (0x7E,2): ((0,0x5BC9),),
    (0x31,4): ((0,0x7083),),
    (0x32,6): ((1,0x3BE7),),
    (0x32,7): ((0,0x6B86),),
    (0x33,3): ((1,0x3736),),
}


def cpu_byte(master: bytes, bank: int, pc: int) -> int:
    if not 0 <= bank < len(BANK_OFFSETS) or not 0x2000 <= pc < 0xA000:
        raise ValueError("Z80 bank/PC outside arcade ROM window")
    return master[BANK_OFFSETS[bank] + pc - 0x2000]


def indexed_bit_opcode(master: bytes, bank: int, pc: int,
                       displacement: int, bit: int, set_bit: bool) -> bool:
    opcode = (0xC6 if set_bit else 0x86) + 8 * bit
    return bytes(cpu_byte(master, bank, pc + n) for n in range(4)) == bytes(
        (0xDD, 0xCB, displacement, opcode)
    )


def scan_flag_set_candidates(master: bytes, field: int, bit: int) -> list[dict]:
    signature = bytes((0xDD, 0xCB, field, 0xC6 + 8*bit))
    results = []
    for bank, offset in enumerate(BANK_OFFSETS):
        image = master[offset:offset + 0x8000]
        pos = 0
        while True:
            pos = image.find(signature, pos)
            if pos < 0:
                break
            results.append({"bank": bank, "cpu_pc": f"{0x2000 + pos:04X}",
                            "evidence": "raw exact opcode signature; execution not established"})
            pos += 1
    return results


def inspect(master: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Verified original Indy Heat master Z80 image required")
    consumers = parse_postevent_handlers(master)
    result = []
    for row in consumers:
        target = (int(row["state_ix_offset"],16), int(row["state_bit"]))
        expected = KNOWN_SET_SITES.get(target)
        if not expected:
            raise ValueError(f"Unexpected original event field: {target}")
        for bank, pc in expected:
            if not indexed_bit_opcode(master, bank, pc, *target, True):
                raise ValueError(f"Original producer SET opcode changed at bank {bank} PC {pc:04X}")
        candidates = scan_flag_set_candidates(master, *target)
        known = {(n["bank"], int(n["cpu_pc"], 16)) for n in candidates}
        if any(site not in known for site in expected):
            raise AssertionError("Known producer missing from raw candidate scan")
        result.append({
            "consumer_pc": row["instruction_pc"],
            "event_field_offset": row["state_ix_offset"],
            "event_bit": row["state_bit"],
            "handler_pc": row["target_pc"],
            "known_aligned_set_sites": [
                {"bank": bank, "pc": f"{pc:04X}"} for bank, pc in expected
            ],
            "raw_candidate_set_sites": candidates,
            "unknowns": "Other writers, reachability and actual gameplay meaning not established",
        })
    # Original routine writes same flag to IX and IY car-like records.
    if bytes(cpu_byte(master,1,0x375A+n) for n in range(4)) != bytes.fromhex("FD CB 33 DE"):
        raise ValueError("Original two-record state update changed at bank1 375A")
    return {
        "source": "original 1991 Indy Heat arcade master Z80 banked ROM",
        "original_event_flag_consumers": len(result),
        "original_instruction_aligned_producer_sites": sum(
            len(x["known_aligned_set_sites"]) for x in result
        ),
        "flag_records": result,
        "two_record_status_site": {
            "bank": 1, "ix_status_set_pc": "3736", "iy_status_set_pc": "375A",
            "field": "+33", "bit": 3,
            "meaning": "Both IX and IY records assigned identical flag; game cause UNVERIFIED",
        },
        "limitation": "Static SET instructions are candidate flag sources. Other writes to whole bytes and untraced indirect execution remain open.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path)
    p.add_argument("--out", type=Path,
                   default=Path("local/engine-extraction/original_flag_provenance.json"))
    args = p.parse_args()
    result = inspect(args.master.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Event consumers:", result["original_event_flag_consumers"])
    print("Confirmed static SET sites:", result["original_instruction_aligned_producer_sites"])
    print("Additional candidate writers and dynamic execution still need tracing.")


if __name__ == "__main__":
    main()
