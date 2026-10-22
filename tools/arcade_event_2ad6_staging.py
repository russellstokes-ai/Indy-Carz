#!/usr/bin/env python3
"""Original Z80 2AD6–2B76 event-word staging, without original ROM bytes.

The real 2B77 F4 bank-selection and QRAM writes remain unresolved.
Private opcode interpreter versus independent model: 100,000 cases, zero mismatches.
"""
from __future__ import annotations

IXS = (0xE080, 0xE180, 0xE280, 0xE380, 0xE480)
SOURCE_BASE = 0x3F00
SOURCE_LENGTH = 512
SOURCE_OFFSETS = (0x3F50, 0x3F38, 0x3F20, 0x3F08)
MISSING_SOURCE_PC = (0x2AED, 0x2B14, 0x2B3E, 0x2B63)


def independent(ram: bytes | bytearray, ix: int,
                source: bytes | bytearray | None = None) -> dict:
    if len(ram) != 0x2000 or ix not in IXS:
        raise ValueError("Original E000–FFFF master RAM and physical car IX required")
    if source is not None and len(source) != SOURCE_LENGTH:
        raise ValueError("Expected original mapped 3F00–40FF source window (4000+ may be banked)")
    out = bytearray(ram)
    value = out[ix + 0x3A - 0xE000]
    group = 0 if value < 12 else 1 if value < 36 else 2 if value < 60 else 3
    source_address = SOURCE_OFFSETS[group] + value
    if source is None:
        return dict(ram=bytes(out), next_pc=MISSING_SOURCE_PC[group],
                    group=group, complete=False, source_addr=source_address,
                    stack_word=0x0108)

    values = [[1, 0] for _ in range(4)]
    for i in range(group):
        values[i] = [19, 0]
    values[group] = [source[source_address - SOURCE_BASE],
                     source[source_address + 25 - SOURCE_BASE]]
    for i, (low, high) in enumerate(values):
        out[0x900 + 2 * i] = low
        out[0x901 + 2 * i] = high
    return dict(ram=bytes(out), next_pc=0x2B77, group=group,
                complete=True, source_addr=source_address, stack_word=0x0108)
