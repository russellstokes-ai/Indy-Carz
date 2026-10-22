#!/usr/bin/env python3
"""Bounded original Z80 7EA3 event model; no ROM or course data bundled.

Private original-opcode comparison: 100,000 cases, zero mismatches.
The 8022 collision-service call and unprovided 1767 table stop explicitly.
"""
from __future__ import annotations
from arcade_effect_allocator_opcode_parity import independent_allocator

BASE = 0xE000
POOL = 0xE800
IXS = (0xE080, 0xE180, 0xE280, 0xE380, 0xE480)
TABLE_LENGTH = 14 * 5 * 4


def read(ram: bytes | bytearray, address: int) -> int:
    if not BASE <= address < 0x10000:
        raise ValueError(f"Invalid original RAM read {address:04X}")
    return ram[address - BASE]


def write(ram: bytearray, address: int, value: int) -> None:
    if not BASE <= address < 0x10000:
        raise ValueError(f"Invalid original RAM write {address:04X}")
    ram[address - BASE] = value & 255


def independent(ram: bytes | bytearray, ix: int,
                course_table: bytes | bytearray | None = None) -> dict:
    """Return exact bounded original state; no guessed event/collision effects."""
    if len(ram) != 0x2000 or ix not in IXS:
        raise ValueError("Expected E000..FFFF master RAM and authentic car IX")
    if course_table is not None and len(course_table) != TABLE_LENGTH:
        raise ValueError("Expected caller-provided 14*5*4-byte event table")
    out = bytearray(ram)
    write(out, ix + 0x31, read(out, ix + 0x31) | 0x40)
    write(out, ix + 0x7E, read(out, ix + 0x7E) | 0x08)
    category = read(out, ix + 0x4E)
    if category == 11 or category < 3:
        return dict(ram=bytes(out), branch="external_8022",
                    next_pc=0x8022, complete=False, slot=None)

    flags = read(out, ix + 0x33)
    if flags & 0x80:
        write(out, ix + 0x33, (flags | 0x40) & 0x7F)
        offset = read(out, ix + 0x64)
        if offset % 16:
            return dict(ram=bytes(out), branch="invalid_reuse_slot",
                        next_pc=0x7F1A, complete=False, slot=None)
        event = POOL + offset
        for field, value in ((3, 0x7F), (2, 0x39), (8, 4), (14, 0)):
            write(out, event + field, value)
        return dict(ram=bytes(out), branch="reuse_event",
                    next_pc=0x7091, complete=True, slot=offset // 16)

    a, slot, updated = independent_allocator(out[0x800:0x900], 0xDF)
    out[0x800:0x900] = updated
    if a == 255:
        return dict(ram=bytes(out), branch="allocation_rejected",
                    next_pc=0x7091, complete=True, slot=None)
    if slot is None:
        raise AssertionError("Original allocator succeeded without a slot")
    offset = slot * 16
    event = POOL + offset
    write(out, ix + 0x33, read(out, ix + 0x33) | 0x40)
    # Original DD 75 64 stores L, not IXL.
    write(out, ix + 0x64, offset)
    write(out, event + 15, read(out, ix - 3))
    for field, value in ((0, 3), (3, 0x7F), (2, 0x33)):
        write(out, event + field, value)

    course = read(out, 0xE699)
    car = read(out, ix - 3)
    if course_table is None or course >= 14 or car >= 5:
        return dict(ram=bytes(out), branch="course_lookup_pending",
                    next_pc=0x1767, complete=False, slot=slot)

    e, d, l, h = course_table[(course * 5 + car) * 4:(course * 5 + car) * 4 + 4]
    for field, value in ((5, d), (4, e), (6, l), (7, h),
                         (8, 1), (9, read(out, ix + 0x75) | 1),
                         (10, read(out, ix + 0x75) | 10), (11, 255), (14, 0)):
        write(out, event + field, value)
    return dict(ram=bytes(out), branch="allocated_free" if a == 1 else "allocated_replace",
                next_pc=0x7091, complete=True, slot=slot)
