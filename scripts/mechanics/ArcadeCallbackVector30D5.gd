class_name ArcadeCallbackVector30D5
extends RefCounted

## Original bank0 30D5–30F7 Z80 vector preparation and EXX register swap.
## Returns exact A/F/BC/DE/HL and alternate BC/DE/HL before JP D958.
## Caller must provide original incoming A and primary HL; never guess.
## Private original opcode parity: 100,000 cases, zero mismatches.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")


static func run_original_30d5(master_ram: PackedByteArray,
                               original_ix: int, incoming_a: int,
                               incoming_hl: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    assert(incoming_a >= 0 and incoming_a <= 255)
    assert(incoming_hl >= 0 and incoming_hl <= 0xFFFF)
    var out: PackedByteArray = master_ram.duplicate()
    var alt_bc: int = State.get16(out, 0xE96F)
    var alt_de: int = State.get16(out, 0xE971)
    State._set16(out, 0xE77D, alt_bc)
    State._set16(out, 0xE77F, alt_de)

    var register_c: int = (incoming_a | State.get8(out, original_ix + 0x75)) & 255
    var source_hl: int = State.get16(out, 0xE735)
    var doubled: int = source_hl << 1
    var register_hl: int = doubled & 0xFFFF
    var register_a: int = (~(register_hl >> 8)) & 255
    var parity_bits: int = 0
    var bits_remaining: int = register_c
    while bits_remaining != 0:
        parity_bits += bits_remaining & 1
        bits_remaining = bits_remaining >> 1
    # OR sets S/Z/PV; ADD HL,HL sets C; CPL sets H/N and result F3/F5.
    var register_f: int = (
        (register_c & 0x80) |
        (0x40 if register_c == 0 else 0) |
        (4 if (parity_bits % 2) == 0 else 0) |
        (1 if doubled > 0xFFFF else 0) |
        0x12 | (register_a & 0x28))
    return {
        "ram": out, "next_pc": 0xD958, "branch": "jp_d958",
        "a": register_a, "f": register_f,
        "bc": (register_a << 8) | register_c,
        "de": State.get16(out, 0xE94E), "hl": register_hl,
        "alt_bc": alt_bc, "alt_de": alt_de, "alt_hl": incoming_hl,
        "complete": false,
        "unverified_downstream": "original D958 callback renderer/dispatch"
    }
