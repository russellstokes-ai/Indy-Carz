#!/usr/bin/env python3
"""Verify the original arcade's 6,912-entry collision contact lookup stage.

Original 1991 Indy Heat master CPU $B4A3-$B4D3 selects master ROM bank 5,
indexes a 18*24*16 three-byte contact table using two accepted rotated
coordinate values and the upper nibble of relative car heading, and tests
whether the first output byte has bit 7 set. A successful contact falls through
to $B4D4. Downstream collision response remains to be recovered.

Requires private verified MAME-rotated ROM images. Never publish the extracted
table, original binary or derived commercial artwork in the public repository.
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
CONTACT_TABLE_SHA = "6f220e853ecb22bd0f5c5697400c651c4ac06e9335e40eb832cfdb611c9febec"
START = 0xB4A3
STOP = 0xB4D4
BANK5_OFFSET = 0x38000
TABLE_BYTES = 18 * 24 * 16 * 3
BANK_SELECTION = bytes.fromhex("3A 08 E6 E6 F0 F6 05 32 08 E6 D3 F4")
BANK_RESTORE = bytes.fromhex("3A 08 E6 E6 F0 32 08 E6 D3 F4 C9")


def source_slot(first: int, second: int, angle_sector: int) -> int:
    if not (0 <= first < 18 and 0 <= second < 24 and 0 <= angle_sector < 16):
        raise ValueError("Original contact projections/sectors outside table dimensions")
    return 3 * ((first * 24 + second) * 16 + angle_sector)


def independent_contact(table: bytes, first: int, second: int, sector: int) -> tuple[int, int, bool, int]:
    """Independent source address and acceptance equation; not response physics."""
    if len(table) != TABLE_BYTES:
        raise ValueError("Expected exactly 6912 original three-byte records")
    index = source_slot(first, second, sector)
    status = table[index]
    return status, 0x2000 + index, (status & 0x80) == 0, sector << 4


def original_z80(master: bytes, xrom: bytes, first: int, second: int,
                 sector: int) -> tuple[int, int, bool, int]:
    """Bounded original Z80 instruction interpretation, $B4A3-$B4D3.

    Input A/AF' contains the second/first accepted axis scores from
    $B45A-$B4A2. IX/IY headings are chosen so their relative upper nibble
    equals sector. Stops on RET P or entry to $B4D4, refuses other opcodes.
    """
    source_slot(first, second, sector)
    if len(master) != 0x90000 or len(xrom) != 0x40000:
        raise ValueError("Wrong original master or X-ROM region length")
    pc, a, alt, h, l, d, e, carry, xaddr = START, second, first, 0, 0, 0, 0, 0, 0
    relative_angle_byte = sector << 4
    high_angle = None
    for _ in range(75):
        op = master[pc]
        if op == 0x08:  # EX AF,AF' - exchange the two projection scores
            a, alt = alt, a
            pc += 1
        elif op == 0x67:  # LD H,A
            h = a; pc += 1
        elif op == 0x2E:  # LD L,12
            if master[pc+1] != 12:
                raise ValueError("Original X-ROM multiplier differs")
            l = 12; pc += 2
        elif op == 0x22:  # LD ($FFFC),HL X-ROM address
            if master[pc+1:pc+3] != bytes.fromhex("fcff"):
                raise ValueError("Original X-ROM address port changed")
            xaddr = (h << 8) | l; pc += 3
        elif op == 0x2A:  # LD HL,($FFFC) X-ROM saturated signed product
            if master[pc+1:pc+3] != bytes.fromhex("fcff"):
                raise ValueError("Original X-ROM data port changed")
            product = xrom[2*xaddr] | (xrom[2*xaddr+1] << 8)
            h, l = product >> 8, product & 255; pc += 3
        elif op == 0x85:  # ADD A,L
            v = a+l
            a, carry = v & 255, int(v > 255)
            pc += 1
        elif op == 0x6F:  # LD L,A
            l = a; pc += 1
        elif op == 0xD2:  # JP NC,$B4B4
            target = master[pc+1] | (master[pc+2] << 8)
            if target != 0xB4B4:
                raise ValueError("Unexpected no-carry branch")
            pc = target if not carry else pc+3
        elif op == 0x24:  # INC H: propagate addition carry
            h = (h+1) & 255; pc += 1
        elif op == 0x29:  # ADD HL,HL
            v = ((h << 8) | l) << 1
            h, l = ((v >> 8) & 255), (v & 255)
            carry = int(v > 0xFFFF)
            pc += 1
        elif op == 0xFD:  # LD A,(IY-$43)
            if master[pc:pc+3] != bytes.fromhex("fd7ebd"):
                raise ValueError("Unknown original IY indexed opcode")
            a = relative_angle_byte; pc += 3
        elif op == 0xDD:  # SUB (IX-$43)
            if master[pc:pc+3] != bytes.fromhex("dd96bd"):
                raise ValueError("Unknown original IX indexed opcode")
            a = (a-0) & 255; pc += 3
        elif op == 0xE6:  # AND $F0
            if master[pc+1] != 0xF0:
                raise ValueError("Unexpected relative angle sector mask")
            a &= 0xF0
            carry = 0; pc += 2
        elif op == 0x32:  # LD ($E922),A
            if master[pc+1:pc+3] != bytes.fromhex("22e9"):
                raise ValueError("Unexpected angle sector destination")
            high_angle = a; pc += 3
        elif op == 0x0F:  # RRCA
            a = ((a >> 1) | (a << 7)) & 255; pc += 1
        elif op == 0xB5:  # OR L
            a |= l; pc += 1
        elif op == 0x54:  # LD D,H
            d = h; pc += 1
        elif op == 0x5D:  # LD E,L
            e = l; pc += 1
        elif op == 0x19:  # ADD HL,DE
            v = (h << 8 | l) + (d << 8 | e)
            h, l = ((v >> 8) & 255), (v & 255)
            carry = int(v > 0xFFFF)
            pc += 1
        elif op == 0x7C:  # LD A,H
            a = h; pc += 1
        elif op == 0xC6:  # ADD A,$20
            if master[pc+1] != 0x20:
                raise ValueError("Original banked lookup base changed")
            v = a + 0x20
            a, carry = v & 255, int(v > 255)
            pc += 2
        elif op == 0x7E:  # LD A,(HL) from *bank 5* ROM window
            address = (h << 8) | l
            if not 0x2000 <= address < 0x7100:
                raise ValueError(f"Original table lookup escaped: {address:04X}")
            a = master[BANK5_OFFSET + address - 0x2000]
            pc += 1
        elif op == 0xB7:  # OR A
            pc += 1
        elif op == 0xF0:  # RET P: exit if bit7 is clear
            if pc != 0xB4D3 or high_angle is None:
                raise ValueError("Unexpected original contact table return")
            return a, ((h << 8) | l), (a & 0x80) == 0, high_angle
        else:
            raise ValueError(f"Unknown arcade opcode {op:02X} at {pc:04X}")
        if not START <= pc < STOP:
            raise ValueError(f"Unexpected original contact control-flow destination {pc:04X}")
    raise ValueError("Contact table original opcode execution exceeded budget")


def inspect(master: bytes, xrom: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Original checksum-matched Indy Heat master Z80 required")
    if len(xrom) != 0x40000 or hashlib.sha256(xrom).hexdigest() != XROM_SHA:
        raise ValueError("Original checksum-matched arcade X-ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest() != STAGE_SHA:
        raise ValueError("Original contact stage opcode signature differs")
    if master[0xAD61:0xAD61+len(BANK_SELECTION)] != BANK_SELECTION:
        raise ValueError("Original bank-5 selection before car-pair pass not found")
    if master[0xB3A6:0xB3A6+len(BANK_RESTORE)] != BANK_RESTORE:
        raise ValueError("Original bank restore after pair pass not found")
    table = master[BANK5_OFFSET:BANK5_OFFSET + TABLE_BYTES]
    if hashlib.sha256(table).hexdigest() != CONTACT_TABLE_SHA:
        raise ValueError("Original 6912-record table hash differs")
    seen = Counter()
    sectors = []
    for first in range(18):
        for second in range(24):
            for sector in range(16):
                expected = independent_contact(table, first, second, sector)
                actual = original_z80(master, xrom, first, second, sector)
                if actual != expected:
                    raise AssertionError(f"Arcade contact stage differs at {first}, {second}, {sector}")
                seen["rejected" if actual[2] else "accepted"] += 1
    if (seen["accepted"], seen["rejected"]) != (4635, 2277):
        raise AssertionError("Unexpected original contact table outcome distribution")
    for sector in range(16):
        accepted = sum(bool(table[source_slot(a,b,sector)] & 0x80)
                       for a in range(18) for b in range(24))
        sectors.append({"relative_angle_sector": sector, "accepted": accepted,
                        "rejected": 18*24-accepted})
    return {
        "game": "indyheat original 1991 arcade",
        "confirmed_bank": 5,
        "bank_select_cpu_pc": "AD61",
        "bank_restore_cpu_pc": "B3A6",
        "contact_lookup_cpu_range": "2000-70FF (bank 5)",
        "original_routine_cpu_range": "B4A3-B4D3",
        "dimensions": [18, 24, 16],
        "record_bytes": 3,
        "original_table_sha256": CONTACT_TABLE_SHA,
        "address_formula": "0x2000 + 3 * ((first_projection*24 + second_projection)*16 + relative_heading_sector)",
        "accepted_by_status_sign": seen["accepted"],
        "rejected_by_status_sign": seen["rejected"],
        "original_z80_parity_cases": sum(seen.values()),
        "mismatches": 0,
        "per_sector": sectors,
        "accepted_processing": "fall through to B4D4; original stores first byte E919 and may read next two into E91A/E91B",
        "limitations": "Three output-byte gameplay meaning and downstream impact physics are not yet reconstructed",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("master", type=Path)
    p.add_argument("xrom", type=Path)
    p.add_argument("--out", type=Path,
                   default=Path("local/recovery/arcade_contact_table_parity.json"))
    a = p.parse_args()
    report = inspect(a.master.read_bytes(), a.xrom.read_bytes())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
