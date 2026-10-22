class_name ArcadeCallbackFirst2EAF
extends RefCounted

## Original bank0 2EAF–2EC6 per-car callback initialization.
## Direct original opcode parity: 100,000 cases, zero mismatches.
## First external original call 85B4 is a strict stop.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")


static func run_original_2eaf(master_ram: PackedByteArray,
                               original_ix: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var out: PackedByteArray = master_ram.duplicate()
    if (State.get8(out, original_ix + 0x33) & 0x02) != 0:
        return {
            "ram": out, "next_pc": 0x2EB3, "branch": "return_if_disabled",
            "return_to_caller": true, "complete": true
        }
    State._set8(out, original_ix + 0x7E,
        State.get8(out, original_ix + 0x7E) & 0xFD)
    State._set8(out, original_ix + 0x1E,
        State.get8(out, original_ix + 0x1E) & 0xFE)
    State._set8(out, original_ix + 0x10, 0)
    State._set8(out, original_ix + 0x56, 0xFF)
    return {
        "ram": out, "next_pc": 0x85B4, "call_site_pc": 0x2EC4,
        "branch": "call_85b4", "return_to_caller": false,
        "complete": false,
        "unverified_downstream": "original 85B4 callback side effects"
    }
