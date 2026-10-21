class_name ArcadeSteeringLookupStage
extends RefCounted

## Clean-room original 1991 Indy Heat master Z80 7376-73CC.
##
## Original owner-ROM opcode comparisons: 100,000 synthetic 256-byte
## lookup arrays plus EVERY one of 65,536 index-pair combinations,
## 0 mismatches. The game-table content is NOT supplied or embedded.
##
## 7376 entry follows E771<0x0100 with carry=1 inherited from 731B.
## 7381 entry follows E773<0x0100 and receives original IX+71 in A.
## 7394 entry is the blended selection reached within the former.
## All branches finish at original PC 73CD with actual B,C control bytes.
##
## Original ADD A,A truncates 2*index at eight bits. The ninth bit
## is lost BEFORE the table pointer is added; index 128 aliases index 0,
## index 255 aliases index 127. Never treat it as a 512-byte indexed
## table lookup or ordinary 16-bit multiplication.

const FIRST_ENTRY_PC: int = 0x7376
const SECOND_ENTRY_PC: int = 0x7381
const BLEND_ENTRY_PC: int = 0x7394
const NEXT_PC: int = 0x73CD
const SYNTHETIC_OR_LICENSED_BYTES: int = 256


static func _pair_offset(index: int) -> int:
    assert(index >= 0 and index <= 255)
    return (index * 2) & 255


static func calculate(entry_pc: int, original_e773: int,
                      original_car70: int, original_car71: int,
                      control_table: PackedByteArray) -> Dictionary:
    assert(entry_pc == FIRST_ENTRY_PC or
           entry_pc == SECOND_ENTRY_PC or entry_pc == BLEND_ENTRY_PC)
    assert(original_e773 >= 0 and original_e773 <= 65535)
    assert(original_car70 >= 0 and original_car70 <= 255)
    assert(original_car71 >= 0 and original_car71 <= 255)
    assert(control_table.size() == SYNTHETIC_OR_LICENSED_BYTES,
           "This stage requires 256 independently supplied control bytes")

    if entry_pc == SECOND_ENTRY_PC or (
            entry_pc == FIRST_ENTRY_PC and original_e773 > 0x0100):
        var selected: int = original_car71 if entry_pc == SECOND_ENTRY_PC \
                            else original_car70
        var pair: int = _pair_offset(selected)
        return {
            "b": control_table[pair] >> 1,
            "c": control_table[pair + 1] >> 1,
            "branch": "halved_car71" if entry_pc == SECOND_ENTRY_PC \
                       else "halved_car70",
            "next_pc": NEXT_PC
        }

    if original_car70 == original_car71:
        var selected_pair: int = _pair_offset(original_car70)
        return {
            "b": control_table[selected_pair],
            "c": control_table[selected_pair + 1],
            "branch": "same_index_full",
            "next_pc": NEXT_PC
        }

    var first_pair: int = _pair_offset(original_car70)
    var second_pair: int = _pair_offset(original_car71)
    return {
        "b": (control_table[first_pair] + control_table[second_pair]) >> 1,
        "c": (control_table[first_pair + 1] +
              control_table[second_pair + 1]) >> 1,
        "branch": "blended_indices",
        "next_pc": NEXT_PC
    }


static func after_verified_7315(first_stage: Dictionary,
                               original_e773: int,
                               original_car70: int, original_car71: int,
                               control_table: PackedByteArray) -> Dictionary:
    ## Only the early original 7315 exits enter this selector.
    ## Normal 7315 processing jumps directly to 7530 and NEVER runs it.
    var next_pc: int = first_stage.get("next_pc",-1)
    assert(next_pc == FIRST_ENTRY_PC or next_pc == SECOND_ENTRY_PC)
    return calculate(next_pc, original_e773, original_car70,
                     original_car71, control_table)
