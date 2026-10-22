class_name ArcadeDriveEvent2AD6
extends RefCounted

## Original bank0 Z80 2AD6–2B76: stage four event words in E900–E907.
## The original ROM table is NOT bundled. Caller may provide 512 bytes
## corresponding to the original mapped 3F00–40FF memory view. Bytes
## at 4000+ may depend on the active ROM bank. Missing data stops at the
## first genuine LDI; completed staging stops at 2B77 BEFORE F4/QRAM.
## Original opcode comparisons: 100,000, zero mismatches.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const ENTRY_PC: int = 0x2AD6
const HARDWARE_CONTINUATION: int = 0x2B77
const SOURCE_BASE: int = 0x3F00
const SOURCE_LENGTH: int = 512
const SOURCE_OFFSETS = [0x3F50, 0x3F38, 0x3F20, 0x3F08]
const MISSING_SOURCE_PC = [0x2AED, 0x2B14, 0x2B3E, 0x2B63]


static func apply_from_original_2ad6(master_ram: PackedByteArray,
                                      original_ix: int,
                                      source_window: PackedByteArray) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    assert(source_window.size() == 0 or source_window.size() == SOURCE_LENGTH)
    var out: PackedByteArray = master_ram.duplicate()
    var original_value: int = State.get8(out, original_ix + 0x3A)
    var group: int = (
        0 if original_value < 12 else
        1 if original_value < 36 else
        2 if original_value < 60 else 3)
    var source_address: int = SOURCE_OFFSETS[group] + original_value
    if source_window.size() != SOURCE_LENGTH:
        return _result(out, MISSING_SOURCE_PC[group], group, false, source_address)

    # Original LDI reads source_address and source_address+25; the
    # other three event words are 0001 or 0013 depending on group.
    for word_index in range(4):
        var low: int = 1
        var high: int = 0
        if word_index < group:
            low = 0x13
        elif word_index == group:
            var source_index: int = source_address - SOURCE_BASE
            low = source_window[source_index]
            high = source_window[source_index + 25]
        State._set8(out, 0xE900 + word_index * 2, low)
        State._set8(out, 0xE901 + word_index * 2, high)
    return _result(out, HARDWARE_CONTINUATION, group, true, source_address)


static func _result(ram: PackedByteArray, next_pc: int, group: int,
                    staging_complete: bool, source_address: int) -> Dictionary:
    return {
        "ram": ram,
        "next_pc": next_pc,
        "group": group,
        "staging_complete": staging_complete,
        "complete": false,
        "source_address": source_address,
        "original_stack_word": 0x0108,
        "unverified_downstream": (
            "original 2B77 F4 bank selection and QRAM write semantics"
            if staging_complete else
            "original 2AD6 table LDI requires authentic bank0 source data")
    }
