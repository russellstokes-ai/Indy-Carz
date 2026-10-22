#!/usr/bin/env python3
"""ROM-free MAME-verified master Z80 bank mapping for Indy Heat.

Input master_region must be the 0x90000-byte image *after* MAME's
leland_state::rotate_memory. The last observed port-F4 byte, not an
unverified E608 shadow, selects the active bank. No ROM bytes are bundled.
"""
from __future__ import annotations

MASTER_SIZE = 0x90000
BANK_BASES = (0x02000,) + tuple(range(0x18000, 0x90000, 0x8000))
SOURCE_START = 0x3F00
SOURCE_END_EXCLUSIVE = 0x4100


def _f4(value: int) -> int:
    if type(value) is not int or not 0 <= value <= 255:
        raise ValueError("The last observed F4 output byte (0..255) is required")
    return value


def bank_base(observed_f4: int) -> int:
    """Physical MAME-rotated master ROM base for CPU 2000..9FFF."""
    return BANK_BASES[_f4(observed_f4) & 15]


def mapped_rom_offset(cpu_address: int, observed_f4: int) -> int:
    if type(cpu_address) is not int or not 0x2000 <= cpu_address <= 0x9FFF:
        raise ValueError("CPU address must be in banked ROM window 2000..9FFF")
    return bank_base(observed_f4) + cpu_address - 0x2000


def event_source_window(master_region: bytes | bytearray,
                        observed_f4: int) -> bytes:
    """Return original mapped CPU 3F00..40FF bytes.

    All 512 CPU addresses are banked (not only addresses >= 4000).
    """
    if len(master_region) != MASTER_SIZE:
        raise ValueError("Expected authenticated 0x90000 MAME-rotated master image")
    start = mapped_rom_offset(SOURCE_START, observed_f4)
    end = start + (SOURCE_END_EXCLUSIVE - SOURCE_START)
    return bytes(master_region[start:end])


def banked_write_target(cpu_address: int, observed_f4: int) -> tuple[str, int | None]:
    """Classify A000..DFFF writes using the actual MAME Ataxx/Indy Heat views.

    A000..DFFF is battery RAM when F4 bits 4..5 == 01, QRAM when == 10,
    and read-only ROM otherwise. QRAM plane is selected by F4 bits 6..7.
    This does not simulate screen partial updates or tilemap dirty marks.
    """
    if type(cpu_address) is not int or not 0xA000 <= cpu_address <= 0xDFFF:
        raise ValueError("Only the banked A000..DFFF memory view is modelled")
    control = _f4(observed_f4)
    view = control & 0x30
    offset = cpu_address - 0xA000
    if view == 0x10:
        return ("battery_ram", offset)
    if view == 0x20:
        return ("qram", ((control & 0xC0) << 8) | offset)
    return ("rom_write_ignored", None)
