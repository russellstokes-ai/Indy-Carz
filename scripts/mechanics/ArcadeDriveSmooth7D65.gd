class_name ArcadeDriveSmooth7D65
extends RefCounted

## Original 1991 Indy Heat master Z80 7D65–7E35, all five fixed-point
## smoothing projections and RET to 7024. Authenticated private original
## Z80 opcode parity: 100,000 cases, zero mismatches. No original binary,
## sprites, track data, floating interpolation or invented frame rate.
##
## Must run ONLY after original 701A CALL 7D4C bit1-clear selects 7D65.
## Caller resumes genuine 7024 JP7572 geometry-only then 75F1 saver.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const Xrom = preload("res://scripts/mechanics/ArcadeDriveXromAccumulator.gd")

const ENTRY_PC: int = 0x7D65
const NORMAL_CALL_RETURN: int = 0x7024


static func _project(original_difference: int, factor: int) -> int:
    assert(original_difference >= 0 and original_difference <= 65535)
    assert(factor == 0x10 or factor == 0x0C)
    var first: int = Xrom.signed_xrom_word(original_difference >> 8,factor)
    var second_high: int = Xrom.signed_xrom_word(
        (original_difference & 255) >> 1,factor) >> 8
    var low_sum: int = (((second_high << 1) & 255) + (first & 255))
    var high: int = ((first >> 8) - int((second_high & 128) != 0) +
                     int(low_sum > 255)) & 255
    return (high << 8) | (low_sum & 255)


static func apply_after_original_7d4c(master_ram: PackedByteArray,
                                      original_ix: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    assert((State.get8(master_ram,original_ix + 0x5C) & 2) == 0)

    var updated: PackedByteArray = master_ram.duplicate()
    var old_y: int = State.get16(updated,0xE72B)
    var old_x: int = State.get16(updated,0xE735)
    var target_y: int = State.get16(updated,original_ix + 0x65)
    var target_x: int = State.get16(updated,original_ix + 0x67)
    var new_y: int = (old_y + _project((target_y - old_y) & 65535,0x10)) & 65535
    var new_x: int = (old_x + _project((target_x - old_x) & 65535,0x10)) & 65535
    State._set16(updated,0xE72B,new_y)
    State._set16(updated,0xE735,new_x)

    # Original 7DBB–7DE8: (E93B<<8 - E767) projection with factor 0C,
    # then write the SAME word to both E767 and E769.
    var prior_heading: int = State.get16(updated,0xE767)
    var target_heading: int = State.get8(updated,0xE93B) << 8
    var new_heading: int = (prior_heading +
        _project((target_heading - prior_heading) & 65535,0x0C)) & 65535
    State._set16(updated,0xE767,new_heading)
    State._set16(updated,0xE769,new_heading)

    # Original 7DE9–7E35: two distinct decay calculations, NOT a
    # shared arbitrary friction factor or frame-time integration.
    var old_motion: int = State.get16(updated,0xE76B)
    var old_speed: int = State.get16(updated,0xE765)
    var new_motion: int = (old_motion - _project(old_motion,0x0C)) & 65535
    var new_speed: int = (old_speed - _project(old_speed,0x0C)) & 65535
    State._set16(updated,0xE76B,new_motion)
    State._set16(updated,0xE765,new_speed)

    return {
        "ram": updated,
        "branch": "smooth_7024",
        "next_pc": NORMAL_CALL_RETURN,
        "complete": true,
        "y": new_y,
        "x": new_x,
        "e767": new_heading,
        "e769": new_heading,
        "e76b": new_motion,
        "e765": new_speed,
        "original_return_continuation": "7024 JP 7572 (geometry only)"
    }
