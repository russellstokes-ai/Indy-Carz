class_name ArcadeCollisionGeometryCheckpoint
extends RefCounted

## Authentic original arcade master Z80 75F2-7634 checkpoint.
## Saves exactly 11 working geometry/heading words for later original
## collision retry rollback. No guessed collision scheduling or forces.
##
## The original save order differs from original BC8C restore order.
## All original source/destination CPU addresses are verified in private.
## This class contains no proprietary ROM code, track or game artwork.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const CHECKPOINT_PC: int = 0x75F2
const ORIGINAL_RET_PC: int = 0x7634

# Genuine original LD HL,(source); LD (backup),HL sequence order.
const SOURCE_TO_BACKUP: Array = [
    [0xE72B,0xE749], [0xE735,0xE753],
    [0xE72D,0xE74B], [0xE737,0xE755],
    [0xE72F,0xE74D], [0xE739,0xE757],
    [0xE731,0xE74F], [0xE73B,0xE759],
    [0xE733,0xE751], [0xE73D,0xE75B],
    [0xE767,0xE747]
]


static func snapshot(master_ram: PackedByteArray) -> Dictionary:
    ## Original call to 75F2 is externally scheduled. Calling
    ## this after EVERY movement update would be an invented change.
    assert(master_ram.size() == State.LENGTH)
    var changed: PackedByteArray = master_ram.duplicate()
    var writes: Array = []
    for pair in SOURCE_TO_BACKUP:
        var source: int = pair[0]
        var backup: int = pair[1]
        var word: int = State.get16(changed, source)
        State._set16(changed, backup, word)
        writes.append(Vector2i(backup, word))
    return {
        "ram": changed,
        "writes": writes,
        "next_pc": ORIGINAL_RET_PC,
        "original_saved_words": SOURCE_TO_BACKUP.size()
    }
