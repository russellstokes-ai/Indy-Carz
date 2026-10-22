class_name ArcadeCollisionTranslation
extends RefCounted

## Original 1991 arcade master Z80 fixed BE0D..BE67 collision-geometry
## translation, independently verified on the user's private ROM.
##
## 100,000 actual original Z80 opcode comparisons, zero mismatches.
## These 16-bit position/geometry adjustments are NOT an invented force
## or traction rule. The surrounding full collision handling is unresolved.
## A caller must establish the authentic original execution context.
##
## Input is the 8192-byte E000..FFFF master RAM working-state view.
## This is a pure function: the input buffer is never modified.

const Retry = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const ORIGINAL_EXIT_PC: int = 0xBCA5
const ORIGINAL_X_WORDS: Array[int] = [0xE72D, 0xE72F, 0xE733, 0xE72B]
const ORIGINAL_Y_WORDS: Array[int] = [0xE737, 0xE739, 0xE73D, 0xE735]


static func apply(memory: PackedByteArray) -> Dictionary:
    assert(memory.size() == Retry.LENGTH, "Original master RAM must be E000..FFFF")
    var result: PackedByteArray = memory.duplicate()

    # Z80 LD HL,(E98D); LD DE,(E731); LD (E731),HL; OR A;
    # SBC HL,DE. Both subtraction and addition wrap at 16 bits.
    var original_x: int = Retry.get16(result, 0xE731)
    var target_x: int = Retry.get16(result, 0xE98D)
    var delta_x: int = (target_x - original_x) & 0xFFFF
    Retry._set16(result, 0xE731, target_x)
    if delta_x != 0:
        for address in ORIGINAL_X_WORDS:
            var existing: int = Retry.get16(result, address)
            Retry._set16(result, address, (existing + delta_x) & 0xFFFF)

    var original_y: int = Retry.get16(result, 0xE73B)
    var target_y: int = Retry.get16(result, 0xE98F)
    var delta_y: int = (target_y - original_y) & 0xFFFF
    Retry._set16(result, 0xE73B, target_y)
    if delta_y != 0:
        for address in ORIGINAL_Y_WORDS:
            var existing: int = Retry.get16(result, address)
            Retry._set16(result, address, (existing + delta_y) & 0xFFFF)

    return {
        "ram": result,
        "delta_x": delta_x,
        "delta_y": delta_y,
        "x_branch": delta_x != 0,
        "y_branch": delta_y != 0,
        "next_pc": ORIGINAL_EXIT_PC
    }
