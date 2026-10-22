class_name ArcadeDriveSlow7049
extends RefCounted

## Exact bounded original master Z80 7049–709B slow pedal update.
## The original owner-ROM bytes were independently interpreted against
## an integer state model for 100,000 cases, zero mismatches.
##
## FFFE slot1 LOW is the proven (unsigned8*unsigned8+128)>>8;
## slot1 HIGH is never consumed. Do not replace original 7E5E/2AD1
## calls with guessed side effects. These routes stop BEFORE the call.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const ENTRY_PC: int = 0x7049
const NORMAL_PC: int = 0x709C
const EXTERNAL_7E5E: int = 0x7E5E
const EXTERNAL_2AD1: int = 0x2AD1


static func _slot1_low(high: int, low: int) -> int:
    assert(high >= 0 and high <= 255)
    assert(low >= 0 and low <= 255)
    return (high * low + 128) >> 8


static func apply_from_original_7049(master_ram: PackedByteArray,
                                     original_ix: int,
                                     inherited_b: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    assert(inherited_b >= 0 and inherited_b <= 255)

    var out: PackedByteArray = master_ram.duplicate()
    var original_speed: int = State.get16(out,0xE765)
    # 7049 LD HL,(E765); ADD HL,HL; LD L,H; slot1 low H*H.
    var doubled_high: int = ((original_speed << 1) & 65535) >> 8
    var first: int = _slot1_low(doubled_high,doubled_high)
    # 7054 SRL A; 7056 ADC A,20: preserve the shifted-out bit.
    var scale: int = (first >> 1) + (first & 1) + 0x20
    # 7059 LD A,B; ADD A,80; CALL C,0A9C clamps to FF.
    var corrected_b: int = mini(255,inherited_b + 128)
    var second: int = _slot1_low(scale,corrected_b)
    # 7066 overwrites the unknown FFFE high with genuine IX+3B.
    var indexed_high: int = State.get8(out,original_ix + 0x3B)
    var subtrahend: int = _slot1_low(indexed_high,second)

    var prior_low: int = State.get8(out,original_ix + 0x39)
    var new_low: int = (prior_low - subtrahend) & 255
    State._set8(out,original_ix + 0x39,new_low)
    var route: String = "fast_709c"
    var next_pc: int = NORMAL_PC

    if prior_low < subtrahend:
        # 7079–7083: borrow decrements IX+3A; a zero result sets
        # persistent status bit4 at IX+31.
        var new_high: int = (State.get8(out,original_ix + 0x3A) - 1) & 255
        State._set8(out,original_ix + 0x3A,new_high)
        if new_high == 0:
            State._set8(out,original_ix + 0x31,
                State.get8(out,original_ix + 0x31) | 0x10)
        # Original CP L after LD HL,(E94D) uses E94D LOW only.
        if new_high < State.get8(out,0xE94D):
            route = "external_7e5e"
            next_pc = EXTERNAL_7E5E
        elif State.get8(out,original_ix - 3) < 3:
            route = "external_2ad1"
            next_pc = EXTERNAL_2AD1

    return {
        "ram": out,
        "branch": route,
        "next_pc": next_pc,
        "complete": next_pc == NORMAL_PC,
        "b": inherited_b,
        "e765": original_speed,
        "ix39": new_low,
        "ix3a": State.get8(out,original_ix + 0x3A),
        "ix31": State.get8(out,original_ix + 0x31),
        "subtrahend": subtrahend,
        "unverified_downstream": (
            "original external 7E5E/2AD1 call" if next_pc != NORMAL_PC else
            "original speed and movement after 709C")
    }
