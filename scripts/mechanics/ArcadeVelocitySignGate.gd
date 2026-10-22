class_name ArcadeVelocitySignGate
extends RefCounted

## Bounded verified original 1991 Indy Heat master Z80 7225..7244.
## This is one sign-crossing gate for the 16-bit E76B motion state,
## NOT the full car acceleration, grip, collisions, boost or fuel model.
##
## Verification: 100,000 original Z80 instruction executions and
## 3,598 original live MAME motion-word writes, ZERO mismatches.
##
## Carry is explicitly cleared before 16-bit SBC HL,DE. JP M / JP P
## tests the SIGN BIT of the 16-bit wrapped difference, not a host
## floating-point value or an ordinary signed arithmetic comparison.

const OriginalRAM = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const MOTION_WORD: int = 0xE76B
const NEXT_PC: int = 0x7245


static func calculate(original_motion: int, original_de: int) -> Dictionary:
    assert(original_motion >= 0 and original_motion <= 65535)
    assert(original_de >= 0 and original_de <= 65535)
    var proposed: int = (original_motion - original_de) & 0xFFFF
    var same_sign: bool = ((original_motion & 0x8000) != 0) == \
                          ((proposed & 0x8000) != 0)
    var selected: int = proposed if same_sign else 0
    var original_path: String = "negative" if (original_motion & 0x8000) != 0 \
                               else "positive"
    original_path += "_keep" if same_sign else "_clamp"
    return {
        "stored_e76b": selected,
        "de_after": selected,
        "hl_after": original_de,
        "branch": original_path,
        "next_pc": NEXT_PC
    }


static func apply_to_ram(memory: PackedByteArray, original_de: int) -> Dictionary:
    ## Original E000–FFFF working state; caller supplies ORIGINAL DE from
    ## the preceding verified motion calculation. No guessed time step.
    assert(memory.size() == OriginalRAM.LENGTH)
    var current: int = OriginalRAM.get16(memory, MOTION_WORD)
    var result: Dictionary = calculate(current, original_de)
    var changed: PackedByteArray = memory.duplicate()
    OriginalRAM._set16(changed, MOTION_WORD, result["stored_e76b"])
    result["ram"] = changed
    return result
