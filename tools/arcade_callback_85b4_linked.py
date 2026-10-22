#!/usr/bin/env python3
"""Original master 1783→85B4–85D7 linked-record callback, bounded at RAM.

The original IY record/pointer and dereferenced HL must be in E000–FFFF
master RAM. Missing memory reads stop at their actual original PC and
preserve prior writes. 100,000 original Z80 comparisons, zero mismatches.
No ROM, tables or graphics included.
"""
from __future__ import annotations
from arcade_callback_2eaf_prefix import independent as first_stage, IXS


def linked_85b4(ram: bytes | bytearray, ix: int) -> dict:
    if len(ram) != 0x2000 or ix not in IXS:
        raise ValueError("Original E000–FFFF master RAM and physical car IX required")
    out = bytearray(ram)
    iy = out[ix + 0x7C - 0xE000] | (out[ix + 0x7D - 0xE000] << 8)

    def available(address):
        return 0xE000 <= address <= 0xFFFF

    record = (iy + 0x1D) & 0xFFFF
    if not available(record):
        return _stop(out, 0x85B7, iy, -1, "requires_iy_record")
    if out[record - 0xE000] >= out[ix + 0x04 - 0xE000]:
        return _stop(out, 0x2EC7, iy, -1, "ret_nc", True)

    out[ix + 0x7E - 0xE000] ^= 0x10
    ptr_lo = (iy + 0x1E) & 0xFFFF
    ptr_hi = (iy + 0x1F) & 0xFFFF
    if not available(ptr_lo) or not available(ptr_hi):
        return _stop(out, 0x85C6, iy, -1, "requires_iy_pointer")
    hl = ((out[ptr_lo - 0xE000] | (out[ptr_hi - 0xE000] << 8)) + 1) & 0xFFFF
    out[ptr_hi - 0xE000] = hl >> 8
    out[ptr_lo - 0xE000] = hl & 0xFF
    if not available(hl):
        return _stop(out, 0x85D3, iy, hl, "requires_cpu_read")
    out[record - 0xE000] = out[hl - 0xE000]
    return _stop(out, 0x2EC7, iy, hl, "ret_full", True)


def _stop(ram: bytearray, next_pc: int, iy: int, hl: int,
          branch: str, returned: bool = False) -> dict:
    return dict(ram=bytes(ram), next_pc=next_pc, iy=iy, hl=hl,
                branch=branch, returned_to_2ec7=returned, complete=returned,
                unverified_downstream=("original continuation from 2EC7" if returned
                                       else "unavailable original CPU hardware memory view"))


def connected_2eaf_to_2ed0(ram: bytes | bytearray, ix: int) -> dict:
    """Follow original 2EAF, 85B4 and 2EC7 BIT0 gate to first unknown call."""
    first = first_stage(ram, ix)
    if first["next_pc"] != 0x85B4:
        return dict(first, original_2eaf=first, original_85b4={})
    linked = linked_85b4(first["ram"], ix)
    if not linked["returned_to_2ec7"]:
        return dict(linked, original_2eaf=first, original_85b4=linked)
    # Original 2EC7 BIT0,(IX+31), JR NZ 2ED0; otherwise CALL 22B8.
    if linked["ram"][ix + 0x31 - 0xE000] & 1:
        pc, branch = 0x2ED0, "post_callback_skip_22b8"
    else:
        pc, branch = 0x22B8, "post_callback_call_22b8"
    return dict(linked, next_pc=pc, branch=branch, complete=False,
                original_2eaf=first, original_85b4=linked,
                unverified_downstream="original 2ED0 downstream or 22B8 callback")
