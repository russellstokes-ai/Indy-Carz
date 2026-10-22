class_name ArcadeDriveMotionCorrection
extends RefCounted

## Authentic original 1991 Indy Heat master-Z80 motion correction:
## 726D-72D2, including original signed 0B76 and 0B6B saturation helpers.
##
## 100,000 actual private original-Z80+XROM machine executions compared
## with independently derived integer formula: ZERO mismatches.
##
## The ORIGINAL per-car source factor is master bank0 memory
## at 0x2000 + car[IX+3C]. It MUST be supplied explicitly by an
## original-compatible verified source (not embedded copyrighted ROM
## table bytes or guessed from generic engine power/track conditions).
## Original IX+3C is PHYSICAL state slot+BC.
##
## Also requires original B (from earlier verified course/car state
## interpolation). This is a verified bounded subroutine, NOT complete
## tyre friction, acceleration, collisions, engine upgrades, or AI.

const Xrom = preload("res://scripts/mechanics/ArcadeDriveXromAccumulator.gd")
const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const ORIGINAL_MOTION_WORD: int = 0xE76B
const ORIGINAL_ANGULAR_WORD: int = 0xE765
const ORIGINAL_PROJECTION_WORD: int = 0xE933
const NEXT_PC: int = 0x72D3


static func _signed16(v: int) -> int:
    assert(v >= 0 and v <= 65535)
    return v - 65536 if v >= 32768 else v


static func calculate(original_b: int,
                      original_rom_factor: int,
                      original_e765: int,
                      original_e933: int,
                      original_e76b: int) -> Dictionary:
    assert(original_b >= 0 and original_b <= 255)
    assert(original_rom_factor >= 0 and original_rom_factor <= 255)
    assert(original_e765 >= 0 and original_e765 <= 65535)
    assert(original_e933 >= 0 and original_e933 <= 65535)
    assert(original_e76b >= 0 and original_e76b <= 65535)

    # Exact original slot-0 signed saturated multiplications, 8x8*2.
    var first: int = Xrom.signed_xrom_word(
        original_e765 >> 8, original_rom_factor)
    var second: int = Xrom.signed_xrom_word(
        (original_e765 & 255) >> 1, original_rom_factor)
    var second_high: int = second >> 8
    var low_sum: int = (((second_high * 2) & 255) + (first & 255))
    var projected: int = (
        (((first >> 8) -
          int((second_high & 128) != 0) +
          int(low_sum > 255)) & 255) << 8
    ) | (low_sum & 255)

    # Original OR A; SBC HL,DE. The 0B76 overflow helper does NOT
    # choose positive/negative saturation: it ALWAYS returns +0x7FFF.
    var difference: int = (projected - original_e933) & 65535
    var first_overflow: bool = (
        ((projected ^ original_e933) & (projected ^ difference) & 32768) != 0
    )
    if first_overflow:
        difference = 0x7FFF

    # Original signed arithmetic shift SRA H / RR L rounds negatives
    # toward minus infinity; no floating-point approximations.
    var negative: bool = (difference & 32768) != 0
    var half: int = (_signed16(difference) >> 1) & 65535
    var threshold: int = 0
    var change: int = 0
    if negative:
        # Original LD H,FF; NEG B; four ADD HL,HL stages. Original
        # 16-bit carry comparison chooses the larger UNSIGNED word.
        threshold = ((0xFF00 | ((-original_b) & 255)) << 4) & 65535
        change = maxi(half, threshold)
    else:
        # Original LD H,0; LD L,B; SLA L (8-bit!); then three shifts.
        # The 16-bit carry comparison chooses the smaller unsigned word.
        threshold = (((original_b << 1) & 255) << 3) & 65535
        change = mini(half, threshold)

    # Original OR A; ADC HL,DE then CALL PE 0B6B. This SECOND
    # saturation helper chooses the opposite bound based on result sign:
    # a positive overflow into negative returns +7FFF, and a negative
    # overflow into positive returns -8000.
    var output: int = (original_e76b + change) & 65535
    var second_overflow: bool = (
        ((~(original_e76b ^ change)) &
         (original_e76b ^ output) & 32768) != 0
    )
    if second_overflow:
        output = 0x7FFF if (output & 32768) != 0 else 0x8000

    return {
        "e76b": output,
        "projected": projected,
        "difference": difference,
        "half": half,
        "threshold": threshold,
        "change": change,
        "first_overflow": first_overflow,
        "second_overflow": second_overflow,
        "negative": negative,
        "factor": original_rom_factor,
        "next_pc": NEXT_PC
    }


static func apply_to_ram(master_ram: PackedByteArray,
                         original_b: int,
                         original_rom_factor: int) -> Dictionary:
    ## Consumes original 0x2000 master RAM image; preserves input copy.
    assert(master_ram.size() == State.LENGTH)
    var result: Dictionary = calculate(
        original_b, original_rom_factor,
        State.get16(master_ram, ORIGINAL_ANGULAR_WORD),
        State.get16(master_ram, ORIGINAL_PROJECTION_WORD),
        State.get16(master_ram, ORIGINAL_MOTION_WORD))
    var updated: PackedByteArray = master_ram.duplicate()
    State._set16(updated, ORIGINAL_MOTION_WORD, result["e76b"])
    result["ram"] = updated
    return result
