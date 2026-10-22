class_name ArcadeCallbackLinked85B4
extends RefCounted

## Original Z80 1783 + 85B4..85D7 linked per-car state record.
## Bounded to E000–FFFF real master RAM; missing CPU reads stop at
## the original instruction. Private opcode parity 100,000 exact cases.
## Also connects 2EAF → 85B4 → original 2EC7 BIT0 branch when possible.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const First2EAF = preload("res://scripts/mechanics/ArcadeCallbackFirst2EAF.gd")


static func _available(address: int) -> bool:
    return address >= 0xE000 and address <= 0xFFFF


static func original_85b4(master_ram: PackedByteArray, original_ix: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var out: PackedByteArray = master_ram.duplicate()
    var iy: int = State.get16(out, original_ix + 0x7C)
    var record: int = (iy + 0x1D) & 0xFFFF
    if not _available(record):
        return _stop(out, 0x85B7, iy, -1, "requires_iy_record")
    if State.get8(out, record) >= State.get8(out, original_ix + 0x04):
        return _stop(out, 0x2EC7, iy, -1, "ret_nc", true)

    State._set8(out, original_ix + 0x7E,
        State.get8(out, original_ix + 0x7E) ^ 0x10)
    var ptr_low: int = (iy + 0x1E) & 0xFFFF
    var ptr_high: int = (iy + 0x1F) & 0xFFFF
    if not _available(ptr_low) or not _available(ptr_high):
        return _stop(out, 0x85C6, iy, -1, "requires_iy_pointer")
    var hl: int = (
        (State.get8(out, ptr_low) | (State.get8(out, ptr_high) << 8)) + 1
    ) & 0xFFFF
    State._set8(out, ptr_high, (hl >> 8) & 255)
    State._set8(out, ptr_low, hl & 255)
    if not _available(hl):
        return _stop(out, 0x85D3, iy, hl, "requires_cpu_read")
    State._set8(out, record, State.get8(out, hl))
    return _stop(out, 0x2EC7, iy, hl, "ret_full", true)


static func _stop(ram: PackedByteArray, pc: int, iy: int, hl: int,
                  branch: String, returned: bool = false) -> Dictionary:
    return {
        "ram": ram, "next_pc": pc, "iy": iy, "hl": hl,
        "branch": branch, "returned_to_2ec7": returned,
        "complete": returned,
        "unverified_downstream": (
            "original continuation from 2EC7" if returned else
            "unavailable original CPU hardware memory view")
    }


static func original_2eaf_through_85b4(
        master_ram: PackedByteArray, original_ix: int) -> Dictionary:
    var first: Dictionary = First2EAF.run_original_2eaf(master_ram, original_ix)
    if first["next_pc"] != 0x85B4:
        var skipped: Dictionary = first.duplicate()
        skipped["original_2eaf"] = first
        skipped["original_85b4"] = {}
        return skipped
    var linked: Dictionary = original_85b4(first["ram"], original_ix)
    var result: Dictionary = linked.duplicate()
    result["original_2eaf"] = first
    result["original_85b4"] = linked
    if not linked["returned_to_2ec7"]:
        return result
    # Original master 2EC7 BIT0,(IX+31): skip CALL 22B8 when set.
    if (State.get8(result["ram"], original_ix + 0x31) & 1) != 0:
        result["next_pc"] = 0x2ED0
        result["branch"] = "post_callback_skip_22b8"
    else:
        result["next_pc"] = 0x22B8
        result["branch"] = "post_callback_call_22b8"
    result["complete"] = false
    result["unverified_downstream"] = "original 2ED0 continuation or 22B8 callback"
    return result
