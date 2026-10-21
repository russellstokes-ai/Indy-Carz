class_name ArcadeCollisionRetry
extends RefCounted

## Independently verified byte-state transitions for fixed Z80 BC8C/BCA5.
## The caller chooses when to invoke these. BCFA response is separate.
## Input is master RAM E000..FFFF, copied before modification.

const BASE: int = 0xE000
const LENGTH: int = 0x2000
const CAR_POINTERS = [0xE080, 0xE180, 0xE280, 0xE380, 0xE480]
const COPY_PAIRS = [
    [0xE749,0xE72B], [0xE753,0xE735], [0xE74B,0xE72D],
    [0xE74D,0xE72F], [0xE74F,0xE731], [0xE751,0xE733],
    [0xE755,0xE737], [0xE757,0xE739], [0xE759,0xE73B],
    [0xE75B,0xE73D], [0xE747,0xE767]
]

static func _check(ram: PackedByteArray, ix: int) -> void:
    assert(ram.size() == LENGTH)
    assert(CAR_POINTERS.has(ix))

static func get8(ram: PackedByteArray, address: int) -> int:
    assert(address >= BASE and address < BASE + LENGTH)
    return ram[address - BASE]

static func get16(ram: PackedByteArray, address: int) -> int:
    return get8(ram, address) | (get8(ram, address + 1) << 8)

static func _set8(ram: PackedByteArray, address: int, value: int) -> void:
    assert(address >= BASE and address < BASE + LENGTH)
    ram[address - BASE] = value & 255

static func _set16(ram: PackedByteArray, address: int, value: int) -> void:
    _set8(ram, address, value)
    _set8(ram, address + 1, value >> 8)

static func begin(ram: PackedByteArray, ix: int) -> Dictionary:
    _check(ram, ix)
    var out: PackedByteArray = ram.duplicate()
    var hl: int = get16(out, 0xE976)
    var bank: int = (get8(out, 0xE608) & 0xF0) | (hl & 255)
    _set8(out, 0xE608, bank)
    _set8(out, ix + 0x31, get8(out, ix + 0x31) & 0x7F)
    _set8(out, 0xE92E, 1)
    _set8(out, 0xE92C, 0)
    return {"ram":out,"f4":bank,"counter":1,"next_pc":0xBCFA,"words_restored":0}

static func retry(ram: PackedByteArray, ix: int) -> Dictionary:
    _check(ram, ix)
    var out: PackedByteArray = ram.duplicate()
    var count: int = (get8(out, 0xE92E) + 1) & 255
    _set8(out, 0xE92E, count)
    if count < 18:
        return {"ram":out,"counter":count,"next_pc":0xBCFA,"words_restored":0}
    _set8(out, ix + 0x41, 0)
    _set8(out, 0xE76A, get8(out, 0xE768))
    _set16(out, 0xE76B, 0xCC00)
    _set16(out, 0xE765, 0)
    _set8(out, ix + 0x4D, 0)
    _set8(out, ix + 0x4C, 0)
    for pair in COPY_PAIRS:
        _set16(out, pair[1], get16(out, pair[0]))
    return {"ram":out,"counter":count,"next_pc":0xBC9E,"words_restored":11}
