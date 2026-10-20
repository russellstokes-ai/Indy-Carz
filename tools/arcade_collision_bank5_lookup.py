#!/usr/bin/env python3
"""Recover Indy Heat's genuine bank-5, 6912-entry oriented contact table.

The original arcade master Z80 at fixed PC $AD64 selects bank 5. Its
$B4A3..$B4D3 routine looks up one of 18 x 24 x 16 records, each exactly
three bytes. This tool compares an independent index model against bounded
execution of the *original instructions* for all 6912 possible records.

The private user-provided arcade ROM is an input; NEVER commit extracted
tables, compiled original code, ROM images or game artwork to this repo.
This is original ENGINE EXTRACTION, not a replacement collision system.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA = "1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_SHA = "64b87e40c4b01bfa554ab8ee8a2829564f1567d3c9ed05bfa6ed0b21103c92cb"
TABLE_SHA = "6f220e853ecb22bd0f5c5697400c651c4ac06e9335e40eb832cfdb611c9febec"
BANK5_OFFSET = 0x38000
GRID_HEIGHT, GRID_WIDTH, HEADINGS, ENTRY_BYTES = 18, 24, 16, 3
TABLE_BYTES = GRID_HEIGHT * GRID_WIDTH * HEADINGS * ENTRY_BYTES
START, END = 0xB4A3, 0xB4D4


def source_assertions(master: bytes, xrom: bytes) -> bytes:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Original checksum-verified 1991 arcade master region required")
    if len(xrom) != 0x40000 or hashlib.sha256(xrom).hexdigest() != XROM_SHA:
        raise ValueError("Original checksum-verified arcade X-ROM region required")
    if hashlib.sha256(master[START:END]).hexdigest() != STAGE_SHA:
        raise ValueError("Original bank5 contact indexing Z80 opcode stage changed")
    # Restore upper master-bank control bits, then select bank 5 for collision.
    if master[0xAD64:0xAD6D] != bytes.fromhex("e6 f0 f6 05 32 08 e6 d3 f4"):
        raise ValueError("Original bank5 select at AD64 changed")
    if master[0xB3A6:0xB3B1] != bytes.fromhex("3a 08 e6 e6 f0 32 08 e6 d3 f4 c9"):
        raise ValueError("Original bank0 restore at B3A6 changed")
    # A negative first-byte result enters the original accepted-contact path.
    # Those instructions save the current/previous table addresses, contact
    # marker, and bump the contact count. Only the first two accepted events
    # reach B506 to read the next two record bytes.
    if master[0xB4D4:0xB4EE] != bytes.fromhex(
        "ed 5b 28 e9 ed 53 2a e9 22 28 e9 32 19 e9 "
        "3a 27 e9 3c 32 27 e9 fe 03 da 06 b5"
    ):
        raise ValueError("Original accepted-contact bookkeeping changed")
    if master[0xB506:0xB510] != bytes.fromhex(
        "23 7e 32 1a e9 23 7e 32 1b e9"
    ):
        raise ValueError("Original contact response record-byte loads changed")
    table = master[BANK5_OFFSET:BANK5_OFFSET + TABLE_BYTES]
    if hashlib.sha256(table).hexdigest() != TABLE_SHA:
        raise ValueError("Original bank5 contact lookup table digest differs")
    return table


def independent_index(axis0: int, axis1: int, heading_diff: int) -> int:
    """Exact arithmetic: 18 x 24 cells, 16 quantized relative headings."""
    if not 0 <= axis0 < GRID_HEIGHT or not 0 <= axis1 < GRID_WIDTH:
        raise ValueError("Original rotated position is outside lookup grid")
    if not 0 <= heading_diff < 256:
        raise ValueError("Original relative heading is an 8-bit subtraction")
    return ((axis0 * GRID_WIDTH + axis1) * HEADINGS
            + ((heading_diff & 0xF0) >> 4))


def independent_lookup(table: bytes, axis0: int, axis1: int,
                       heading_diff: int) -> tuple[int, bytes, bool]:
    if len(table) != TABLE_BYTES:
        raise ValueError("Original bank5 contact data must contain 20736 bytes")
    index = independent_index(axis0, axis1, heading_diff)
    addr = 0x2000 + ENTRY_BYTES * index
    entry = table[ENTRY_BYTES * index:ENTRY_BYTES * (index + 1)]
    # Original B4D1 reads first byte, OR A / RET P at B4D2-B4D3.
    return addr, entry, bool(entry[0] & 0x80)


def execute_original(master: bytes, xrom: bytes, table: bytes,
                     axis0: int, axis1: int,
                     angle_iy: int, angle_ix: int) -> tuple[int, bytes, bool]:
    """Interpret only original $B4A3..$B4D3; fail on unrecognised opcode.

    The first and second projection accumulators are the incoming main and
    alternate A registers, respectively. Both are known to pass upstream
    limits (axis0: 0..17, axis1: 0..23).
    """
    if len(master) < END or len(xrom) != 0x40000 or len(table) != TABLE_BYTES:
        raise ValueError("Missing original CPU region, X-ROM or contact bank")
    if not 0 <= axis0 < 18 or not 0 <= axis1 < 24:
        raise ValueError("Original projection did not pass previous stage")
    if not 0 <= angle_ix < 256 or not 0 <= angle_iy < 256:
        raise ValueError("Heading fields must be bytes")
    pc, a, alt = START, axis1, axis0
    h = l = d = e = carry = xrom_addr = 0
    current_addr = -1
    for _ in range(100):
        op = master[pc]
        if op == 0x08:  # EX AF,AF'
            a, alt = alt, a
            pc += 1
        elif op == 0x67:  # LD H,A
            h = a
            pc += 1
        elif op == 0x2E:  # LD L,n
            l = master[pc + 1]
            pc += 2
        elif op == 0x22:  # LD ($FFFC),HL = X-ROM slot0 address
            if master[pc+1:pc+3] != bytes.fromhex("fc ff"):
                raise ValueError(f"Unknown indexed-ROM address at {pc:04X}")
            xrom_addr = h << 8 | l
            pc += 3
        elif op == 0x2A:  # LD HL,($FFFC) = signed 16-bit multiplier
            if master[pc+1:pc+3] != bytes.fromhex("fc ff"):
                raise ValueError(f"Unknown indexed-ROM read at {pc:04X}")
            value = xrom[2*xrom_addr] | (xrom[2*xrom_addr+1] << 8)
            h, l = value >> 8, value & 255
            pc += 3
        elif op == 0x85:  # ADD A,L (carry retained for high-byte correction)
            value = a + l
            a, carry = value & 255, int(value > 255)
            pc += 1
        elif op == 0x6F:  # LD L,A
            l = a
            pc += 1
        elif op == 0xD2:  # JP NC,$B4B4
            if master[pc+1:pc+3] != bytes.fromhex("b4 b4"):
                raise ValueError("Unexpected Z80 carry-branch target")
            pc = 0xB4B4 if not carry else pc + 3
        elif op == 0x24:  # INC H
            h = (h + 1) & 255
            pc += 1
        elif op == 0x29:  # ADD HL,HL
            value = ((h << 8) | l) * 2
            h, l, carry = (value >> 8) & 255, value & 255, int(value > 65535)
            pc += 1
        elif op == 0xFD:  # LD A,(IY-$43)
            if master[pc+1:pc+3] != bytes.fromhex("7e bd"):
                raise ValueError(f"Unknown IY opcode at {pc:04X}")
            a = angle_iy
            pc += 3
        elif op == 0xDD:  # SUB (IX-$43)
            if master[pc+1:pc+3] != bytes.fromhex("96 bd"):
                raise ValueError(f"Unknown IX opcode at {pc:04X}")
            a = (a - angle_ix) & 255
            pc += 3
        elif op == 0xE6:  # AND $F0 (high nibble)
            a &= master[pc+1]
            carry = 0
            pc += 2
        elif op == 0x32:  # LD ($E922),A, orientation category before rotate
            if master[pc+1:pc+3] != bytes.fromhex("22 e9"):
                raise ValueError("Unexpected E922 direction category write")
            pc += 3
        elif op == 0x0F:  # RRCA x4
            a = ((a >> 1) | (a << 7)) & 255
            pc += 1
        elif op == 0xB5:  # OR L
            a |= l
            pc += 1
        elif op == 0x54:  # LD D,H
            d = h
            pc += 1
        elif op == 0x5D:  # LD E,L
            e = l
            pc += 1
        elif op == 0x19:  # ADD HL,DE
            value = ((h << 8) | l) + ((d << 8) | e)
            h, l, carry = (value >> 8) & 255, value & 255, int(value > 65535)
            pc += 1
        elif op == 0x7C:  # LD A,H
            a = h
            pc += 1
        elif op == 0xC6:  # ADD A,$20 (base address high byte)
            value = a + master[pc+1]
            a, carry = value & 255, int(value > 255)
            pc += 2
        elif op == 0x7E:  # LD A,(HL), mapped bank5 contact record byte
            current_addr = h << 8 | l
            if not 0x2000 <= current_addr <= 0x70FD:
                raise ValueError(f"Unexpected original contact table CPU addr {current_addr:04X}")
            a = table[current_addr-0x2000]
            pc += 1
        elif op == 0xB7:  # OR A (sign from first record byte)
            carry = 0
            pc += 1
        elif op == 0xF0:  # RET P if first table byte not negative
            if not (a & 0x80):
                offset = current_addr-0x2000
                return current_addr, table[offset:offset+3], False
            pc += 1
        else:
            raise ValueError(f"Unexpected original Z80 opcode {op:02X} at {pc:04X}")
        if pc == END:
            offset = current_addr-0x2000
            return current_addr, table[offset:offset+3], True
        if not START <= pc < END:
            raise ValueError(f"Original collision indexing left stage at {pc:04X}")
    raise ValueError("Original contact-index opcode budget exceeded")


def verify(master: bytes, xrom: bytes, export_private: Path | None = None) -> dict:
    table = source_assertions(master, xrom)
    checks = Counter()
    accepted = [0] * HEADINGS
    # Exhaust every possible index, including carry boundaries of the
    # 24 * first-axis + second-axis calculation and every heading nibble.
    for a0 in range(GRID_HEIGHT):
        for a1 in range(GRID_WIDTH):
            for heading in range(HEADINGS):
                iy, ix = (heading*16 + 13) & 255, 13
                expected = independent_lookup(table, a0, a1, (iy-ix) & 255)
                observed = execute_original(master, xrom, table, a0, a1, iy, ix)
                if observed != expected:
                    raise AssertionError(
                        f"Original collision table mismatch {a0},{a1},{heading}")
                checks["total"] += 1
                checks["accepted" if observed[2] else "rejected"] += 1
                accepted[heading] += int(observed[2])
    if export_private is not None:
        export_private.parent.mkdir(parents=True, exist_ok=True)
        export_private.write_bytes(table)
    # IMPORTANT: summary contains no original record payload values.
    return {
        "original": "1991 Indy Heat arcade master fixed PC B4A3..B4D3",
        "bank_select": "AD64: set master ROM bank5 via port F4",
        "bank_restore": "B3A6: clear master bank select nibble via port F4",
        "master_rom_bank": 5,
        "table_cpu_range": "2000..70FF",
        "table_size_bytes": TABLE_BYTES,
        "table_sha256": hashlib.sha256(table).hexdigest(),
        "spatial_bins": [GRID_HEIGHT, GRID_WIDTH],
        "relative_heading_bins": HEADINGS,
        "record_bytes": ENTRY_BYTES,
        "index_equation": "3 * (((axis0*24 + axis1)*16) + (((IY_angle-IX_angle)&0xF0)>>4))",
        "accepted_if": "record[0] bit7 == 1 (RET P rejects if bit7=0)",
        "original_opcode_cases": checks["total"],
        "accepted_record_cases": checks["accepted"],
        "rejected_record_cases": checks["rejected"],
        "accepted_per_heading": accepted,
        "mismatches": 0,
        "downstream_payload": "B506..B50F reads record[1] and record[2] into E91A and E91B on selected branch",
        "downstream_limit": "B4E9 compares E927 contact count with 3; full response still unresolved",
        "scope": "Complete table/index and first-byte acceptance only; responses and game parity OPEN",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path, help="PRIVATE master.mame_runtime.bin")
    p.add_argument("xrom", type=Path, help="PRIVATE xrom.mame_runtime.bin")
    p.add_argument("--out", type=Path, default=Path("local/recovery/collision_mask_report.json"))
    p.add_argument("--export-private-table", type=Path,
                   help="PRIVATE original 20736-byte ROM-derived table; never commit")
    a = p.parse_args()
    result = verify(a.master.read_bytes(), a.xrom.read_bytes(), a.export_private_table)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("This does not establish collision response, impulse, damage or full engine parity.")


if __name__ == "__main__":
    main()
