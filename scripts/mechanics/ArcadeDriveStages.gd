class_name ArcadeDriveStages
extends RefCounted

## Two additional numeric stages recovered from the 1991 arcade master Z80.
##
## - master bank 0, $7039-$7043: multiplies a car input byte by $60 (96)
##   through the exact X-ROM 8x8 fixed-point lookup; stores result in B.
## - master bank 0, $709C-$70AB: multiplies B by $A6 (166) through X-ROM
##   and adds indexed car-record field IX+$54, saturating to $FF on carry
##   by calling the original fixed helper $0A9C.
##
## These operations are ORIGINAL numeric stages. Their use in complete
## acceleration, wheel dynamics, collision and fuel systems is *not*
## yet fully reverse-engineered. No new physics is introduced here.


static func xrom_rounded_u8(left: int, right: int) -> int:
    assert(left >= 0 and left <= 255, "Original X-ROM first operand must be 8-bit")
    assert(right >= 0 and right <= 255, "Original X-ROM second operand must be 8-bit")
    return ((left * right) + 128) >> 8


static func exceptional_input_branch(original_input: int) -> int:
    # Master bank0 $7039; IX-$1D counter adjustment occurs before this
    # stage and must be modelled by the eventual car-state update system.
    return xrom_rounded_u8(original_input, 0x60)


static func weighted_car_output(input_byte: int, car_field_54: int) -> int:
    # Master bank0 $709C through $70AB, including original carry helper.
    assert(car_field_54 >= 0 and car_field_54 <= 255, "Original IX+$54 is 8-bit")
    return mini(0xFF, xrom_rounded_u8(input_byte, 0xA6) + car_field_54)
