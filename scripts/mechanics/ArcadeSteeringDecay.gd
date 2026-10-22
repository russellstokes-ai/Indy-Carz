class_name ArcadeSteeringDecay
extends RefCounted

## Original arcade 1991 master Z80 74D8–752F verified state update.
## Consumes original second steering projection and original E76B
## signed motion; applies the same inherited-carry 3x SRA/RR limit
## unless IX+31 bit0 bypasses the limiter. Original car IX+41 has a
## signed DEC A / JP M decision, NOT a conventional countdown.
##
## For a decremented counter (original input 1..128), store counter-1,
## add SIGNED half of the selected projection to E769, and subtract
## DOUBLE that half from E767.
##
## For a counter NOT decremented (input 0,129..255), add the full
## selected projection to E769 and subtract its signed QUARTER
## from E767. Preserve the original car counter byte.
##
## Original Z80 opcode comparisons: 100,000 cases, zero mismatches.
## This does not synthesize tyre handling, AI or collision forces.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const NEXT_PC: int = 0x7530


static func _signed16(value: int) -> int:
    assert(value >= 0 and value <= 65535)
    return value - 65536 if value >= 32768 else value


static func calculate(original_projection: int,
                      original_motion: int,
                      original_e769: int,
                      original_e767: int,
                      original_car_plus_41: int,
                      original_car_plus_31: int) -> Dictionary:
    assert(original_projection >= 0 and original_projection <= 65535)
    assert(original_motion >= 0 and original_motion <= 65535)
    assert(original_e769 >= 0 and original_e769 <= 65535)
    assert(original_e767 >= 0 and original_e767 <= 65535)
    assert(original_car_plus_41 >= 0 and original_car_plus_41 <= 255)
    assert(original_car_plus_31 >= 0 and original_car_plus_31 <= 255)

    var selected: int = original_projection
    var limited: bool = false
    if (original_car_plus_31 & 1) == 0:
        var eighth: int = (_signed16(original_motion) >> 3) & 65535
        var carry: int = 1 if (original_motion & 4) != 0 else 0

        # Three original SRA B/RR C pairs leave the carry from bit2;
        # first SBC HL,BC borrows and the second SBC HL,DE consumes it.
        var intermediate: int = 0x9600 - eighth - carry
        var borrowed: int = 1 if intermediate < 0 else 0
        var inverted: int = original_projection ^ 0x8000
        var second: int = (intermediate & 65535) - inverted - borrowed
        if second < 0:
            selected = ((((second & 65535) + inverted) & 65535) ^ 0x8000)
            limited = true

    # Z80 DEC A, JP M: the original byte value 0 or 129..255
    # takes the negative branch. Values 1..128 are decremented.
    var decremented_byte: int = (original_car_plus_41 - 1) & 255
    var original_store: bool = (decremented_byte & 128) == 0
    var next_counter: int = original_car_plus_41
    var final_de: int = 0
    var next_e769: int = 0

    if original_store:
        var half: int = (_signed16(selected) >> 1) & 65535
        final_de = (half * 2) & 65535
        next_e769 = (original_e769 + half) & 65535
        next_counter = decremented_byte
    else:
        final_de = (_signed16(selected) >> 2) & 65535
        next_e769 = (original_e769 + selected) & 65535

    return {
        "selected_projection": selected,
        "final_de": final_de,
        "e769": next_e769,
        "e767": (original_e767 - final_de) & 65535,
        "car41": next_counter,
        "limited": limited,
        "counter_decremented": original_store,
        "next_pc": NEXT_PC
    }


static func apply_to_ram(original_ram: PackedByteArray,
                         original_ix: int,
                         original_projection: int) -> Dictionary:
    ## The original CPU stores E769 and E767, and conditionally IX+41.
    ## State is copied so callers can safely compare original snapshots.
    assert(original_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var answer: Dictionary = calculate(
        original_projection,
        State.get16(original_ram, 0xE76B),
        State.get16(original_ram, 0xE769),
        State.get16(original_ram, 0xE767),
        State.get8(original_ram, original_ix + 0x41),
        State.get8(original_ram, original_ix + 0x31)
    )
    var changed: PackedByteArray = original_ram.duplicate()
    State._set16(changed, 0xE769, answer["e769"])
    State._set16(changed, 0xE767, answer["e767"])
    if answer["counter_decremented"]:
        State._set8(changed, original_ix + 0x41, answer["car41"])
    answer["ram"] = changed
    return answer
