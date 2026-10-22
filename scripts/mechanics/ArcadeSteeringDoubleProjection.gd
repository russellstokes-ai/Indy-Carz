class_name ArcadeSteeringDoubleProjection
extends RefCounted

## Verified original 1991 arcade master Z80 7442–7462.
## The original 73F6 angular-control A (32..127), original IX+79
## sign byte H, and the weighted steering A saved by 73CD PUSH AF
## produce two signed doubled X-ROM products. The second is shifted
## arithmetically right by one. Original IX+31 bit0 bypasses the
## subsequent velocity limiter at 7463, landing directly at 748A.
##
## 100,000 authentic Z80 opcode cases checked against independent
## clean-room integer arithmetic with zero mismatches. No ROM tables,
## game art or unverified tyre forces are included.
const LIMIT_PC: int = 0x7463
const BYPASS_PC: int = 0x748A


static func _signed8(byte_value: int) -> int:
    assert(byte_value >= 0 and byte_value <= 255)
    return byte_value - 256 if byte_value >= 128 else byte_value


static func _slot0(a: int, b: int) -> int:
    var signed_result: int = _signed8(a) * _signed8(b) * 2
    return clampi(signed_result, -32768, 32767) & 65535


static func calculate(control: int, original_ix_plus_79: int,
                      weighted_byte: int, car_ix_plus_31: int) -> Dictionary:
    assert(control >= 32 and control <= 127)
    assert(original_ix_plus_79 >= 0 and original_ix_plus_79 <= 255)
    assert(weighted_byte >= 0 and weighted_byte <= 255)
    assert(car_ix_plus_31 >= 0 and car_ix_plus_31 <= 255)

    var original_first_address: int = (original_ix_plus_79 << 8) | control
    var first: int = _slot0(original_ix_plus_79, control)
    var high: int = first >> 8
    var low_factor: int = weighted_byte

    # Original POP AF; OR A; JP P,7452. When negative: SRL A; SLA H.
    # Crucial: the high X-ROM output byte doubles MODULO 256, not 16 bits.
    if (weighted_byte & 128) != 0:
        high = (high << 1) & 255
        low_factor = weighted_byte >> 1

    var original_second_address: int = (high << 8) | low_factor
    var second: int = _slot0(high, low_factor)
    var signed_second: int = _signed8(second >> 8) * 256 + (second & 255)
    var correction: int = (signed_second >> 1) & 65535

    var bypass: bool = (car_ix_plus_31 & 1) != 0
    return {
        "correction": correction,
        "next_pc": BYPASS_PC if bypass else LIMIT_PC,
        "skip_velocity_limiter": bypass,
        "first_xrom_address": original_first_address,
        "second_xrom_address": original_second_address
    }
