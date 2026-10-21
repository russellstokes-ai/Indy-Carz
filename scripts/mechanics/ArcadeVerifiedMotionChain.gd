class_name ArcadeVerifiedMotionChain
extends RefCounted

## Authentic bounded original master Z80 motion sequence 71FA -> 7225 ->
## 7245 -> 726D. This is a deterministic low-level physics CHAIN, not
## a finished full arcade per-car simulation or independent frame scheduler.
##
## It reuses separately genuine original opcode-verified calculations.
## Only genuine original E76B and E933 RAM words are changed here.
## The original nonlocal CALL PE 1689 traps outside the normal chain:
## NEVER guess a motion value or advance 7225 on that route.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const Xrom = preload("res://scripts/mechanics/ArcadeDriveXromAccumulator.gd")
const Velocity = preload("res://scripts/mechanics/ArcadeVelocitySignGate.gd")
const Heading = preload("res://scripts/mechanics/ArcadeDriveHeadingProjection.gd")
const Entry = preload("res://scripts/mechanics/ArcadeDriveEntryGate.gd")
const Car = preload("res://scripts/mechanics/ArcadeCarRecord.gd")

const E76B: int = 0xE76B
const E768: int = 0xE768
const E769: int = 0xE769
const E933: int = 0xE933
const CONTINUE_PC: int = 0x726D
const NONLOCAL_PC: int = 0x1689


static func advance_verified_segment(master_ram: PackedByteArray,
                                     original_c: int,
                                     incoming_de: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH,
           "Expected the original E000-FFFF 8192-byte master RAM view")
    assert(original_c >= 0 and original_c <= 255)
    assert(incoming_de >= 0 and incoming_de <= 65535)

    var prior_e933: int = State.get16(master_ram, E933)
    var stage_71fa: Dictionary = Xrom.calculate(original_c, prior_e933, incoming_de)
    if stage_71fa["next_pc"] == NONLOCAL_PC:
        # Original CALL PE 1689 takes over CPU flow; this stage is NOT
        # a normal returned car update. Preserve caller state untouched.
        return {
            "complete": false,
            "next_pc": NONLOCAL_PC,
            "ram": master_ram.duplicate(),
            "xrom": stage_71fa,
            "motion": {},
            "heading_projection": {}
        }
    assert(stage_71fa["next_pc"] == 0x7225)

    var old_motion: int = State.get16(master_ram, E76B)
    var motion: Dictionary = Velocity.calculate(old_motion, stage_71fa["de"])
    assert(motion["next_pc"] == 0x7245)

    # The original EX DE,HL leaves DE equal to the signed-clamped motion
    # word that the NEXT original trigonometric projection consumes.
    var projection: Dictionary = Heading.calculate(
        State.get8(master_ram, E768),
        State.get16(master_ram, E769),
        motion["de_after"])
    assert(projection["next_pc"] == CONTINUE_PC)
    var out: PackedByteArray = master_ram.duplicate()
    State._set16(out, E76B, motion["stored_e76b"])
    State._set16(out, E933, projection["e933"])

    return {
        "complete": true,
        "next_pc": CONTINUE_PC,
        "ram": out,
        "xrom": stage_71fa,
        "motion": motion,
        "heading_projection": projection
    }



static func advance_from_original_input(master_ram: PackedByteArray,
                                        physical_car: ArcadeCarRecord,
                                        original_b: int,
                                        original_c: int) -> Dictionary:
    ## Composed original 71C8–726C. Original B/C come from the earlier
    ## per-car/course table-selection code; they must NOT be guessed.
    ## This method intentionally does not alter the supplied car record.
    assert(master_ram.size() == State.LENGTH)
    assert(original_b >= 0 and original_b <= 255)
    assert(original_c >= 0 and original_c <= 255)

    var entry: Dictionary = Entry.calculate(
        physical_car.read_u8(Car.FIELD_PEDAL_RESPONSE), original_b,
        original_c, physical_car.read_u8(0x75),
        State.get8(master_ram, 0xE76C))

    if entry["next_pc"] == 0x726D:
        # Original Z80 JP Z,726D: skips 71FA, 7225 and 7245.
        # Unrelated master RAM and caller's physical car stay unchanged.
        return {
            "complete": true,
            "motion_update_skipped": true,
            "next_pc": CONTINUE_PC,
            "ram": master_ram.duplicate(),
            "entry": entry,
            "xrom": {},
            "motion": {},
            "heading_projection": {}
        }

    assert(entry["next_pc"] == 0x71FF or entry["next_pc"] == 0x7225)
    # If entry is 7225, original C is zero: the 71FA helper itself
    # takes the zero-C branch to 7225 without the X-ROM lookup.
    var continuation: Dictionary = advance_verified_segment(
        master_ram, original_c, entry["de"])
    continuation["entry"] = entry
    continuation["motion_update_skipped"] = false
    return continuation
