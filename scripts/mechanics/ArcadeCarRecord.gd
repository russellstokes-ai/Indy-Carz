class_name ArcadeCarRecord
extends RefCounted

## Byte-exact storage for one original 1991 Indy Heat arcade car record.
## Five racer records occupy master shared RAM at E080,E180,E280,E380,E480,
## each separated by 0x100 bytes. Three human controls map to first three.
##
## This is a compatibility data structure, not a new vehicle physics engine.
## Offsets below are recovered from original master-Z80 instructions and
## intentionally leave unknown fields unlabelled until they are traced.

const RECORD_LENGTH: int = 0x100
const CAR_BASES: Array[int] = [0xE080, 0xE180, 0xE280, 0xE380, 0xE480]
const ORIGINAL_PLAYER_COUNT: int = 3

const FIELD_WEIGHTED_DRIVE_BIAS: int = 0x54
const FIELD_PEDAL_RESPONSE: int = 0x57
const FIELD_PEDAL_FACTOR: int = 0x58
const FIELD_PEDAL_BIAS: int = 0x59
const FIELD_STEERING_PRIMARY: int = 0x79
const FIELD_STEERING_SAMPLE: int = 0x7A
const FIELD_STEERING_STATE: int = 0x7B
const FIELD_PEDAL_TIMEOUT_FLAG: int = 0x32 # bit 1 set by original at $67AD

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
