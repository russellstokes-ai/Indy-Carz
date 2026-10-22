class_name ArcadeScratchSerializer
extends RefCounted

## Original arcade master Z80:
## 61CE–6299 loads 48 POP-HL/LD-(nn),HL words from one physical car slot
## into shared E72B..E789 working state.
## 629A–6365 loads 48 scratch words in REVERSE ORDER and PUSHes into
## the original car-slot stack window. This writes exactly bytes +00..+5F
## of one original 0x100-byte slot; +60..+FF are never overwritten by
## either transfer.
##
## An original six-slot pass explicitly includes E500 (auxiliary slot).
## No copyrighted game program, graphics, sound or trackmap is stored.
## These pure copies do not simulate original Z80 DI/EI, SP or scheduling:
## the actual 601E callback and its game effects are separate.

const BASE: int = 0xE000
const MEMORY_LENGTH: int = 0x2000
const SCRATCH_START: int = 0xE72B
const SCRATCH_LENGTH: int = 96
const ORIGINAL_SLOT_LENGTH: int = 256
const SLOT_STARTS: Array[int] = [
    0xE000, 0xE100, 0xE200, 0xE300, 0xE400, 0xE500
]


static func _validate(master_ram: PackedByteArray, slot_start: int) -> void:
    assert(master_ram.size() == MEMORY_LENGTH)
    assert(SLOT_STARTS.has(slot_start),
        "Original Z80 snapshot uses one of six 256-byte physical slots")


static func load_slot_to_scratch(master_ram: PackedByteArray,
                                 slot_start: int) -> PackedByteArray:
    ## This intentionally copies only the 48 little-endian Z80 POP-HL
    ## words. The original CPU executes DI, borrows SP, then restores it,
    ## but these CPU flags/stack semantics aren't part of this byte model.
    _validate(master_ram,slot_start)
    var changed: PackedByteArray = master_ram.duplicate()
    var source: int = slot_start - BASE
    var scratch: int = SCRATCH_START - BASE
    for index in range(SCRATCH_LENGTH):
        changed[scratch + index] = master_ram[source + index]
    return changed


static func save_scratch_to_slot(master_ram: PackedByteArray,
                                 slot_start: int) -> PackedByteArray:
    ## Original PUSH-HL visits scratch 0xE789 backwards and decrements
    ## SP from slot_start+0x60 to slot_start; byte outcome is a natural
    ## forward 96-byte copy. Slot +60..+FF must stay untouched.
    _validate(master_ram,slot_start)
    var changed: PackedByteArray = master_ram.duplicate()
    var destination: int = slot_start - BASE
    var scratch: int = SCRATCH_START - BASE
    for index in range(SCRATCH_LENGTH):
        changed[destination + index] = master_ram[scratch + index]
    return changed


static func physical_slot_for_ix(original_ix: int) -> int:
    var slot: int = original_ix - 0x80
    assert(SLOT_STARTS.has(slot),
        "Original IX must point 0x80 bytes into one physical state slot")
    return slot
