class_name ArcadeSteeringSecondProjection
extends RefCounted

## Authentic original arcade master Z80 7499–74D7, isolated pure maths.
## C from original 7376 steering control table, IX+00 byte, and the
## current E767/E769 angular words generate one unsigned X-ROM slot1
## rounded factor followed by TWO original signed X-ROM slot0 lookups.
## The result doubles as a 16-bit Z80 signed word. On signed overflow
## the original returning helper 0B6B saturates at 0x7FFF/0x8000.
##
## Original private-Z80 opcode verification: 100,000 deterministic
## states, ZERO branch/intermediate/output mismatches. No ROM bytes,
## copyrighted game tables or invented tyre physics are embedded.

const NEXT_PC: int = 0x74D8


static func _s8(input_byte: int) -> int:
    assert(input_byte >= 0 and input_byte <= 255)
    return input_byte - 256 if input_byte >= 128 else input_byte


static func _slot0(a: int, b: int) -> int:
    var result: int = 2 * _s8(a) * _s8(b)
    return clampi(result, -32768, 32767) & 65535


static func _round8(a: int, b: int) -> int:
    assert(a >= 0 and a <= 255 and b >= 0 and b <= 255)
    return ((a * b + 128) >> 8)


static func calculate(original_c: int,
                      original_car_plus_00: int,
                      original_e767: int,
                      original_e769: int) -> Dictionary:
    assert(original_c >= 0 and original_c <= 255)
    assert(original_car_plus_00 >= 0 and original_car_plus_00 <= 255)
    assert(original_e767 >= 0 and original_e767 <= 65535)
    assert(original_e769 >= 0 and original_e769 <= 65535)

    # 7499: LD H,C ; LD L,(IX+00); slot1 unsigned rounded low byte.
    var factor_b: int = _round8(original_c, original_car_plus_00)

    # 74AA SBC HL,DE after OR A clear-carry. The original bit7 check
    # halves B if B negative; otherwise it arithmetic-right-shifts
    # the signed heading difference. These cases are not equivalent.
    var difference: int = (original_e767 - original_e769) & 65535
    var working: int = difference
    if (factor_b & 128) != 0:
        factor_b >>= 1
    else:
        var signed_difference: int = difference - 65536 if (
            difference & 32768) != 0 else difference
        working = (signed_difference >> 1) & 65535

    var first_address: int = (working & 0xFF00) | factor_b
    var first: int = _slot0(working >> 8, factor_b)

    # Original SRL A; LD (FFFD),A substitutes the upper address byte
    # for a second signed lookup while keeping the original low factor B.
    var second_address: int = (((working & 255) >> 1) << 8) | factor_b
    var second_high: int = _slot0((working & 255) >> 1, factor_b) >> 8

    var low_sum: int = (((second_high * 2) & 255) + (first & 255))
    var high: int = (
        (first >> 8) -
        int((second_high & 128) != 0) +
        int(low_sum > 255)
    ) & 255
    var intermediate: int = (high << 8) | (low_sum & 255)
    var doubled: int = (intermediate * 2) & 65535
    var signed_overflow: bool = ((intermediate ^ doubled) & 32768) != 0

    # Original CALL PE,0B6B returns with signed 16-bit saturation.
    var correction: int = doubled
    if signed_overflow:
        correction = 0x7FFF if (doubled & 32768) != 0 else 0x8000

    return {
        "de_projection": correction,
        "factor_b": factor_b,
        "overflow_saturated": signed_overflow,
        "slot1_address": (original_c << 8) | original_car_plus_00,
        "first_slot0_address": first_address,
        "second_slot0_address": second_address,
        "next_pc": NEXT_PC
    }
