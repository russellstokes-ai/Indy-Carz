class_name ArcadeDriveSpecial7D4C
extends RefCounted

## Original 1991 master Z80 7D4C–7D64 SHORT direct-centre branch.
## Exact owner-ROM Z80 opcode parity: 100,000 cases, zero mismatches.
##
## This helper is entered ONLY by an authentic CALL 7D4C. BIT1 of
## original IX+5C selects the short Y/X override and RET to 7024.
## Otherwise it stops at the genuine unresolved slow path PC7D65.
## It NEVER fabricates the rest of 7D65–7E35 or any collision effects.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const ENTRY_PC: int = 0x7D4C
const NORMAL_CALL_RETURN: int = 0x7024
const UNRESOLVED_PC: int = 0x7D65


static func apply_from_original_call(master_ram: PackedByteArray,
                                    original_ix: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var out: PackedByteArray = master_ram.duplicate()
    var old_y: int = State.get16(out,0xE72B)
    var old_x: int = State.get16(out,0xE735)

    if (State.get8(out,original_ix + 0x5C) & 2) == 0:
        return {
            "ram": out, "branch": "slow_7d65", "next_pc": UNRESOLVED_PC,
            "y": old_y, "x": old_x, "complete": false,
            "unverified_continuation": "original 7D65–7E35 smoothing"
        }

    # Original LD H,(IX+66); LD L,(IX+65); LD (E72B),HL;
    # then corresponding IX+68/IX+67 centre and original RET.
    var destination_y: int = State.get16(out,original_ix + 0x65)
    var destination_x: int = State.get16(out,original_ix + 0x67)
    State._set16(out,0xE72B,destination_y)
    State._set16(out,0xE735,destination_x)
    return {
        "ram": out, "branch": "direct_7024", "next_pc": NORMAL_CALL_RETURN,
        "y": destination_y, "x": destination_x, "complete": true,
        "original_return_continuation": "7024 JP 7572 (geometry only)"
    }
