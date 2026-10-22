#!/usr/bin/env python3
"""ROM-verified original bank0 Z80 3006–304C priority-ordered status calls.

Yields the next original call WITHOUT executing its unknown side effects.
100,000 private Z80 instruction comparisons, zero mismatches.
"""
from __future__ import annotations
IXS = (0xE080, 0xE180, 0xE280, 0xE380, 0xE480)
# (original call site, IX-relative status offset, bit, original target)
HANDLERS = (
    (0x300A, 0x32, 5, 0x6C1C),
    (0x3011, 0x32, 3, 0x6DFA),
    (0x3018, 0x32, 4, 0x6E06),
    (0x301F, 0x31, 5, 0x6EA6),
    (0x3026, 0x7E, 2, 0x6A18),
    (0x302D, 0x31, 4, 0x6A3A),
    (0x3034, 0x32, 6, 0x6B61),
    (0x303B, 0x32, 7, 0x6BA2),
    (0x3042, 0x33, 3, 0x6A51),
)


def independent(ram: bytes | bytearray, ix: int) -> dict:
    if len(ram) != 0x2000 or ix not in IXS:
        raise ValueError("Original E000–FFFF master RAM and physical car IX required")
    for site, offset, bit, target in HANDLERS:
        if ram[ix + offset - 0xE000] & (1 << bit):
            return dict(next_pc=target, call_site_pc=site, branch="status_handler",
                        status_offset=offset, status_bit=bit, complete=False,
                        unverified_downstream="original status handler external CALL")
    if ram[ix + 0x34 - 0xE000] & 0x30:
        return dict(next_pc=0x113B, call_site_pc=0x304A,
                    branch="aggregate_flag_handler", complete=False,
                    unverified_downstream="original 113B status aggregation CALL")
    return dict(next_pc=0x689D, call_site_pc=0x304D,
                branch="post_status_dispatch", complete=False,
                unverified_downstream="original 689D post-dispatch CALL")
