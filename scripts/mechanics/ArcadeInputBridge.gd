class_name ArcadeInputBridge
extends RefCounted

## Connect verified original 1991 arcade input routines to the original
## 0x100-byte car state records. Does not invent movement, AI, collision,
## steering yaw or upgrade effects.
##
## The three hardware human inputs feed the first three of five car records.
## The original master Z80 uses a separate code path for AI cars.

const WheelScript = preload("res://scripts/mechanics/ArcadeWheelInput.gd")
const PedalScript = preload("res://scripts/mechanics/ArcadePedalInput.gd")
const CarScript = preload("res://scripts/mechanics/ArcadeCarRecord.gd")

var _wheel = WheelScript.new()


func reset_controls() -> void:
    _wheel.reset()


func sample_original_wheel(player_index: int, dial_sample: int,
                           car: ArcadeCarRecord) -> Dictionary:
    # Original master $0D6A writes sampled signed steering at IX+$7A.
    # IX+$79 is only conditionally updated by other original code and
    # deliberately must not be overwritten here without that context.
    assert(player_index >= 0 and player_index < CarScript.ORIGINAL_PLAYER_COUNT)
    var output: Dictionary = _wheel.read_player(player_index, dial_sample)
    car.write_u8(CarScript.FIELD_STEERING_SAMPLE, output["steering_response"])
    return output


func sample_original_pedal(raw_pedal: int, car: ArcadeCarRecord,
                            input_timeout: bool = false) -> Dictionary:
    # Original master $67B5-$67D5 uses IX+$58 and IX+$59 to write IX+$57.
    var response: Dictionary = PedalScript.response(
        raw_pedal,
        car.read_u8(CarScript.FIELD_PEDAL_FACTOR),
        car.read_u8(CarScript.FIELD_PEDAL_BIAS),
        input_timeout
    )
    car.write_u8(CarScript.FIELD_PEDAL_RESPONSE, response["response"])
    if input_timeout:
        # Original $67AD sets bit 1 of IX+$32 when analog polling times out.
        car.set_bit(CarScript.FIELD_PEDAL_TIMEOUT_FLAG, 1)
    return response
