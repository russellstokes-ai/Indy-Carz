class_name ArcadeDriveGate701A
extends RefCounted

## Original 1991 master Z80 701A–7048, AFTER original CALL 75F2.
## Private original-instruction parity against independent branch arithmetic:
## 100,000 cases, zero mismatches across all three original exits.
##
## This module ONLY models the 701A–7048 gate. Its 7049 and 7D4C
## exits are now separately recovered and composed by the surrounding
## ArcadeVerifiedVehiclePhysicsPrefix; no external CALL is fabricated.
## Original IX +/- offsets are addresses in persistent car RAM.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")

const SOURCE_PC: int = 0x701A
const FAST_PC: int = 0x709C
const SLOW_PC: int = 0x7049
const OPAQUE_CALL_PC: int = 0x7D4C


static func apply_after_75f2(master_ram: PackedByteArray, original_ix: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var out: PackedByteArray = master_ram.duplicate()
    var counter_address: int = original_ix - 0x1D
    var previous_counter: int = State.get8(out,counter_address)

    # Original BIT0,(IX+5C); JP Z,7027; CALL 7D4C; JP 7572.
    # Stop AT 7D4C: its side effects/return have not been proven.
    if (State.get8(out,original_ix + 0x5C) & 1) != 0:
        return {
            "ram": out, "branch": "special_7d4c", "next_pc": OPAQUE_CALL_PC,
            "counter": previous_counter, "b": null, "complete": false,
            "pending_original_call": "7D4C (returns to 7024 if it returns normally)"
        }

    # Original LD B,(IX+57) and the two independent car status bit gates.
    var source_b: int = State.get8(out,original_ix + 0x57)
    var first_gate: bool = (State.get8(out,original_ix + 0x31) & 0x10) != 0
    var second_gate: bool = (State.get8(out,original_ix + 0x33) & 1) != 0
    if first_gate or second_gate:
        # INC (IX-1D) wraps in 8 bits, then exact original 256x256
        # X-ROM slot1 LOW arithmetic using B and literal factor 0x60.
        var updated_counter: int = (previous_counter + 1) & 255
        State._set8(out,counter_address,updated_counter)
        var source_multiply_b: int = ((source_b * 0x60 + 128) >> 8)
        return {
            "ram": out, "branch": "fast_709c", "next_pc": FAST_PC,
            "counter": updated_counter, "b": source_multiply_b, "complete": true
        }

    # Original 7045 LD (IX-1D),00 then continue at 7049.
    # The caller applies separately verified 7049–709B arithmetic; its
    # external calls 7E5E and 2AD1 still stop before unknown effects.
    State._set8(out,counter_address,0)
    return {
        "ram": out, "branch": "slow_7049", "next_pc": SLOW_PC,
        "counter": 0, "b": source_b, "complete": false,
        "unverified_continuation": "original 7049–709B",
        "continuation": "original recovered 7049–709B (possible external 7E5E/2AD1)"
    }
