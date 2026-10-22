class_name ArcadeDriveXromAccumulator
extends RefCounted

## Exact bounded original 1991 arcade Z80 motion stage 71FA..7224.
## The signed 8x8 slot0 X-ROM is reproduced mathematically, including
## original doubled-product 16-bit saturation; no copyrighted ROM table
## or image data are embedded in this independent implementation.
##
## Genuine original CPU parity: 100,000 cases, 0 branch/output mismatches.
## The original overflow CALL 1689 is NONLOCAL and remains unresolved.
## Caller MUST NOT invent a DE result for that branch or proceed as though
## the original operation had completed. No full physics is implied here.

const NEXT_PC: int = 0x7225
const ORIGINAL_EXTERNAL: int = 0x1689


static func _signed8(value: int) -> int:
    assert(value >= 0 and value <= 255)
    return value - 256 if value >= 128 else value


static func _signed16(value: int) -> int:
    assert(value >= 0 and value <= 65535)
    return value - 65536 if value >= 32768 else value


static func signed_xrom_word(a: int, b: int) -> int:
    ## Verified all 65,536 original slot0 X-ROM 16-bit products.
    var raw: int = _signed8(a) * _signed8(b) * 2
    return clampi(raw, -32768, 32767) & 0xFFFF


static func calculate(original_c: int,
                       original_e933: int,
                       incoming_de: int) -> Dictionary:
    assert(original_c >= 0 and original_c <= 255)
    assert(original_e933 >= 0 and original_e933 <= 65535)
    assert(incoming_de >= 0 and incoming_de <= 65535)

    if original_c == 0:
        return {
            "exit": "skip_C_zero",
            "next_pc": NEXT_PC,
            "de": incoming_de,
            "xr_addresses": []
        }

    var first_address: int = (original_e933 & 0xFF00) | original_c
    var second_address: int = (((original_e933 & 255) >> 1) << 8) | original_c
    var first: int = signed_xrom_word(original_e933 >> 8, original_c)
    var second: int = signed_xrom_word((original_e933 & 255) >> 1, original_c)

    var first_lo: int = first & 255
    var first_hi: int = first >> 8
    var second_hi: int = second >> 8
    var doubled: int = (second_hi * 2) & 255
    var low_sum: int = doubled + first_lo
    var mixed_hi: int = (first_hi - int((second_hi & 0x80) != 0) +
                         int(low_sum > 255)) & 255
    var mixed: int = (mixed_hi << 8) | (low_sum & 255)

    # The original SRA H; RR L is signed 16-bit shift with carry
    # equal to the lowest pre-shift bit, then ADC HL,DE.
    var shifted: int = (_signed16(mixed) >> 1) & 65535
    var total: int = (shifted + incoming_de + (mixed & 1)) & 65535
    var shift_sign: bool = (shifted & 0x8000) != 0
    var de_sign: bool = (incoming_de & 0x8000) != 0
    var total_sign: bool = (total & 0x8000) != 0
    var original_overflow: bool = (shift_sign == de_sign) and (shift_sign != total_sign)

    return {
        "exit": "external_1689" if original_overflow else "normal_7225",
        "next_pc": ORIGINAL_EXTERNAL if original_overflow else NEXT_PC,
        "de": null if original_overflow else total,
        "xr_addresses": [first_address, second_address]
    }
