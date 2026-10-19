class_name ArcadeWheelInput
extends RefCounted

## Independently implemented 1991 Indy Heat *input* logic, not vehicle physics.
##
## MAME's dial_compute_value supplies the three signed 8-bit wheel channels.
## Original arcade Z80 master code at $0D6A transforms each channel through
## its $0DCD 32-entry response table and writes car-record IX+$7A.
##
## Preserve this as a verified input adapter. Do not add steering grip,
## velocity, yaw or other invented gameplay calculations to this module.

const PLAYER_COUNT: int = 3

# Original recovered input-response numbers. This is an input mapping, NOT
# the complete steering or traction algorithm.
const STEERING_RESPONSE := [
    0, 12, 20, 26, 30, 32, 34, 36,
    36, 38, 40, 40, 42, 44, 44, 46,
    48, 48, 50, 52, 52, 54, 56, 56,
    58, 60, 60, 62, 62, 62, 62, 62,
]

var _previous_hardware: PackedByteArray = PackedByteArray([0, 0, 0])
var _previous_encoded: PackedByteArray = PackedByteArray([0, 0, 0])
var _previous_game_phase: PackedByteArray = PackedByteArray([0, 0, 0])


func reset() -> void:
    _previous_hardware.fill(0)
    _previous_encoded.fill(0)
    _previous_game_phase.fill(0)


static func mame_dial_encoder(raw_input: int, previous_input: int, previous_encoded: int) -> int:
    # MAME src/mame/cinematronics/leland_m.cpp, dial_compute_value
    var delta: int = (raw_input & 0xFF) - (previous_input & 0xFF)
    var result: int = previous_encoded & 0x80

    if delta > 0x80:
        delta -= 0x100
    elif delta < -0x80:
        delta += 0x100

    if delta < 0:
        result = 0x80
        delta = -delta
    elif delta > 0:
        result = 0

    delta = mini(delta, 0x1F)
    result |= (previous_encoded + delta) & 0x1F
    return result


static func arcade_steering_response(encoded: int, previous_phase: int) -> Dictionary:
    # Original arcade Z80 master routine $0D6A, indexed by $0DCD table.
    var phase: int = encoded & 0x1F
    var delta: int = (phase - (previous_phase & 0x1F)) & 0x1F
    var magnitude: int = STEERING_RESPONSE[delta]
    var response: int = magnitude if ((encoded & 0x80) != 0) else -magnitude
    return {"phase": phase, "response": response, "delta": delta}


func read_player(player: int, physical_dial_8bit: int) -> Dictionary:
    assert(player >= 0 and player < PLAYER_COUNT, "Original cabinet has three wheel inputs")
    var current: int = physical_dial_8bit & 0xFF
    var encoded: int = mame_dial_encoder(
        current, _previous_hardware[player], _previous_encoded[player]
    )
    var mapped: Dictionary = arcade_steering_response(encoded, _previous_game_phase[player])
    _previous_hardware[player] = current
    _previous_encoded[player] = encoded
    _previous_game_phase[player] = mapped["phase"]
    return {
        "hardware_dial": current,
        "arcade_encoded": encoded,
        "steering_response": mapped["response"],
        "phase": mapped["phase"],
        "step": mapped["delta"],
    }
