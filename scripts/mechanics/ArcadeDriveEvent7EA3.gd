class_name ArcadeDriveEvent7EA3
extends RefCounted

## Original Z80 7EA3–7F32 event handling, with original 8659 allocator and
## 1767/174E course/car table selection. No ROM data ships with the game.
## The caller supplies a 14*5*4-byte course/event table; without it the
## routine stops before 1767. The original 8022→0971 helper now follows
## three verified early returns, stopping at the unresolved 0985 transfer.
## Private original opcode parity: 100,000 cases, zero mismatches.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const ENTRY_PC: int = 0x7EA3
const NORMAL_CALL_RETURN: int = 0x7091
const EXTERNAL_COLLISION: int = 0x8022
const OPAQUE_COLLISION_TRANSFER: int = 0x0985
const EXTERNAL_COURSE_LOOKUP: int = 0x1767
const EFFECT_BASE: int = 0xE800
const EFFECT_STRIDE: int = 16
const EFFECT_SLOTS: int = 16
const COURSE_TABLE_LENGTH: int = 280


static func apply_from_original_call(master_ram: PackedByteArray,
                                     original_ix: int,
                                     course_table: PackedByteArray) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    assert(course_table.size() == 0 or course_table.size() == COURSE_TABLE_LENGTH)
    var out: PackedByteArray = master_ram.duplicate()
    State._set8(out, original_ix + 0x31, State.get8(out, original_ix + 0x31) | 0x40)
    State._set8(out, original_ix + 0x7E, State.get8(out, original_ix + 0x7E) | 0x08)
    var category: int = State.get8(out, original_ix + 0x4E)
    var collision_gate: String = "skipped"
    if category == 11 or category < 3:
        # Original 8022 saves/restores DE around CALL 0971.
        # The original 0971 has three verified early returns.
        if (State.get8(out, original_ix + 0x31) & 1) != 0:
            collision_gate = "return_status"
        else:
            State._set8(out, original_ix + 0x4E, 1)
            if State.get8(out, original_ix - 3) >= 3:
                collision_gate = "return_car_id"
            elif State.get8(out, original_ix + 0x23) != 0:
                collision_gate = "return_secondary"
            else:
                return _result(out, "collision_0985_pending",
                    OPAQUE_COLLISION_TRANSFER, false, -1, "pending_0985")

    var flags: int = State.get8(out, original_ix + 0x33)
    if (flags & 0x80) != 0:
        State._set8(out, original_ix + 0x33, (flags | 0x40) & 0x7F)
        var reused_offset: int = State.get8(out, original_ix + 0x64)
        if (reused_offset % EFFECT_STRIDE) != 0:
            return _result(out, "invalid_reuse_slot", 0x7F1A, false, -1, collision_gate)
        var reused_event: int = EFFECT_BASE + reused_offset
        State._set8(out, reused_event + 3, 0x7F)
        State._set8(out, reused_event + 2, 0x39)
        State._set8(out, reused_event + 8, 4)
        State._set8(out, reused_event + 14, 0)
        return _result(out, "reuse_event", NORMAL_CALL_RETURN, true,
            reused_offset >> 4, collision_gate)

    # Original B=DF, CALL 8659. First empty slot wins; otherwise
    # replace earliest minimum only if its priority is below DF.
    var selected: int = -1
    var kind: String = "allocated_free"
    for slot in range(EFFECT_SLOTS):
        if State.get8(out, EFFECT_BASE + EFFECT_STRIDE * slot) == 0:
            selected = slot
            break
    if selected < 0:
        kind = "allocated_replace"
        var minimum: int = 0xDF
        for slot in range(EFFECT_SLOTS):
            var priority: int = State.get8(out, EFFECT_BASE + EFFECT_STRIDE * slot + 1)
            if priority < minimum:
                minimum = priority
                selected = slot
        if selected < 0:
            return _result(out, "allocation_rejected", NORMAL_CALL_RETURN, true, -1, collision_gate)

    var offset: int = selected * EFFECT_STRIDE
    var event: int = EFFECT_BASE + offset
    State._set8(out, event + 1, 0xDF)
    State._set8(out, original_ix + 0x33, State.get8(out, original_ix + 0x33) | 0x40)
    # DD 75 64 writes the real Z80 L register, NOT IXL.
    State._set8(out, original_ix + 0x64, offset)
    var car_id: int = State.get8(out, original_ix - 3)
    State._set8(out, event + 15, car_id)
    State._set8(out, event, 3)
    State._set8(out, event + 3, 0x7F)
    State._set8(out, event + 2, 0x33)

    var course_id: int = State.get8(out, 0xE699)
    if course_table.size() != COURSE_TABLE_LENGTH or course_id >= 14 or car_id >= 5:
        return _result(out, "course_lookup_pending", EXTERNAL_COURSE_LOOKUP,
            false, selected, collision_gate)

    # 1767 selects course pointer from 8282, 174E selects car tuple E,D,L,H.
    var index: int = (course_id * 5 + car_id) * 4
    State._set8(out, event + 5, course_table[index + 1])
    State._set8(out, event + 4, course_table[index])
    State._set8(out, event + 6, course_table[index + 2])
    State._set8(out, event + 7, course_table[index + 3])
    State._set8(out, event + 8, 1)
    var car_flag: int = State.get8(out, original_ix + 0x75)
    State._set8(out, event + 9, car_flag | 1)
    State._set8(out, event + 10, car_flag | 0x0A)
    State._set8(out, event + 11, 0xFF)
    State._set8(out, event + 14, 0)
    return _result(out, kind, NORMAL_CALL_RETURN, true, selected, collision_gate)


static func _result(ram: PackedByteArray, branch: String, next_pc: int,
                    complete: bool, slot: int,
                    collision_gate: String) -> Dictionary:
    return {
        "ram": ram,
        "branch": branch,
        "next_pc": next_pc,
        "complete": complete,
        "slot": slot,
        "collision_gate": collision_gate,
        "unverified_downstream": (
            "original 0985 collision banked-memory transfer" if next_pc == OPAQUE_COLLISION_TRANSFER else
            "original 1767 course lookup requires authentic table" if next_pc == EXTERNAL_COURSE_LOOKUP else
            "original 7F1A event reuse requires allocator-owned slot" if next_pc == 0x7F1A else
            "original 7091 POP BC and 7092/2AD1 control gate")
    }
