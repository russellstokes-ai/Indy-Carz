#!/usr/bin/env python3
"""Replay MAME-confirmed memory effects of original Indy Heat 2B77 bus writes.

Original ROM-free Z80 bus trace supplies 3 F4 changes and 8 CPU writes.
This module models only MAME-documented writable A000-DFFF battery/QRAM
planes and ROM write ignores. Other write regions fail closed, atomically.
Real frame timing, video rendering, and return into game code remain open.
"""
from __future__ import annotations

from arcade_event_2b77_bus import independent as original_bus, IXS
from arcade_master_bank_map import banked_write_target

BATTERY_SIZE = 0x4000
QRAM_SIZE = 0x10000


def replay(master_ram: bytes | bytearray, ix: int,
           battery_ram: bytes | bytearray, qram: bytes | bytearray) -> dict:
    """Return copies of affected hardware planes; do not mutate caller state."""
    if type(battery_ram) not in (bytes, bytearray) or len(battery_ram) != BATTERY_SIZE:
        raise ValueError("Supply 0x4000 bytes of original battery RAM")
    if type(qram) not in (bytes, bytearray) or len(qram) != QRAM_SIZE:
        raise ValueError("Supply 0x10000 bytes of original QRAM")
    if ix not in IXS:
        raise ValueError("Physical car IX required")

    trace = original_bus(master_ram, ix)
    actions = []
    for bank, addr, value in trace["memory_writes"]:
        if 0 <= addr < 0xA000:
            actions.append(("rom_write_ignored", -1, value, bank, addr))
        elif 0xA000 <= addr <= 0xDFFF:
            kind, offset = banked_write_target(addr, bank)
            actions.append((kind, -1 if offset is None else offset,
                            value, bank, addr))
        else:
            raise ValueError(
                f"CPU target 0x{addr:04X} requires separate hardware model")

    battery_out, qram_out = bytearray(battery_ram), bytearray(qram)
    dirty_tiles, partial_updates = [], 0
    for kind, offset, value, bank, addr in actions:
        if kind == "battery_ram":
            battery_out[offset] = value
        elif kind == "qram":
            qram_out[offset] = value
            dirty_tiles.append(((bank & 0x80) << 8) | (addr - 0xA000))
            partial_updates += 1
    return dict(ram=trace["ram"], battery_ram=bytes(battery_out),
                qram=bytes(qram_out), next_pc=trace["next_pc"],
                bank_writes=trace["bank_writes"],
                memory_writes=trace["memory_writes"],
                mapped_writes=tuple(actions),
                qram_dirty_tiles=tuple(dirty_tiles),
                partial_update_requests=partial_updates,
                memory_replay_complete=True, engine_return_verified=False)
