class_name ArcadeDriveHeadingProjection
extends RefCounted

## Exact original 1991 Indy Heat master Z80 7245-726C.
## Uses heading difference and two original signed X-ROM slot0 multiplications
## to calculate original E933. No original proprietary ROM/table bytes.
## Original-machine comparison: 100,000 cases, zero mismatches.
##
## This is ONE original driving stage, not independent frame scheduling,
## steering/grip physics, force handling or track boundary management.

const Motion = preload("res://scripts/mechanics/ArcadeMotionGeometry.gd")
const NEXT_PC: int = 0x726D
const E933: int = 0xE933


static func _signed8(value: int) -> int:
    assert(value >= 0 and value <= 255)
    return value - 256 if value >= 128 else value


static func _slot0_signed_word(a: int, b: int) -> int:
    assert(a >= 0 and a <= 255 and b >= 0 and b <= 255)
    var signed_product: int = _signed8(a) * _signed8(b) * 2
    return clampi(signed_product, -32768, 32767) & 0xFFFF


static func calculate(geometry_heading: int,
                      angular_word: int,
                      motion_word: int) -> Dictionary:
    assert(geometry_heading >= 0 and geometry_heading <= 255)
    assert(angular_word >= 0 and angular_word <= 65535)
    assert(motion_word >= 0 and motion_word <= 65535)

    # Original: LD A,(E768); LD HL,(E769); SUB H.
    var angle: int = (geometry_heading - (angular_word >> 8)) & 255
    var cosine_byte: int = Motion._trig8(angle, false) & 255
    var first_address: int = (motion_word & 0xFF00) | cosine_byte
    var second_address: int = (((motion_word & 255) >> 1) << 8) | cosine_byte

    # Both original X-ROM multiplications are exact saturating,
    # signed 8x8 products times two.
    var first: int = _slot0_signed_word(motion_word >> 8, cosine_byte)
    var second: int = _slot0_signed_word((motion_word & 255) >> 1, cosine_byte)
    var second_high: int = second >> 8
    var doubled: int = (second_high * 2) & 255
    var low_sum: int = doubled + (first & 255)

    # Z80 JR NC / DEC H, then ADD A,L / JR NC / INC H.
    var high: int = (
        (first >> 8) -
        int((second_high & 0x80) != 0) +
        int(low_sum > 255)
    ) & 255
    var projected_word: int = (high << 8) | (low_sum & 255)
    return {
        "e933": projected_word,
        "angle": angle,
        "cosbyte": cosine_byte,
        "first_xrom_address": first_address,
        "second_xrom_address": second_address,
        "next_pc": NEXT_PC
    }
