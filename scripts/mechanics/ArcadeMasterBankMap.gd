class_name ArcadeMasterBankMap
extends RefCounted

## Original Ataxx/Indy Heat master Z80 F4 hardware mapping, as documented
## by MAME leland.cpp, leland_m.cpp and leland_v.cpp. Requires a caller-owned
## MAME-rotated 0x90000-byte master image and the ACTUALLY OBSERVED F4 value.
## Never infer the active bank solely from an E608 shadow. No ROM included.

const MASTER_SIZE: int = 0x90000
const SOURCE_START: int = 0x3F00
const SOURCE_LENGTH: int = 512
const BANK_BASES = [
    0x02000, 0x18000, 0x20000, 0x28000,
    0x30000, 0x38000, 0x40000, 0x48000,
    0x50000, 0x58000, 0x60000, 0x68000,
    0x70000, 0x78000, 0x80000, 0x88000
]


static func bank_base(observed_f4: int) -> int:
    assert(observed_f4 >= 0 and observed_f4 <= 255)
    return BANK_BASES[observed_f4 & 0x0F]


static func mapped_rom_offset(cpu_address: int, observed_f4: int) -> int:
    assert(cpu_address >= 0x2000 and cpu_address <= 0x9FFF)
    return bank_base(observed_f4) + cpu_address - 0x2000


static func event_source_window(
        rotated_master_region: PackedByteArray,
        observed_f4: int) -> PackedByteArray:
    ## All original CPU addresses 3F00..40FF are inside 2000..9FFF
    ## and therefore depend on the active F4 low-nibble bank.
    assert(rotated_master_region.size() == MASTER_SIZE)
    var first: int = mapped_rom_offset(SOURCE_START, observed_f4)
    return rotated_master_region.slice(first, first + SOURCE_LENGTH)


static func banked_write_target(cpu_address: int, observed_f4: int) -> Dictionary:
    ## MAME 0xA000..0xDFFF memory view only. No speculative writes to
    ## other CPU ranges or simulation of tilemap/screen side effects.
    assert(cpu_address >= 0xA000 and cpu_address <= 0xDFFF)
    assert(observed_f4 >= 0 and observed_f4 <= 255)
    var view: int = observed_f4 & 0x30
    var offset: int = cpu_address - 0xA000
    if view == 0x10:
        return {"target": "battery_ram", "offset": offset}
    if view == 0x20:
        return {"target": "qram",
                "offset": ((observed_f4 & 0xC0) << 8) | offset}
    return {"target": "rom_write_ignored", "offset": -1}
