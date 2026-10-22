class_name ArcadeSteeringWeightedInput
extends RefCounted

## Independently verified original 1991 Indy Heat master Z80 73CD-73F5.
##
## Actual original CPU and X-ROM interpretation: 100,000 synthetic cases
## plus 65,536 exhaustive motion/B combinations; zero mismatches.
## The first X-ROM slot1 rounded product is an input to SECOND rounded
## slot1 product. Do not combine them into one float calculation.
##
## NEG on original motion -128 calls original helper 1C85. That helper
## returns A=0x7F; it is NOT the non-returning CPU diagnostic 1689.
## This stage produces an A byte saved by original PUSH AF at 73F5.
## No car coordinate/heading memory is written until later original code.
##
## The selected factor from original fixed CPU 7635+table_index must be
## supplied by the caller. Original proprietary 65-byte table, source
## ROM, sprites and original track art are NOT part of this class.

const RETURN_PC: int = 0x73F6
const FACTOR_TABLE_BASE: int = 0x7635
const FACTOR_TABLE_ENTRIES: int = 65


static func _round8(left: int, right: int) -> int:
    assert(left >= 0 and left <= 255)
    assert(right >= 0 and right <= 255)
    return ((left * right) + 128) >> 8


static func original_table_index(original_e76c: int) -> int:
    assert(original_e76c >= 0 and original_e76c <= 255)
    var absolute: int = original_e76c
    if original_e76c >= 128:
        absolute = 256 - original_e76c
    # NEG on -128 overflows; original 1C85 clamps A to 127 and RETURNS.
    absolute = mini(absolute, 127)
    return (absolute + 1) >> 1


static func calculate(original_e76c: int,
                      original_b: int,
                      original_ix_minus_01: int,
                      supplied_factor: int) -> Dictionary:
    assert(original_e76c >= 0 and original_e76c <= 255)
    assert(original_b >= 0 and original_b <= 255)
    assert(original_ix_minus_01 >= 0 and original_ix_minus_01 <= 255)
    assert(supplied_factor >= 0 and supplied_factor <= 255)

    var index: int = original_table_index(original_e76c)
    var first: int = _round8(supplied_factor, original_b)
    var second: int = _round8(original_ix_minus_01, first)

    return {
        "weighted": second,
        "first_low": first,
        "factor": supplied_factor,
        "table_index": index,
        "xr_addresses": [
            (supplied_factor << 8) | original_b,
            (original_ix_minus_01 << 8) | first
        ],
        "neg128_saturated": original_e76c == 128,
        "next_pc": RETURN_PC
    }
