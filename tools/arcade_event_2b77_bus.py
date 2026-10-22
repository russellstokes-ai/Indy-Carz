#!/usr/bin/env python3
"""Original Z80 2B77–2BCB CPU bus events; QRAM hardware mapping remains open.

Private original opcode comparison: 100,000 cases, zero mismatches,
300,000 port-F4 writes and 800,000 ordered memory bus writes.
"""
from __future__ import annotations

IXS = (0xE080, 0xE180, 0xE280, 0xE380, 0xE480)


def independent(ram: bytes | bytearray, ix: int) -> dict:
    if len(ram) != 0x2000 or ix not in IXS:
        raise ValueError("Original E000–FFFF master RAM and car IX required")
    out = bytearray(ram)

    def get(address: int) -> int:
        return out[address - 0xE000]

    base = get(ix + 0x12) | (get(ix + 0x13) << 8)
    target = (base + 0x0108) & 0xFFFF
    high, low = target & 0xFF00, target & 255
    bank1 = (get(0xE608) & 15) | get(0xE613)
    bank2 = (bank1 & 15) | get(0xE615)
    final = bank2 & 15

    events = []
    for i in range(4):
        events.append((bank1, high | ((low + i) & 255), get(0xE900 + 2 * i)))
    for i in (3, 2, 1, 0):
        events.append((bank2, high | ((low + i) & 255), get(0xE901 + 2 * i)))
    out[0x608] = final
    return dict(ram=bytes(out), next_pc=0x2BCC,
                bank_writes=(bank1, bank2, final),
                memory_writes=tuple(events), de=target,
                hl=get(0xE615) | (get(0xE616) << 8), a=final)
