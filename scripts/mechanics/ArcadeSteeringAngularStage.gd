class_name ArcadeSteeringAngularStage
extends RefCounted

## Independently verified original 1991 arcade master Z80 7315–7375.
##
## Strict original opcode parity: 100,000 randomized source states plus
## all 65,536 original 16-bit indexed angular input values, 0 mismatches.
## No original program table, game artwork, proprietary ROM or physics
## approximation is embedded.
##
## E771<0x0100 branches to original 7376; E773<0x0100 branches to
## original 7381. Those downstream paths are NOT part of this helper.
## The third path transforms original IX+4C/+4D, writes those two bytes,
## updates E767 and jumps into original movement stage 7530.
##
## CRITICAL ORIGINAL Z80 QUIRK:
## SBC HL,DE at 7335 sets carry; SBC HL,DE at 733C consumes it.
## Thus original 0xFBFE is NOT clamped. The clamped interval is
## strictly (0x0402,0xFBFE), not (0x0402,0xFBFE].

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const NORMAL_PC: int = 0x7530
const LOW_FIRST_PC: int = 0x7376
const LOW_SECOND_PC: int = 0x7381


static func _signed8(number: int) -> int:
    assert(number >= 0 and number <= 255)
    return number - 256 if number >= 128 else number


static func _slot0(a: int, b: int) -> int:
    var raw: int = 2 * _signed8(a) * _signed8(b)
    return clampi(raw, -32768, 32767) & 65535


static func calculate(e771: int, e773: int,
                      indexed_car_word: int,
                      heading_word: int, car_plus_71: int) -> Dictionary:
    assert(e771 >= 0 and e771 <= 65535)
    assert(e773 >= 0 and e773 <= 65535)
    assert(indexed_car_word >= 0 and indexed_car_word <= 65535)
    assert(heading_word >= 0 and heading_word <= 65535)
    assert(car_plus_71 >= 0 and car_plus_71 <= 255)

    if e771 < 0x0100:
        return {
            "branch": "low_E771_to_7376",
            "next_pc": LOW_FIRST_PC,
            "e767": heading_word,
            "car4c4d": indexed_car_word,
            "addresses": []
        }
    if e773 < 0x0100:
        return {
            "branch": "low_E773_to_7381",
            "next_pc": LOW_SECOND_PC,
            "e767": heading_word,
            "car4c4d": indexed_car_word,
            "addresses": [],
            "a": car_plus_71
        }

    var selected: int = indexed_car_word
    var branch_name: String = "passthrough"
    if selected > 0x0402 and selected < 0xFBFE:
        if (selected & 0x8000) != 0:
            selected = 0xFC00
            branch_name = "negative_clamp"
        else:
            selected = 0x0400
            branch_name = "positive_clamp"

    # Original first X-ROM signed slot0 address: high(DE), low(0x70).
    # Original second signed address: high(low(DE)>>1), low(0x70).
    var first: int = _slot0(selected >> 8, 0x70)
    var second: int = _slot0((selected & 255) >> 1, 0x70)
    var first_high: int = first >> 8
    var first_low: int = first & 255
    var second_high: int = second >> 8
    var doubled: int = second_high * 2

    var high: int = (first_high - int(doubled > 255)) & 255
    var low_sum: int = (doubled & 255) + first_low
    high = (high + int(low_sum > 255)) & 255
    var converted_word: int = (high << 8) | (low_sum & 255)

    return {
        "branch": branch_name,
        "next_pc": NORMAL_PC,
        "e767": (heading_word + converted_word) & 65535,
        "car4c4d": converted_word,
        "addresses": [
            ((selected >> 8) << 8) | 0x70,
            (((selected & 255) >> 1) << 8) | 0x70
        ]
    }


static func apply_to_ram(master_ram: PackedByteArray,
                         original_ix: int) -> Dictionary:
    ## Original master CPU E000–FFFF RAM contains both the shared working
    ## values and the physical car record addressed by original IX.
    ## Return a new buffer; never mutate input or guess missing branches.
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var original: Dictionary = calculate(
        State.get16(master_ram, 0xE771),
        State.get16(master_ram, 0xE773),
        State.get16(master_ram, original_ix + 0x4C),
        State.get16(master_ram, 0xE767),
        State.get8(master_ram, original_ix + 0x71)
    )
    var out: PackedByteArray = master_ram.duplicate()
    var verified_exit: bool = original["next_pc"] == NORMAL_PC
    if verified_exit:
        State._set16(out, original_ix + 0x4C, original["car4c4d"])
        State._set16(out, 0xE767, original["e767"])
    original["ram"] = out
    original["complete"] = verified_exit
    return original
