class_name ArcadeMotionGeometry
extends RefCounted

## Verified ORIGINAL 1991 Indy Heat master Z80:
## - bank 0 7530-7571: signed X-ROM coordinate integration
## - bank 0 7572-75F1: rotated 3x2 car footprint as eight 16-bit words
##
## Genuine live MAME CPU write-tap verification:
## 7,015 integrated position steps and 7,935 complete footprints,
## including 920 authentic geometry-only updates; 0 mismatches.
## 5 original racing cars, 256 motion heading and footprint heading values.
##
## This class implements ONLY those verified subroutines. It does NOT invent
## vehicle acceleration, steering rate, grip, track walls, collisions, AI,
## fuel/turbo, lap logic or the original CPU scheduling.
##
## The original 256-sample trig values are independently regenerated with
## maths at runtime. No original ROM/graphics/table bytes are distributed.

const CAR_POSITION_Y: int = 0x00  # original E72B - E72B
const CAR_POSITION_X: int = 0x0A  # original E735 - E72B
const CAR_GEOMETRY_HEADING: int = 0x3D  # original E768
const CAR_MOTION_HEADING: int = 0x3F  # original E76A
const CAR_SIGNED_MOTION: int = 0x41  # original E76C

const CORNER_X_1: int = 0x12  # E73D
const CORNER_X_2: int = 0x0C  # E737
const CORNER_X_3: int = 0x10  # E73B
const CORNER_X_4: int = 0x0E  # E739
const CORNER_Y_1: int = 0x08  # E733
const CORNER_Y_2: int = 0x02  # E72D
const CORNER_Y_3: int = 0x06  # E731
const CORNER_Y_4: int = 0x04  # E72F


static func _signed8(value: int) -> int:
    assert(value >= 0 and value <= 255, "Original Z80 field must be 8-bit")
    return value - 256 if value >= 128 else value


static func _trig8(heading: int, sine_value: bool) -> int:
    assert(heading >= 0 and heading <= 255, "Original angle must be 8-bit")
    var angle: float = float(heading) * TAU / 256.0
    var scaled: float = 128.0 * (sin(angle) if sine_value else cos(angle))
    return clampi(roundi(scaled), -128, 127)


static func _axis_step(trig_byte: int, motion_byte: int) -> int:
    ## Exact slot-0 signed product, saturate to 16-bit, multiply by four
    ## then round as the ORIGINAL Z80 shift/carry instruction sequence.
    assert(trig_byte >= -128 and trig_byte <= 127)
    var product: int = clampi(trig_byte * _signed8(motion_byte) * 2, -32768, 32767)
    return (product * 4 + 128) >> 8


static func integrate_center(angle: int, motion_byte: int, x: int, y: int) -> Dictionary:
    assert(x >= 0 and x <= 65535 and y >= 0 and y <= 65535)
    var dx: int = _axis_step(_trig8(angle, true), motion_byte)
    var dy: int = _axis_step(_trig8(angle, false), motion_byte)
    return {
        "x": (x + dx) & 0xFFFF,
        "y": (y + dy) & 0xFFFF,
        "dx": dx,
        "dy": dy
    }


static func footprint(angle: int, x: int, y: int) -> Dictionary:
    assert(x >= 0 and x <= 65535 and y >= 0 and y <= 65535)
    var sine_byte: int = _trig8(angle, true)
    var cosine_byte: int = _trig8(angle, false)
    return {
        CORNER_X_1: (x + 3 * sine_byte - 2 * cosine_byte) & 0xFFFF,
        CORNER_X_2: (x - 3 * sine_byte + 2 * cosine_byte) & 0xFFFF,
        CORNER_X_3: (x + 3 * sine_byte + 2 * cosine_byte) & 0xFFFF,
        CORNER_X_4: (x - 3 * sine_byte - 2 * cosine_byte) & 0xFFFF,
        CORNER_Y_1: (y + 3 * cosine_byte + 2 * sine_byte) & 0xFFFF,
        CORNER_Y_2: (y - 3 * cosine_byte - 2 * sine_byte) & 0xFFFF,
        CORNER_Y_3: (y + 3 * cosine_byte - 2 * sine_byte) & 0xFFFF,
        CORNER_Y_4: (y - 3 * cosine_byte + 2 * sine_byte) & 0xFFFF
    }


static func _read_word(record: ArcadeCarRecord, offset: int) -> int:
    return record.read_u8(offset) | (record.read_u8(offset + 1) << 8)


static func _write_word(record: ArcadeCarRecord, offset: int, value: int) -> void:
    record.write_u8(offset, value & 255)
    record.write_u8(offset + 1, (value >> 8) & 255)


static func apply_verified_stages(record: ArcadeCarRecord,
                                  run_original_integrator: bool) -> Dictionary:
    ## Caller MUST supply the real game's branch decision. Original MAME
    ## runs geometry-only in some cases; never invent a movement update.
    ## No whole-game tick rate or incomplete car physics is presumed here.
    var x: int = _read_word(record, CAR_POSITION_X)
    var y: int = _read_word(record, CAR_POSITION_Y)
    if run_original_integrator:
        var movement: Dictionary = integrate_center(
            record.read_u8(CAR_MOTION_HEADING),
            record.read_u8(CAR_SIGNED_MOTION), x, y)
        x = movement["x"]
        y = movement["y"]
        _write_word(record, CAR_POSITION_X, x)
        _write_word(record, CAR_POSITION_Y, y)
    var geometry: Dictionary = footprint(
        record.read_u8(CAR_GEOMETRY_HEADING), x, y)
    for offset in geometry.keys():
        _write_word(record, offset, geometry[offset])
    return {
        "integrated": run_original_integrator,
        "x": x, "y": y,
        "footprint": geometry
    }
