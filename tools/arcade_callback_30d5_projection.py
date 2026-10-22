#!/usr/bin/env python3
"""Original Z80 master bank0 30D5–30F7 callback vector prelude.

Copies original shared velocity words and reconstructs outgoing registers,
Z80 F flags, and EXX-saved registers up to JP D958. The D958 side effects
are NOT recovered. 100,000 private opcode comparisons, zero mismatches.
"""
from __future__ import annotations
IXS = (0xE080, 0xE180, 0xE280, 0xE380, 0xE480)


def independent(ram: bytes | bytearray, ix: int,
                incoming_a: int, incoming_hl: int) -> dict:
    if len(ram) != 0x2000 or ix not in IXS:
        raise ValueError("Original E000–FFFF RAM and physical car IX required")
    if (type(incoming_a) is not int or not 0 <= incoming_a <= 0xFF or
            type(incoming_hl) is not int or not 0 <= incoming_hl <= 0xFFFF):
        raise ValueError("Original incoming Z80 A and HL registers required")
    out = bytearray(ram)

    def read16(addr):
        return out[addr - 0xE000] | (out[addr + 1 - 0xE000] << 8)

    def write16(addr, value):
        out[addr - 0xE000] = value & 0xFF
        out[addr + 1 - 0xE000] = (value >> 8) & 0xFF

    alt_bc = read16(0xE96F)
    alt_de = read16(0xE971)
    write16(0xE77D, alt_bc)
    write16(0xE77F, alt_de)
    c = incoming_a | out[ix + 0x75 - 0xE000]
    source_hl = read16(0xE735)
    doubled = source_hl << 1
    hl = doubled & 0xFFFF
    a = (~(hl >> 8)) & 0xFF
    # OR sets S/Z/PV; ADD HL,HL updates carry; CPL sets H/N and F3/F5.
    flags = ((c & 0x80) | (0x40 if c == 0 else 0) |
             (0x04 if c.bit_count() % 2 == 0 else 0) |
             (1 if doubled > 0xFFFF else 0) | 0x12 | (a & 0x28))
    return dict(ram=bytes(out), next_pc=0xD958, branch="jp_d958",
                a=a, f=flags, bc=(a << 8) | c,
                de=read16(0xE94E), hl=hl, alt_bc=alt_bc,
                alt_de=alt_de, alt_hl=incoming_hl,
                complete=False,
                unverified_downstream="original D958 callback renderer/dispatch")
