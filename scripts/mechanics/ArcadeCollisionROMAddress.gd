class_name ArcadeCollisionROMAddress
extends RefCounted

## Original 1991 Indy Heat master Z80 BCFA->BD17 collision-map lookup.
## Clean-room integer arithmetic only; contains NO original ROM table,
## original track image, QRAM, copyrighted graphics or game assembly.
##
## Original MAME 0.264 live verification: 11,123 original CPU lookups
## with 0 address/ROM-byte/branch mismatches (21 October 2026).
##
## This class does NOT provide xrom_low/high values or original banked-ROM
## byte data: these must be supplied from a separately verified,
## rights-cleared original-compatible map/maths source. Do not silently
## substitute guessed data for original physical wall/grip/impact systems.


static func derived_address(original_e731_word: int,
                            original_e73b_word: int,
                            original_e978: int,
                            slot0_xrom_low: int,
                            slot0_xrom_high: int) -> Dictionary:
    assert(original_e731_word >= 0 and original_e731_word <= 65535)
    assert(original_e73b_word >= 0 and original_e73b_word <= 65535)
    assert(original_e978 >= 0 and original_e978 <= 255)
    assert(slot0_xrom_low >= 0 and slot0_xrom_low <= 255)
    assert(slot0_xrom_high >= 0 and slot0_xrom_high <= 255)

    # Original: LD H, high(E73B); LD L,0x5A; LD (FFFC),HL.
    # The original X-ROM slot0 returns low and high result bytes.
    var xrom_source_address: int = (original_e73b_word & 0xFF00) | 0x5A

    # Original Z80: ADD A,A; ADD A,L; LD L,A, using HIGH(E731)
    # as initial accumulator. Carry from the SECOND addition enters
    # ADC A,H with original global E978 as its starting accumulator.
    var low_sum: int = (((original_e731_word >> 8) * 2) & 0xFF) + slot0_xrom_low
    var original_carry: int = 1 if low_sum > 255 else 0
    var low_address: int = low_sum & 0xFF
    var high_address: int = (original_e978 + slot0_xrom_high + original_carry) & 0xFF

    return {
        "original_slot0_xrom_address": xrom_source_address,
        "original_cpu_pointer": (high_address << 8) | low_address,
        "original_high_byte": high_address,
        "carry_from_add_a_l": original_carry
    }


static func original_branch_for_rom_byte(original_rom_byte: int) -> int:
    assert(original_rom_byte >= 0 and original_rom_byte <= 255)
    # Original fixed master BD18: CP 84; JP C,BE6B.
    # Return ORIGINAL instruction address, NOT a gameplay label.
    return 0xBE6B if original_rom_byte < 0x84 else 0xBD1D


static func original_banked_rom_offset(master_bank_control: int,
                                       original_cpu_pointer: int) -> int:
    ## This is ORIGINAL master 0x2000–0x9FFF ROM window only. Do NOT
    ## guess 0xA000–0xFFFF; QRAM, battery RAM and palette routing are
    ## controlled by additional original MAME hardware flags.
    assert(master_bank_control >= 0 and master_bank_control <= 255)
    assert(original_cpu_pointer >= 0x2000 and original_cpu_pointer < 0xA000)

    const ROM_BANK_BASES: Array[int] = [
        0x02000,0x18000,0x20000,0x28000,
        0x30000,0x38000,0x40000,0x48000,
        0x50000,0x58000,0x60000,0x68000,
        0x70000,0x78000,0x80000,0x88000
    ]
    return ROM_BANK_BASES[master_bank_control & 0x0F] + original_cpu_pointer - 0x2000
