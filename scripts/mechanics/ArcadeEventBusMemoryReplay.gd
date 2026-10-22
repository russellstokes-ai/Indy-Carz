class_name ArcadeEventBusMemoryReplay
extends RefCounted

## Replay MAME-verified A000-DFFF memory effects of original Z80 2B77
## bus operations. Preflight all eight writes; unknown hardware aborts.
## Does NOT simulate original scanline timing or game-event consequences.

const Bus = preload("res://scripts/mechanics/ArcadeDriveEvent2B77Bus.gd")
const BankMap = preload("res://scripts/mechanics/ArcadeMasterBankMap.gd")
const BATTERY_SIZE: int = 0x4000
const QRAM_SIZE: int = 0x10000


static func replay_original_2b77(master_ram: PackedByteArray, original_ix: int,
                                 battery_ram: PackedByteArray,
                                 qram: PackedByteArray) -> Dictionary:
    assert(battery_ram.size() == BATTERY_SIZE)
    assert(qram.size() == QRAM_SIZE)
    var original: Dictionary = Bus.trace_after_original_2b77(master_ram, original_ix)
    var decoded_writes: Array = []
    for write in original["memory_bus_writes"]:
        var f4: int = write[0]
        var addr: int = write[1]
        var value: int = write[2]
        var target: String = "rom_write_ignored"
        var offset: int = -1
        if addr >= 0xA000 and addr <= 0xDFFF:
            var mapping: Dictionary = BankMap.banked_write_target(addr, f4)
            target = mapping["target"]
            offset = mapping["offset"]
        elif addr >= 0xA000:
            return {
                "ram": master_ram.duplicate(),
                "battery_ram": battery_ram.duplicate(),
                "qram": qram.duplicate(),
                "next_pc": original["next_pc"],
                "memory_replay_complete": false,
                "complete": false,
                "unresolved_address": addr,
                "unverified_downstream": "write targets unmodelled master/video hardware"
            }
        decoded_writes.append({
            "f4": f4, "address": addr, "value": value,
            "target": target, "offset": offset
        })

    var battery_out: PackedByteArray = battery_ram.duplicate()
    var qram_out: PackedByteArray = qram.duplicate()
    var dirty_tiles: Array = []
    var partial_updates: int = 0
    for write in decoded_writes:
        var target: String = write["target"]
        var offset: int = write["offset"]
        var value: int = write["value"]
        if target == "battery_ram":
            battery_out[offset] = value
        elif target == "qram":
            qram_out[offset] = value
            var f4: int = write["f4"]
            var addr: int = write["address"]
            dirty_tiles.append(((f4 & 0x80) << 8) | (addr - 0xA000))
            partial_updates += 1

    original["battery_ram"] = battery_out
    original["qram"] = qram_out
    original["mapped_memory_bus_writes"] = decoded_writes
    original["qram_dirty_tiles"] = dirty_tiles
    original["partial_update_requests"] = partial_updates
    original["memory_replay_complete"] = true
    original["engine_return_verified"] = false
    original["complete"] = false
    original["unverified_downstream"] = (
        "real 2BCC return context, beam-timed video changes and race-event consequences")
    return original
