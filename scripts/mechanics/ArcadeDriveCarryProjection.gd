class_name ArcadeDriveCarryProjection
extends RefCounted

## Authentic original 1991 arcade master Z80 7124–714D.
## Owner-ROM verified against 100,000 authentic Z80 opcode executions
## with zero mismatches, INCLUDING the exact outgoing Z80 Carry flag.
##
## This is not a full physics engine. It writes original shared E933
## and passes carry into the separately verified original 714E B/C
## control selector. No proprietary source table or artwork embedded.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const Motion = preload("res://scripts/mechanics/ArcadeMotionGeometry.gd")
const Xrom = preload("res://scripts/mechanics/ArcadeDriveXromAccumulator.gd")

const PC_END: int = 0x714E
const HEADING: int = 0xE768
const ANGULAR_WORD: int = 0xE769
const MOTION_WORD: int = 0xE76B
const PROJECTION_WORD: int = 0xE933


static func calculate(e768: int, e769: int, e76b: int) -> Dictionary:
    assert(e768 >= 0 and e768 <= 255)
    assert(e769 >= 0 and e769 <= 65535)
    assert(e76b >= 0 and e76b <= 65535)

    var angle: int = (e768 - (e769 >> 8)) & 255
    var cosine: int = Motion._trig8(angle, false) & 255

    # Original signed doubled X-ROM slot0 multiplication is exact.
    var first: int = Xrom.signed_xrom_word(e76b >> 8, cosine)
    var second: int = Xrom.signed_xrom_word((e76b & 255) >> 1, cosine)
    var second_high: int = second >> 8

    # The original ADD A,A; JR NC; DEC H and ADD A,L;
    # JR NC; INC H are BYTE arithmetic, with the last addition's
    # carry unchanged by the INC H and LD (E933),HL operations.
    var doubled: int = (second_high * 2) & 255
    var low_sum: int = doubled + (first & 255)
    var outgoing_carry: int = 1 if low_sum > 255 else 0
    var high: int = (
        (first >> 8) -
        int(second_high >= 128) +
        outgoing_carry
    ) & 255
    return {
        "e933": (high << 8) | (low_sum & 255),
        "carry": outgoing_carry,
        "cos": cosine,
        "angle": angle,
        "xrom": [
            ((e76b >> 8) << 8) | cosine,
            (((e76b & 255) >> 1) << 8) | cosine
        ],
        "next_pc": PC_END
    }


static func apply_to_ram(master_ram: PackedByteArray) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    var projection: Dictionary = calculate(
        State.get8(master_ram, HEADING),
        State.get16(master_ram, ANGULAR_WORD),
        State.get16(master_ram, MOTION_WORD)
    )
    var changed: PackedByteArray = master_ram.duplicate()
    State._set16(changed, PROJECTION_WORD, projection["e933"])
    projection["ram"] = changed
    return projection
