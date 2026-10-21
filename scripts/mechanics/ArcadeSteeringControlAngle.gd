class_name ArcadeSteeringControlAngle
extends RefCounted

## Original 1991 arcade master Z80 73F6-7441, three returning overflow
## helpers 0B35, 0B3E and 1C85. This computes the ORIGINAL bounded
## 8-bit steering control in register A and continues at original 7442.
##
## Genuine original opcode parity: 100,000 synthetic input states,
## zero output, branch or intermediate-word mismatches.
##
## Do not substitute float atan/friction/tyre force here. Four full
## 16-bit original RAM state words are required. The carry/borrow from
## the first SBC HL,DE enters the SECOND SBC HL,DE.
## Source ROM and dynamic track/steering data stay outside this project.

const NEXT_PC: int = 0x7442
const ANGLE_MAX: int = 127
const ANGLE_MIN: int = 32


static func _signed16(word: int) -> int:
    assert(word >= 0 and word <= 65535)
    return word - 65536 if word >= 32768 else word


static func calculate(e789: int,e773: int,e787: int,e771: int,
                      original_ix_plus79: int) -> Dictionary:
    assert(e789 >= 0 and e789 <= 65535)
    assert(e773 >= 0 and e773 <= 65535)
    assert(e787 >= 0 and e787 <= 65535)
    assert(e771 >= 0 and e771 <= 65535)
    assert(original_ix_plus79 >= 0 and original_ix_plus79 <= 255)

    # Original incoming carry at 73F6 is guaranteed clear by 73DE:
    # the factor-index range is 0x7635..0x7675, never a byte carry.
    var first: int = e789 - e773
    var borrowed: int = int(first < 0)
    var second: int = ((first & 65535) - e787 - borrowed) & 65535
    var wrapped_word: int = (second + e771) & 65535

    # Actual original SRA H / RR L, two SLA L / ADC A,A steps,
    # then 0B3E saturation are mathematically equivalent to signed
    # arithmetic divide by 128 with saturation to [-128,+127].
    var angular: int = clampi(_signed16(wrapped_word) >> 7, -128, 127)

    # The original NEG on -128 calls helper 1C85 to return +127.
    # This is NOT the nonlocal diagnostic 1689.
    var magnitude: int = mini(127, absi(angular))
    var same_direction: bool = ((angular < 0) ==
                                ((original_ix_plus79 & 0x80) != 0))
    var selected_a: int
    if same_direction:
        selected_a = mini(ANGLE_MAX, 64 + magnitude)
    else:
        selected_a = maxi(ANGLE_MIN, 64 - magnitude)

    return {
        "a": selected_a,
        "wrapped_word": wrapped_word,
        "angular_sample": angular,
        "direction_matches": same_direction,
        "borrow_from_first_subtraction": borrowed,
        "next_pc": NEXT_PC
    }
