class_name ArcadeDriveControlSelector
extends RefCounted

## Original 1991 Indy Heat master Z80 714E–71C7 selects B/C.
## Private original Z80 opcode verification: 100,000 independent input
## comparisons, zero mismatches.
##
## The *actual* table is reached through a 16-bit pointer at E96B.
## Its source bytes must be supplied by the caller from authenticated
## runtime RAM/ROM. This class embeds NO original lookup or track bytes.
##
## The original first SBC HL,DE INHERITS CARRY from the preceding
## 7148 addition. The second SBC can inherit the borrow from the first.
## Do not approximate either threshold as a standalone >=0x0100.
##
## Original indexes are multiplied by 2 as BYTE ARITHMETIC:
## indexes 128–255 alias indexes 0–127. Blend uses Z80 RRCA of the
## wrapped byte SUM rather than arithmetic averaging. Negative E76C
## overrides BOTH B and C unless 7315 was already branched to.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const Car = preload("res://scripts/mechanics/ArcadeCarRecord.gd")

const ENTRY_PC: int = 0x714E
const NEXT_DRIVE_PC: int = 0x71C8
const BYPASS_TO_STEERING_PC: int = 0x7315
const REQUIRED_SOURCE_BYTES: int = 257


static func _check_source(source: PackedByteArray) -> void:
    assert(source.size() == REQUIRED_SOURCE_BYTES,
           "Need exactly 257 authenticated original address-window bytes")


static func _pair(source: PackedByteArray, index: int) -> Vector2i:
    # Original ADD A,A is 8-bit and drops its doubling carry.
    var address: int = (index * 2) & 255
    return Vector2i(source[address], source[address + 1])


static func _rrca(value: int) -> int:
    var wrapped: int = value & 255
    return ((wrapped >> 1) | ((wrapped & 1) << 7)) & 255


static func select_bc(e76d: int, e76f: int,
                      original_ix_plus_6e: int,
                      original_ix_plus_6f: int,
                      e76c: int,
                      original_table_window: PackedByteArray,
                      incoming_b: int = 0,
                      incoming_c: int = 0,
                      inherited_carry: int = 0) -> Dictionary:
    assert(e76d >= 0 and e76d <= 65535)
    assert(e76f >= 0 and e76f <= 65535)
    assert(original_ix_plus_6e >= 0 and original_ix_plus_6e <= 255)
    assert(original_ix_plus_6f >= 0 and original_ix_plus_6f <= 255)
    assert(e76c >= 0 and e76c <= 255)
    assert(incoming_b >= 0 and incoming_b <= 255)
    assert(incoming_c >= 0 and incoming_c <= 255)
    assert(inherited_carry == 0 or inherited_carry == 1)
    _check_source(original_table_window)

    var b: int = incoming_b
    var c: int = incoming_c
    var path: String = ""
    if e76d >= 0x100 + inherited_carry:
        if e76f >= 0x100:
            return {
                "next_pc": BYPASS_TO_STEERING_PC,
                "b": b, "c": c, "path": "bypass_7315",
                "overridden": false
            }
        var direct6f: Vector2i = _pair(
            original_table_window, original_ix_plus_6f)
        b = direct6f.x >> 1
        c = direct6f.y
        path = "direct_6f"
    elif e76f >= 0x101:
        var direct6e: Vector2i = _pair(
            original_table_window, original_ix_plus_6e)
        b = direct6e.x >> 1
        c = direct6e.y
        path = "direct_6e"
    elif original_ix_plus_6e == original_ix_plus_6f:
        var same: Vector2i = _pair(
            original_table_window, original_ix_plus_6e)
        b = same.x
        c = same.y
        path = "matching_indices"
    else:
        var first: Vector2i = _pair(
            original_table_window, original_ix_plus_6e)
        var second: Vector2i = _pair(
            original_table_window, original_ix_plus_6f)
        b = _rrca((first.x + second.x) & 255)
        c = _rrca((first.y + second.y) & 255)
        path = "rotated_blend"

    var overridden: bool = (e76c & 128) != 0
    if overridden:
        b = original_table_window[0]
        c = original_table_window[1]

    return {
        "next_pc": NEXT_DRIVE_PC,
        "b": b, "c": c,
        "path": path, "overridden": overridden
    }


static func select_from_original_state(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_table_window: PackedByteArray,
        incoming_b: int = 0,
        incoming_c: int = 0,
        inherited_carry: int = 0) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    # Z80 IX is physical car slot +0x80. Actual physical offsets:
    # IX+0x6E -> slot+0xEE; IX+0x6F -> slot+0xEF.
    return select_bc(
        State.get16(master_ram, 0xE76D),
        State.get16(master_ram, 0xE76F),
        physical_car.read_u8(Car.ix_displacement_to_slot_offset(0x6E)),
        physical_car.read_u8(Car.ix_displacement_to_slot_offset(0x6F)),
        State.get8(master_ram, 0xE76C),
        original_table_window,
        incoming_b, incoming_c, inherited_carry
    )
