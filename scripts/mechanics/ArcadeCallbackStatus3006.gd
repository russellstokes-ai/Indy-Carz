class_name ArcadeCallbackStatus3006
extends RefCounted

## Original bank0 3006–304C priority order of nine CALL NZ handlers.
## Stop at FIRST called handler: cannot skip an unverified callee and
## assume it did not change later flags. 100,000 original ROM comparisons.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const HANDLERS = [
    [0x300A, 0x32, 5, 0x6C1C],
    [0x3011, 0x32, 3, 0x6DFA],
    [0x3018, 0x32, 4, 0x6E06],
    [0x301F, 0x31, 5, 0x6EA6],
    [0x3026, 0x7E, 2, 0x6A18],
    [0x302D, 0x31, 4, 0x6A3A],
    [0x3034, 0x32, 6, 0x6B61],
    [0x303B, 0x32, 7, 0x6BA2],
    [0x3042, 0x33, 3, 0x6A51]
]


static func run_original_3006(master_ram: PackedByteArray,
                               original_ix: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    for route in HANDLERS:
        var site: int = route[0]
        var offset: int = route[1]
        var bit: int = route[2]
        var target: int = route[3]
        if (State.get8(master_ram, original_ix + offset) & (1 << bit)) != 0:
            return {
                "ram": master_ram.duplicate(), "next_pc": target,
                "call_site_pc": site, "branch": "status_handler",
                "status_offset": offset, "status_bit": bit,
                "complete": false,
                "unverified_downstream": "original status handler external CALL"
            }
    if (State.get8(master_ram, original_ix + 0x34) & 0x30) != 0:
        return {
            "ram": master_ram.duplicate(), "next_pc": 0x113B,
            "call_site_pc": 0x304A,
            "branch": "aggregate_flag_handler", "complete": false,
            "unverified_downstream": "original 113B status aggregation CALL"
        }
    return {
        "ram": master_ram.duplicate(), "next_pc": 0x689D,
        "call_site_pc": 0x304D, "branch": "post_status_dispatch",
        "complete": false,
        "unverified_downstream": "original 689D post-dispatch CALL"
    }
