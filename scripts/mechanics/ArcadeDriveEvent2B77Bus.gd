class_name ArcadeDriveEvent2B77Bus
extends RefCounted

## Original Z80 2B77–2BCB CPU bus sequence: three port-F4 writes
## and eight ordered bank-tagged memory writes. This records the
## original bus operations and classifies MAME A000-DFFF views, but does
## NOT apply QRAM writes, screen updates or a full 2AD1 call return.
## Original opcode parity: 100,000 cases, zero mismatches.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const BankMap = preload("res://scripts/mechanics/ArcadeMasterBankMap.gd")
const ENTRY_PC: int = 0x2B77
const RET_PC: int = 0x2BCC


static func trace_after_original_2b77(master_ram: PackedByteArray,
                                      original_ix: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var out: PackedByteArray = master_ram.duplicate()
    var base: int = State.get16(out, original_ix + 0x12)
    var target: int = (base + 0x0108) & 0xFFFF
    var target_high: int = target & 0xFF00
    var target_low: int = target & 255

    var bank1: int = (State.get8(out, 0xE608) & 15) | State.get8(out, 0xE613)
    var bank2: int = (bank1 & 15) | State.get8(out, 0xE615)
    var final_bank: int = bank2 & 15

    var writes: Array = []
    for i in range(4):
        writes.append([bank1, target_high | ((target_low + i) & 255),
            State.get8(out, 0xE900 + i * 2)])
    for i in [3, 2, 1, 0]:
        writes.append([bank2, target_high | ((target_low + i) & 255),
            State.get8(out, 0xE901 + i * 2)])

    # Classify only the hardware address window established by MAME.
    # Other addresses remain explicitly unclassified, never invented.
    var mapped_writes: Array = []
    for event in writes:
        var f4: int = event[0]
        var address: int = event[1]
        var decoded: Dictionary = {
            "f4": f4, "address": address, "value": event[2],
            "target": "outside_a000_dfff", "offset": -1
        }
        if address >= 0xA000 and address <= 0xDFFF:
            decoded.merge(BankMap.banked_write_target(address, f4), true)
        mapped_writes.append(decoded)

    # E608 is ordinary master RAM. Hardware writes to selected
    # memory banks are deliberately represented as bus events only.
    State._set8(out, 0xE608, final_bank)
    return {
        "ram": out,
        "next_pc": RET_PC,
        "bus_sequence_complete": true,
        "complete": false,
        "port_f4_values": [bank1, bank2, final_bank],
        "memory_bus_writes": writes,
        "mapped_memory_bus_writes": mapped_writes,
        "original_final_de": target,
        "original_final_hl": State.get16(out, 0xE615),
        "original_final_a": final_bank,
        "unverified_downstream": "original QRAM write replay, video timing, event consequences and 2AD1 return"
    }
