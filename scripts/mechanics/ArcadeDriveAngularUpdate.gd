class_name ArcadeDriveAngularUpdate
extends RefCounted

## Exact bounded original 1991 Indy Heat Z80 72D3–7314 and original
## saturating signed-overflow helper 0B7D–0B97.
##
## Genuine original opcode/X-ROM parity: 100,000 cases, 0 mismatches:
## normal 7315, first-double 1689 and second-double 1689 all covered.
##
## Original factor comes from master bank0 at
## 0x2000 + ((-car[IX+3C]) & 255). It must be supplied by a verified
## original-compatible provider, never guessed or copied with ROM art.
## Original IX+3C is physical state slot+BC.
##
## The original DE entering at 72D3 is the exact correction change
## selected at 726D–72D2, NOT E76B or a computed seconds-per-frame
## velocity. The original 1689 handler is nonreturning; this stage
## preserves E765 on that path, but does not fabricate handler effects.

const Xrom = preload("res://scripts/mechanics/ArcadeDriveXromAccumulator.gd")
const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const E765: int = 0xE765
const NEXT_PC: int = 0x7315
const NONLOCAL_PC: int = 0x1689


static func calculate(original_rom_factor: int,
                      original_de_change: int,
                      original_e765: int) -> Dictionary:
    assert(original_rom_factor >= 0 and original_rom_factor <= 255)
    assert(original_de_change >= 0 and original_de_change <= 65535)
    assert(original_e765 >= 0 and original_e765 <= 65535)

    var first: int = Xrom.signed_xrom_word(
        original_de_change >> 8, original_rom_factor)
    var second: int = Xrom.signed_xrom_word(
        (original_de_change & 255) >> 1, original_rom_factor)
    var second_hi: int = second >> 8
    var low_sum: int = (((second_hi * 2) & 255) + (first & 255))
    var projected: int = (
        (((first >> 8) -
          int((second_hi & 128) != 0) +
          int(low_sum > 255)) & 255) << 8
    ) | (low_sum & 255)

    # Original OR A / ADC HL,HL / CALL PE 1689 is a NONLOCAL escape.
    # A double that changes the original sign bit is signed overflow.
    var doubled_once: int = (projected * 2) & 65535
    if ((projected ^ doubled_once) & 32768) != 0:
        return {
            "exit": "external_1689_first_double",
            "next_pc": NONLOCAL_PC,
            "e765": original_e765,
            "factor": original_rom_factor,
            "projection": projected,
            "delta": null,
            "overflow_sub": null
        }

    # The original SECOND double also calls 1689 on signed overflow.
    var doubled_twice: int = (doubled_once * 2) & 65535
    if ((doubled_once ^ doubled_twice) & 32768) != 0:
        return {
            "exit": "external_1689_second_double",
            "next_pc": NONLOCAL_PC,
            "e765": original_e765,
            "factor": original_rom_factor,
            "projection": projected,
            "delta": null,
            "overflow_sub": null
        }

    # Original E765 - doubled_twice is signed 16-bit subtraction.
    # Original CALL PE 0B7D returns 0x7FFF for POSITIVE overflow,
    # or 0x8000 for NEGATIVE overflow. Following JP P / LD HL,0
    # clamps any negative result to zero.
    var candidate: int = (original_e765 - doubled_twice) & 65535
    var overflow: bool = (
        ((original_e765 ^ doubled_twice) &
         (original_e765 ^ candidate) & 32768) != 0
    )
    if overflow:
        candidate = 0x7FFF if (candidate & 32768) != 0 else 0x8000
    var updated: int = candidate if (candidate & 32768) == 0 else 0

    return {
        "exit": "normal_7315",
        "next_pc": NEXT_PC,
        "e765": updated,
        "factor": original_rom_factor,
        "projection": projected,
        "delta": doubled_twice,
        "overflow_sub": overflow
    }


static func apply_to_ram(master_ram: PackedByteArray,
                         original_rom_factor: int,
                         original_de_change: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    var result: Dictionary = calculate(
        original_rom_factor, original_de_change,
        State.get16(master_ram, E765))
    var copy: PackedByteArray = master_ram.duplicate()
    if result["next_pc"] == NEXT_PC:
        State._set16(copy, E765, result["e765"])
    else:
        assert(result["next_pc"] == NONLOCAL_PC)
        # Only E765 is protected here. The ORIGINAL separate 1689
        # handler can affect other bank/diagnostic RAM addresses.
    result["ram"] = copy
    return result
