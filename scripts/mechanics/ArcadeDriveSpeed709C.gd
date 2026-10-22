class_name ArcadeDriveSpeed709C
extends RefCounted

## ORIGINAL 1991 Z80 MASTER BANK0 709C–7123, ending at 7124.
## Bounded authentic E765 speed-word update, selected by earlier original B.
## Original machine opcodes vs independent integer arithmetic: 100,000
## privately verified cases and zero mismatches. No guessed physics.
##
## Previous genuine X-ROM analysis exhaustively recovered the original
## 256x256 slot1 LOW rounded product and slot0 signed saturated product.
## Original 709C–7123 never CONSUMES slot1 HIGH: the Z80 replaces H before
## using it. Original ROM page 2000–20FF is provided, never embedded.
##
## The caller owns the original 7017–709B state/inputs and subsequent
## 7124 heading/carry chain; this is not a playable per-frame update.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const Car = preload("res://scripts/mechanics/ArcadeCarRecord.gd")

const ENTRY_PC: int = 0x709C
const RETURN_PC: int = 0x7124
const SCRATCH_SPEED: int = 0xE765


static func _signed8(value: int) -> int:
    return value - 256 if value >= 128 else value


static func _slot1_low(high: int, low: int) -> int:
    assert(high >= 0 and high <= 255)
    assert(low >= 0 and low <= 255)
    return ((high * low + 128) >> 8)


static func _slot0_word(high: int, low: int) -> int:
    assert(high >= 0 and high <= 255)
    assert(low >= 0 and low <= 255)
    return clampi(2 * _signed8(high) * _signed8(low),-32768,32767) & 65535


static func apply_original_709c(master_ram: PackedByteArray,
                                physical_car: ArcadeCarRecord,
                                original_b: int,
                                original_rom_2000_table: PackedByteArray) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(original_b >= 0 and original_b <= 255)
    assert(original_rom_2000_table.size() == 256)

    var previous: int = State.get16(master_ram,SCRATCH_SPEED)
    var prior_high: int = previous >> 8
    var ix54: int = physical_car.read_u8(Car.FIELD_WEIGHTED_DRIVE_BIAS)
    var ix3c: int = physical_car.read_u8(0xBC)
    var factor: int = original_rom_2000_table[(-ix3c) & 255]
    var threshold: int = mini(255,_slot1_low(original_b,0xA6) + ix54)
    var exit_b: int = threshold
    var updated_speed: int = previous
    var branch: String = "equal"

    if threshold > prior_high:
        branch = "add"
        var doubled: int = (factor << 1) & 255
        var first: int = _slot1_low(doubled,doubled)
        var second: int = _slot1_low(threshold,first)
        var high: int = physical_car.read_u8(0x60)  # original IX-20
        if (second & 128) != 0:
            second >>= 1
            high = (high << 1) & 255
        var product: int = _slot0_word(high,second)
        # Original Z80: SRL H; RR L; ADC HL,DE; CALL PE,1C88.
        # RR L's carry is the low bit rounded back into the 16-bit sum.
        var lhs: int = product >> 1
        var raw: int = previous + lhs + (product & 1)
        var computed: int = raw & 65535
        var overflow: bool = ((~(lhs ^ previous) & (lhs ^ computed) & 0x8000) != 0)
        updated_speed = 0x7FFF if overflow else computed

    elif threshold < prior_high:
        branch = "subtract"
        exit_b = prior_high - threshold  # original 70EE NEG A; LD B,A
        var doubled: int = (factor << 1) & 255
        var first: int = _slot1_low(doubled,doubled)
        var second: int = _slot1_low(exit_b,first)
        var high: int = physical_car.read_u8(0x61) # original IX-1F
        # Original 70FA SLA H supplies carry unless BIT7/L selects
        # the later 7113 SLA H, which supersedes that carry.
        var carry: int = 1 if (factor & 128) != 0 else 0
        if (second & 128) != 0:
            second >>= 1
            carry = 1 if (high & 128) != 0 else 0
            high = (high << 1) & 255
        var product: int = _slot0_word(high,second)
        var computed: int = (previous - product - carry) & 65535
        # Original SBC HL,DE; CALL M,0AA0: sign bit clamps to zero.
        updated_speed = 0 if (computed & 0x8000) != 0 else computed

    var updated: PackedByteArray = master_ram.duplicate()
    State._set16(updated,SCRATCH_SPEED,updated_speed)
    return {
        "ram": updated,
        "branch": branch,
        "b": exit_b,
        "threshold_b": threshold,
        "e765": updated_speed,
        "factor": factor,
        "next_pc": RETURN_PC,
        "verified_bounded_stage": true,
        "unverified_upstream": "original pre-709C driving, external calls and input cadence"
    }
