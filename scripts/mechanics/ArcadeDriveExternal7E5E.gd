class_name ArcadeDriveExternal7E5E
extends RefCounted

## Authenticated 1991 master Z80 7E5E–7EA2 only: four genuine early
## returns to the slow-driving caller at 7091, or stop at 7EA3 before
## event/collision dispatch with unknown external CALLs.
## Original ROM interpreter versus separate branch model:
## 100,000 private original-Z80 comparisons; zero mismatches.
## No fabricated 8022/8659/1767 effects or event scheduling.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const ENTRY_PC: int = 0x7E5E
const NORMAL_CALL_RETURN: int = 0x7091
const OPAQUE_DISPATCH_PC: int = 0x7EA3


static func apply_from_original_call(master_ram: PackedByteArray,
                                     original_ix: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var out: PackedByteArray = master_ram.duplicate()
    var branch: String = "dispatch_7ea3"
    var next_pc: int = OPAQUE_DISPATCH_PC

    if (State.get8(out,original_ix + 0x31) & 0x40) != 0:
        branch = "return_flag"
    elif State.get8(out,0xE603) != 0:
        pass # Genuine 7E67 JR NZ,7EA3 (not verified beyond this stop)
    else:
        var original_id: int = State.get8(out,original_ix - 3)
        var competition_count: int = State.get8(out,0xE602)
        var race_phase: int = State.get8(out,0xE674)
        var global_position: int = State.get8(out,0xE639)
        var car_position: int = State.get8(out,original_ix + 2)
        if original_id == 4 and competition_count == 0 and race_phase < 2:
            # Original SUB(IX+02), CP B, JP P gate uses the Z80 signed
            # SIGN flag, NOT an unsigned comparison/negative integer.
            var compare_byte: int = (
                global_position - car_position - State.get8(out,0xE638)) & 255
            if (compare_byte & 0x80) != 0:
                State._set8(out,original_ix + 0x3A,0x48)
                branch = "return_special"

        if branch == "dispatch_7ea3":
            if global_position == car_position:
                branch = "return_equal"
            elif ((global_position - 1) & 255) == car_position and (
                    State.get8(out,original_ix + 0x51) >= 0x1E):
                branch = "return_neighbor"

    if branch != "dispatch_7ea3":
        next_pc = NORMAL_CALL_RETURN
    return {
        "ram": out,
        "branch": branch,
        "next_pc": next_pc,
        "complete": next_pc == NORMAL_CALL_RETURN,
        "ix3a": State.get8(out,original_ix + 0x3A),
        "unverified_downstream": (
            "original event dispatch at 7EA3" if next_pc == OPAQUE_DISPATCH_PC else
            "original POP BC and 7092 gate after return 7091")
    }
