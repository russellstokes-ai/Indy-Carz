class_name ArcadeCarRecord
extends RefCounted

## Byte-exact storage for one original 1991 Indy Heat arcade car record.
## Five 256-byte physical records occupy original RAM E000,E100,E200,
## E300,E400; the Z80's IX pointers are E080,E180,E280,E380,E480.
## The IX pointer is therefore exactly 0x80 bytes INTO each slot.
## All constants below are PHYSICAL offsets from slot start E000+i*0x100,
## NOT the displacements encoded by original Z80 instructions.
## Three human controls map to the first three of five racing records.
##
## This is a compatibility data structure, not a new vehicle physics engine.
## Offsets below are recovered from original master-Z80 instructions and
## intentionally leave unknown fields unlabelled until they are traced.

const RECORD_LENGTH: int = 0x100
const CAR_BASES: Array[int] = [0xE080, 0xE180, 0xE280, 0xE380, 0xE480]
const ORIGINAL_PLAYER_COUNT: int = 3

const IX_BIAS_IN_PHYSICAL_SLOT: int = 0x80
# Recovered original IX+54, IX+57, IX+58, IX+59:
const FIELD_WEIGHTED_DRIVE_BIAS: int = 0xD4
const FIELD_PEDAL_RESPONSE: int = 0xD7
const FIELD_PEDAL_FACTOR: int = 0xD8
const FIELD_PEDAL_BIAS: int = 0xD9
# Original fixed input routine 0D6A writes IX+7A and sometimes IX+79:
const FIELD_STEERING_PRIMARY: int = 0xF9
const FIELD_STEERING_SAMPLE: int = 0xFA
const FIELD_STEERING_STATE: int = 0xFB
# Original 67AD changes bit 1 of IX+32:
const FIELD_PEDAL_TIMEOUT_FLAG: int = 0xB2

var _record: PackedByteArray = PackedByteArray()


func _init(initial_data: PackedByteArray = PackedByteArray()) -> void:
    if initial_data.size() == RECORD_LENGTH:
        _record = initial_data.duplicate()
    else:
        assert(initial_data.is_empty(), "Expected one original 0x100-byte car record")
        _record.resize(RECORD_LENGTH)
        _record.fill(0)


func read_u8(offset: int) -> int:
    assert(offset >= 0 and offset < RECORD_LENGTH, "Car field offset out of range")
    return _record[offset]


func read_i8(offset: int) -> int:
    var value: int = read_u8(offset)
    return value - 256 if value >= 128 else value


func write_u8(offset: int, value: int) -> void:
    assert(offset >= 0 and offset < RECORD_LENGTH, "Car field offset out of range")
    _record[offset] = value & 0xFF


func set_bit(offset: int, bit: int) -> void:
    assert(bit >= 0 and bit < 8, "Original car state flags are 8-bit")
    write_u8(offset, read_u8(offset) | (1 << bit))


func snapshot_bytes() -> PackedByteArray:
    # Never return a mutable alias to live simulation state.
    return _record.duplicate()


static func racer_ram_base(index: int) -> int:
    assert(index >= 0 and index < CAR_BASES.size(), "Only five original racers")
    return CAR_BASES[index]


static func ix_displacement_to_slot_offset(signed_displacement: int) -> int:
    # Original Z80 indexed offsets are signed [-128,+127].
    # Examples: IX+0x57 -> slot+0xD7; IX-0x3F -> slot+0x41.
    assert(signed_displacement >= -128 and signed_displacement <= 127)
    return signed_displacement + IX_BIAS_IN_PHYSICAL_SLOT


static func racer_slot_start(index: int) -> int:
    return racer_ram_base(index) - IX_BIAS_IN_PHYSICAL_SLOT

