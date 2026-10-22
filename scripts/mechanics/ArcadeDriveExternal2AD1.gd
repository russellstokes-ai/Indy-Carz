class_name ArcadeDriveExternal2AD1
extends RefCounted

## Original Z80 2AD1–2AD5 ONLY: BIT 0,(IX+31); RET NZ.
## Original private-ROM opcode parity: 100,000 cases, zero mismatches.
## If clear, stop BEFORE original 2AD6 event/ROM bank switching.
## A return continues at original caller 709B POP BC then 709C.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const ENTRY_PC: int = 0x2AD1
const NORMAL_CALL_RETURN: int = 0x709B
const OPAQUE_DISPATCH_PC: int = 0x2AD6


static func apply_from_original_call(master_ram: PackedByteArray,
                                     original_ix: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var branch: String = "return_709b" if (
        State.get8(master_ram,original_ix + 0x31) & 1) != 0 else "dispatch_2ad6"
    var next_pc: int = NORMAL_CALL_RETURN if (
        branch == "return_709b") else OPAQUE_DISPATCH_PC
    return {
        "ram": master_ram.duplicate(),
        "branch": branch,
        "next_pc": next_pc,
        "complete": next_pc == NORMAL_CALL_RETURN,
        "unverified_downstream": (
            "original 2AD6 banked event code" if next_pc == OPAQUE_DISPATCH_PC else
            "original 709B POP BC then 709C speed")
    }
