class_name ArcadeSteeringSpeedLimiter
extends RefCounted

## Original 1991 arcade master Z80 7463–7498.
## The original steering projection in HL is either passed through
## from 748A (IX+31 bit0 set) or limited by a speed-dependent test.
## Its three SRA/RR 16-bit arithmetic shifts preserve a carry bit:
## bit2 of original E76B. Original SBC HL,BC then SBC HL,DE
## use inherited carries in sequence. This must NOT be replaced by
## floating-point clamping or a normal unbounded integer comparison.
##
## Original 100,000 Z80 opcode comparisons against an independent
## 16-bit state model, zero mismatches. No gameplay approximations,
## ROM contents, asset data or unverified collision forces embedded.

const OriginalRAM = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const NEXT_PC: int = 0x7499


static func calculate(projection: int, original_motion: int,
                      original_heading: int, car_ix_plus_31: int) -> Dictionary:
    assert(projection >= 0 and projection <= 65535)
    assert(original_motion >= 0 and original_motion <= 65535)
    assert(original_heading >= 0 and original_heading <= 65535)
    assert(car_ix_plus_31 >= 0 and car_ix_plus_31 <= 255)

    var selected: int = projection
    var limited: bool = false
    var bypass: bool = (car_ix_plus_31 & 1) != 0

    if not bypass:
        # First original three SRA B; RR C pairs: SIGNED 16-bit >> 3.
        var signed_motion: int = original_motion - 65536 if (
            original_motion & 0x8000) != 0 else original_motion
        var speed_eighth: int = (signed_motion >> 3) & 65535
        var inherited_carry: int = 1 if (original_motion & 4) != 0 else 0

        # Original LD HL,9600; SBC HL,BC uses inherited carry.
        var first: int = 0x9600 - speed_eighth - inherited_carry
        var first_borrow: int = 1 if first < 0 else 0
        var inverted_projection: int = projection ^ 0x8000

        # The second original SBC HL,DE consumes the FIRST borrow.
        var second: int = (first & 65535) - inverted_projection - first_borrow
        if second < 0:
            # Original ADD HL,DE, EX DE,HL, then XOR 80h on D.
            var restored: int = ((second & 65535) + inverted_projection) & 65535
            selected = restored ^ 0x8000
            limited = true

    return {
        "car4c4d": selected,
        "heading_e767": (original_heading + selected) & 65535,
        "limited": limited,
        "limiter_bypassed": bypass,
        "next_pc": NEXT_PC
    }


static func apply_to_ram(memory: PackedByteArray,
                         original_ix: int,
                         projected_word: int) -> Dictionary:
    ## This writes only the ORIGINAL car+4C/+4D and shared E767 word,
    ## using the exact same source inputs as original CPU 7463/748A.
    ## Return a copy: the caller's state must never be mutated here.
    assert(memory.size() == OriginalRAM.LENGTH)
    assert(OriginalRAM.CAR_POINTERS.has(original_ix))
    var result: Dictionary = calculate(
        projected_word,
        OriginalRAM.get16(memory, 0xE76B),
        OriginalRAM.get16(memory, 0xE767),
        OriginalRAM.get8(memory, original_ix + 0x31)
    )
    var out: PackedByteArray = memory.duplicate()
    OriginalRAM._set16(out, original_ix + 0x4C, result["car4c4d"])
    OriginalRAM._set16(out, 0xE767, result["heading_e767"])
    result["ram"] = out
    return result
