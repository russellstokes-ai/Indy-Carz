extends SceneTree

# Godot 4.4 headless functional checks — no original ROMs, reconstructed
# copyrighted binary blobs, track sprites or speculative car physics needed.
# This intentionally verifies only the recovered input stages and camera pan.

const Wheel = preload("res://scripts/mechanics/ArcadeWheelInput.gd")
const Steering = preload("res://scripts/mechanics/ArcadeSteeringState.gd")
const Pedal = preload("res://scripts/mechanics/ArcadePedalInput.gd")
const Drive = preload("res://scripts/mechanics/ArcadeDriveStages.gd")
const Motion = preload("res://scripts/mechanics/ArcadeMotionGeometry.gd")
const CollisionRetry = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const CollisionTranslation = preload("res://scripts/mechanics/ArcadeCollisionTranslation.gd")
const VelocityGate = preload("res://scripts/mechanics/ArcadeVelocitySignGate.gd")
const Entry = preload("res://scripts/mechanics/ArcadeDriveEntryGate.gd")
const MotionChain = preload("res://scripts/mechanics/ArcadeVerifiedMotionChain.gd")
const AngularCorrection = preload("res://scripts/mechanics/ArcadeDriveMotionCorrection.gd")
const Steering7315 = preload("res://scripts/mechanics/ArcadeSteeringAngularStage.gd")
const SteeringLookup = preload("res://scripts/mechanics/ArcadeSteeringLookupStage.gd")
const SteeringWeighted = preload("res://scripts/mechanics/ArcadeSteeringWeightedInput.gd")
const SteeringControl = preload("res://scripts/mechanics/ArcadeSteeringControlAngle.gd")
const DoubleProjection = preload("res://scripts/mechanics/ArcadeSteeringDoubleProjection.gd")
const SpeedLimiter = preload("res://scripts/mechanics/ArcadeSteeringSpeedLimiter.gd")
const Car = preload("res://scripts/mechanics/ArcadeCarRecord.gd")
const InputBridge = preload("res://scripts/mechanics/ArcadeInputBridge.gd")
const PortraitCamera = preload("res://scripts/camera/ArcadePortraitCamera.gd")

var _failed: int = 0
var _checks: int = 0


func _verify(condition: bool, description: String) -> void:
    _checks += 1
    if not condition:
        _failed += 1
        push_error("INDY-CARZ FAIL: " + description)


func _initialize() -> void:
    _test_original_wheel()
    _test_original_steering_accumulators()
    _test_original_accelerator()
    _test_exhaustive_input_arithmetic()
    _test_original_drive_byte_stages()
    _test_original_car_state_bridge()
    _test_original_live_motion_geometry()
    _test_verified_collision_retry()
    _test_verified_collision_translation()
    _test_original_velocity_sign_gate()
    _test_original_drive_entry_chain()
    _test_original_angular_motion_limit()
    _test_original_steering_7315()
    _test_original_steering_7376_lookup()
    _test_connected_original_steering_prefix()
    _test_original_weighted_steering_73cd()
    _test_connected_original_weighted_steering()
    _test_original_steering_control_73f6()
    _test_original_steering_7442_7463()
    _test_portrait_camera()

    if _failed > 0:
        printerr("INDY-CARZ: ", _failed, " failures from ", _checks, " checks.")
        quit(1)
    else:
        print("INDY-CARZ: ", _checks, " headless checks passed.")
        quit(0)


func _test_original_wheel() -> void:
    var wheel = Wheel.new()
    var first: Dictionary = wheel.read_player(0, 1)
    _verify(first["steering_response"] == -12, "wheel clockwise step matches ROM")
    _verify(first["phase"] == 1, "wheel phase 1")
    var second: Dictionary = wheel.read_player(0, 0)
    _verify(second["steering_response"] == 12, "wheel reverse step matches ROM")
    _verify(second["phase"] == 2, "wheel phase accumulates")
    wheel.reset()
    _verify(wheel.read_player(0, 0)["steering_response"] == 0, "wheel reset")


func _test_original_steering_accumulators() -> void:
    var straight: Dictionary = Steering.advance(
        0, 0, Steering.Path.DIRECT_BANK_3
    )
    _verify(straight["state_byte"] == 8, "bank-3 centring amount")
    _verify(not straight["overflow_branch"], "bank-3 straight branch")

    var turn: Dictionary = Steering.advance(
        12, 240, Steering.Path.XROM_BANK_0
    )
    _verify(turn["state_byte"] == 134, "bank-0 original overflow state")
    _verify(turn["overflow_branch"], "bank-0 carries into branch")

    var opposite: Dictionary = Steering.advance(
        -12, 150, Steering.Path.XROM_BANK_0
    )
    _verify(opposite["state_byte"] == 130, "bank-0 reverse wheel state")


func _test_original_accelerator() -> void:
    _verify(Pedal.response(0, 255, 255)["response"] == 0, "pedal at rest")
    _verify(Pedal.response(2, 255, 255)["response"] == 2, "pedal fixed-point")
    _verify(Pedal.response(255, 255, 255)["response"] == 126, "pedal saturation")
    var timeout: Dictionary = Pedal.response(0, 0, 0, true)
    _verify(timeout["response"] == 126 and timeout["timeout"], "pedal timeout")


func _test_exhaustive_input_arithmetic() -> void:
    # CI-level independent reference for the verified Z80 math, without ROMs.
    # 41 signed steering inputs x 256 states x 2 original code paths.
    var samples: Array[int] = [0]
    for magnitude in [12, 20, 26, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 62]:
        samples.append(-magnitude)
        samples.append(magnitude)

    for path in [Steering.Path.XROM_BANK_0, Steering.Path.DIRECT_BANK_3]:
        for input_steer in samples:
            for state in range(256):
                var drive: int = 0
                var bias: int = 0
                if path == Steering.Path.XROM_BANK_0:
                    var upper: int = ((input_steer - 1) if input_steer > 0 else input_steer) & 255
                    drive = (upper * 2) & 255
                    bias = 4
                else:
                    drive = (input_steer * 2) & 255
                    bias = 8
                var unwrapped: int = drive + state
                var expected: int = unwrapped & 255
                var boundary: bool = (((drive & 128) != 0) != (unwrapped > 255))
                if boundary:
                    expected ^= 128
                elif (expected & 128) != 0:
                    expected = (expected - bias) & 255
                else:
                    expected = (expected + bias) & 255

                var actual: Dictionary = Steering.advance(input_steer, state, path)
                _verify(actual["state_byte"] == expected and actual["overflow_branch"] == boundary,
                        "steering opcode-math parity, path=%d input=%d state=%d" % [path, input_steer, state])

    # Every unsigned 8x8 X-ROM multiply pair, across representative original
    # input-bias values. The private original X-ROM was exhaustively checked
    # against this independent mathematical formula before commit.
    for raw in range(256):
        for factor in range(256):
            var product: int = ((raw * factor) + 128) >> 8
            for bias in [0, 254, 255]:
                var summed: int = product + bias
                var expected: int = 0
                if summed >= 256:
                    expected = mini((summed - 256) * 2, 0x7E)
                var output: Dictionary = Pedal.response(raw, factor, bias)
                _verify(output["response"] == expected,
                        "pedal Z80 math parity, raw=%d factor=%d bias=%d" % [raw, factor, bias])


func _test_original_drive_byte_stages() -> void:
    _verify(Drive.exceptional_input_branch(126) == 47,
            "original 7039 special branch multiplier")
    _verify(Drive.weighted_car_output(126, 150) == 232,
            "original 709C weighted output")
    _verify(Drive.weighted_car_output(126, 200) == 255,
            "original 709C saturates via carry helper")

    for input_byte in range(256):
        var first_expected: int = ((input_byte * 0x60) + 128) >> 8
        _verify(Drive.exceptional_input_branch(input_byte) == first_expected,
                "original X-ROM special-branch input %d" % input_byte)
        for original_bias in [0, 127, 255]:
            var second_expected: int = mini(
                255, ((input_byte * 0xA6 + 128) >> 8) + original_bias
            )
            _verify(Drive.weighted_car_output(input_byte, original_bias) == second_expected,
                    "original weighted-byte input %d bias %d" % [input_byte, original_bias])


func _test_original_car_state_bridge() -> void:
    var record = Car.new()
    _verify(record.snapshot_bytes().size() == 0x100, "original car-record length")
    # Independent original Z80 opcode + actual MAME state: IX points 0x80
    # bytes INTO the backing physical 0x100-byte state record.
    _verify(Car.racer_slot_start(0) == 0xE000 and
            Car.racer_slot_start(4) == 0xE400,
            "original physical state slots begin 0x80 below Z80 IX")
    _verify(Car.ix_displacement_to_slot_offset(0x57) == Car.FIELD_PEDAL_RESPONSE and
            Car.ix_displacement_to_slot_offset(0x58) == Car.FIELD_PEDAL_FACTOR and
            Car.ix_displacement_to_slot_offset(0x59) == Car.FIELD_PEDAL_BIAS,
            "pedal records are at physical +D7/+D8/+D9, not +57/+58/+59")
    _verify(Car.ix_displacement_to_slot_offset(0x79) == Car.FIELD_STEERING_PRIMARY and
            Car.ix_displacement_to_slot_offset(0x7A) == Car.FIELD_STEERING_SAMPLE and
            Car.ix_displacement_to_slot_offset(0x7B) == Car.FIELD_STEERING_STATE,
            "steering records are at physical +F9/+FA/+FB")
    _verify(Car.ix_displacement_to_slot_offset(0x32) == Car.FIELD_PEDAL_TIMEOUT_FLAG and
            Car.ix_displacement_to_slot_offset(0x54) == Car.FIELD_WEIGHTED_DRIVE_BIAS,
            "original input flag +B2 and weighted drive bias +D4")
    _verify(Car.ix_displacement_to_slot_offset(-0x3F) == 0x41,
            "negative IX displacement maps original shared motion byte")
    # The *old incorrect offsets* must remain untouched during processing.
    record.write_u8(0x57, 0xA5)
    record.write_u8(0x7A, 0x5A)
    record.write_u8(0x32, 0xE0)
    _verify(Car.racer_ram_base(0) == 0xE080, "first arcade racer address")
    _verify(Car.racer_ram_base(4) == 0xE480, "fifth arcade racer address")

    record.write_u8(Car.FIELD_PEDAL_FACTOR, 255)
    record.write_u8(Car.FIELD_PEDAL_BIAS, 255)
    var bridge = InputBridge.new()
    var accel: Dictionary = bridge.sample_original_pedal(2, record)
    _verify(accel["response"] == 2, "original pedal bridge response")
    _verify(record.read_u8(Car.FIELD_PEDAL_RESPONSE) == 2,
            "original pedal writes actual physical slot+D7 (IX+57)")
    _verify(record.read_u8(0x57) == 0xA5,
            "pedal input must not corrupt unrelated physical slot+57")

    var wheel: Dictionary = bridge.sample_original_wheel(0, 1, record)
    _verify(wheel["steering_response"] == -12, "original steering bridge response")
    _verify(record.read_i8(Car.FIELD_STEERING_SAMPLE) == -12,
            "original steering sample reads as signed byte at physical slot+FA")
    _verify(record.read_u8(0x7A) == 0x5A,
            "steering input must not corrupt unrelated physical slot+7A")
    _verify(record.read_u8(Car.FIELD_STEERING_PRIMARY) == 0,
            "conditional original steering primary field untouched")

    bridge.sample_original_pedal(0, record, true)
    _verify(record.read_u8(Car.FIELD_PEDAL_RESPONSE) == 0x7E,
            "original pedal timeout response")
    _verify((record.read_u8(Car.FIELD_PEDAL_TIMEOUT_FLAG) & 2) == 2,
            "original pedal timeout sets bit 1 at physical slot+B2")
    _verify(record.read_u8(0x32) == 0xE0,
            "original timeout must not change unrelated physical slot+32")

    var copy: PackedByteArray = record.snapshot_bytes()
    copy[Car.FIELD_PEDAL_RESPONSE] = 0
    _verify(record.read_u8(Car.FIELD_PEDAL_RESPONSE) == 0x7E,
            "debug snapshots cannot mutate original live record")



func _test_original_live_motion_geometry() -> void:
    # Independent golden hash for original 256 sine + cosine samples, rebuilt
    # mathematically without original game-table bytes in this repository.
    var samples: PackedByteArray = PackedByteArray()
    for is_sine in [false, true]:
        for angle in range(256):
            samples.append(Motion._trig8(angle, is_sine) & 255)
    var hash_context: HashingContext = HashingContext.new()
    hash_context.start(HashingContext.HASH_SHA256)
    hash_context.update(samples)
    var sample_digest: String = hash_context.finish().hex_encode()
    _verify(sample_digest == "8a9cef6191018fefbc88bfaae6acb6faabfee0b9e4ea104e21c0c75286b5b895",
            "all 512 original trigonometric outputs match independent maths")

    var center: Dictionary = Motion.integrate_center(64, 64, 5, 65535)
    _verify(center["x"] == 259 and center["y"] == 65535,
            "original clockwise 16-bit movement wraps exactly")
    _verify(center["dx"] == 254 and center["dy"] == 0,
            "original 8-bit signed X-ROM multiply and axis rounding")

    var reversed: Dictionary = Motion.integrate_center(192, 128, 0, 0)
    _verify(reversed["dx"] == 512 and reversed["dy"] == 0,
            "original signed multiplication saturates before the fourfold shift")

    var record: ArcadeCarRecord = Car.new()
    record.write_u8(0x0A, 5)
    record.write_u8(0x0B, 0)
    record.write_u8(0x00, 255)
    record.write_u8(0x01, 255)
    record.write_u8(Motion.CAR_MOTION_HEADING, 64)
    record.write_u8(Motion.CAR_SIGNED_MOTION, 64)
    record.write_u8(Motion.CAR_GEOMETRY_HEADING, 0)
    record.write_u8(0x80, 0xAB) # untouched auxiliary state

    var updated: Dictionary = Motion.apply_verified_stages(record, true)
    _verify(updated["integrated"] and updated["x"] == 259 and updated["y"] == 65535,
            "verified centre state stored into original 256-byte car record")
    var footprint: Dictionary = updated["footprint"]
    _verify(footprint[Motion.CORNER_X_1] == 5 and
            footprint[Motion.CORNER_X_2] == 513 and
            footprint[Motion.CORNER_X_3] == 513 and
            footprint[Motion.CORNER_X_4] == 5,
            "original four rotated vehicle X corners at heading zero")
    _verify(footprint[Motion.CORNER_Y_1] == 380 and
            footprint[Motion.CORNER_Y_2] == 65154 and
            footprint[Motion.CORNER_Y_3] == 380 and
            footprint[Motion.CORNER_Y_4] == 65154,
            "original vehicle Y corners and 16-bit wrap")
    _verify(record.read_u8(0x80) == 0xAB,
            "original unrelated car state unchanged by geometry helper")

    # Live MAME tracing also proved that 920 geometry-only events were valid
    # original branches: a caller must choose whether to integrate.
    var no_motion: Dictionary = Motion.apply_verified_stages(record, false)
    _verify(not no_motion["integrated"] and
            no_motion["x"] == 259 and no_motion["y"] == 65535,
            "geometry-only update never fabricates a movement step")

    # Angle/byte domains are exhaustive, with original signed saturation,
    # modulo-16-bit coordinates and no floating-point car velocity update.
    for angle in range(256):
        for motion_byte in [0, 1, 64, 127, 128, 192, 255]:
            var original: Dictionary = Motion.integrate_center(
                angle, motion_byte, 0xFFFA, 0x0005)
            var expected_x: int = (0xFFFA + Motion._axis_step(
                Motion._trig8(angle, true), motion_byte)) & 65535
            var expected_y: int = (5 + Motion._axis_step(
                Motion._trig8(angle, false), motion_byte)) & 65535
            _verify(original["x"] == expected_x and original["y"] == expected_y,
                    "original driving component numerical parity, angle=%d motion=%d" %
                    [angle, motion_byte])


func _test_verified_collision_retry() -> void:
    # Exact bounded original BC8C/BCA5/C468 rules only. Never run
    # speculative physics or synthesize a collision response from these.
    var initial: PackedByteArray = PackedByteArray()
    initial.resize(CollisionRetry.LENGTH)
    initial.fill(0x59)
    initial[0xE608 - 0xE000] = 0xA5
    initial[0xE976 - 0xE000] = 0x13
    initial[0xE977 - 0xE000] = 0xCD
    initial[0xE92E - 0xE000] = 0xFE
    initial[0xE92C - 0xE000] = 0xDD

    for ix in CollisionRetry.CAR_POINTERS:
        initial[ix + 0x31 - 0xE000] = 0xA7
        var entry: Dictionary = CollisionRetry.begin(initial, ix)
        var entry_state: PackedByteArray = entry["ram"]
        _verify(entry["f4"] == 0xB3,
                "original bank OR E976 low byte, not low-nibble replacement")
        _verify(entry["next_pc"] == 0xBCFA and entry["counter"] == 1,
                "original collision first attempt begins at BCFA")
        _verify(CollisionRetry.get8(entry_state, ix + 0x31) == 0x27,
                "original collision entry clears only bit 7 at IX+31")
        _verify(CollisionRetry.get8(entry_state, 0xE92E) == 1 and
                CollisionRetry.get8(entry_state, 0xE92C) == 0,
                "original BC9E entry sets first retry and clears second counter")
        _verify(CollisionRetry.get8(entry_state, 0xE608) == 0xB3,
                "original master hardware bank shadow is updated")
        _verify(CollisionRetry.get8(initial, ix + 0x31) == 0xA7 and
                CollisionRetry.get8(initial, 0xE608) == 0xA5,
                "original input memory snapshot is never mutated by pure helper")

    var fresh: PackedByteArray = PackedByteArray()
    fresh.resize(0x2000)
    fresh.fill(0x7F)
    for n in range(CollisionRetry.COPY_PAIRS.size()):
        var pair: Array = CollisionRetry.COPY_PAIRS[n]
        var saved_word: int = (0x1234 + 0x0137 * n) & 0xFFFF
        fresh[pair[0] - 0xE000] = saved_word & 255
        fresh[pair[0] - 0xE000 + 1] = saved_word >> 8
        fresh[pair[1] - 0xE000] = 0
        fresh[pair[1] - 0xE000 + 1] = 0
    # Set the old angle AFTER resetting the eleven destination words:
    # the final 16-bit restore destination E767 overlaps E768 by design.
    fresh[0xE768 - 0xE000] = 0xD6

    for ix in CollisionRetry.CAR_POINTERS:
        for count in [0, 1, 15, 16, 17, 18, 253, 254, 255]:
            var trial: PackedByteArray = fresh.duplicate()
            trial[0xE92E - 0xE000] = count
            trial[ix + 0x41 - 0xE000] = 0xE4
            trial[ix + 0x4C - 0xE000] = 0xE5
            trial[ix + 0x4D - 0xE000] = 0xE6
            var actual: Dictionary = CollisionRetry.retry(trial, ix)
            var final_ram: PackedByteArray = actual["ram"]
            var new_count: int = (count + 1) & 255
            var fallback: bool = new_count >= 18
            _verify(actual["counter"] == new_count and
                    CollisionRetry.get8(final_ram, 0xE92E) == new_count,
                    "original Z80 retry counter 8-bit wrapping at count=%d" % count)
            _verify(actual["next_pc"] == (0xBC9E if fallback else 0xBCFA) and
                    actual["words_restored"] == (11 if fallback else 0),
                    "original BCFA vs BC9E branch and 11-word restoration at count=%d" % count)
            _verify(CollisionRetry.get8(trial, 0xE92E) == count,
                    "caller RAM copy unchanged after retry")
            if fallback:
                for pair in CollisionRetry.COPY_PAIRS:
                    _verify(CollisionRetry.get16(final_ram, pair[1]) ==
                            CollisionRetry.get16(trial, pair[0]),
                            "all original eleven geometry/heading backup words are restored")
                _verify(CollisionRetry.get8(final_ram, 0xE76A) == 0xD6 and
                        CollisionRetry.get16(final_ram, 0xE76B) == 0xCC00 and
                        CollisionRetry.get16(final_ram, 0xE765) == 0,
                        "original C468 heading, velocity and spin state reset")
                _verify(CollisionRetry.get8(final_ram, ix + 0x41) == 0 and
                        CollisionRetry.get8(final_ram, ix + 0x4C) == 0 and
                        CollisionRetry.get8(final_ram, ix + 0x4D) == 0,
                        "original C468 IX+41/4C/4D fields cleared")
            else:
                _verify(CollisionRetry.get8(final_ram, ix + 0x41) == 0xE4 and
                        CollisionRetry.get8(final_ram, ix + 0x4C) == 0xE5,
                        "the original continuing branch must not run C468")

    var exhausted: PackedByteArray = fresh.duplicate()
    exhausted[0xE92E - 0xE000] = 0xFF
    var wrapped: Dictionary = CollisionRetry.retry(exhausted, 0xE080)
    _verify(wrapped["next_pc"] == 0xBCFA and wrapped["counter"] == 0,
            "original Z80 retry FF-to-zero wraps and skips rollback")


func _test_verified_collision_translation() -> void:
    # Entire original fixed master BE0D-BE67 subroutine: an existing
    # collision response supplies two new positions, and this bounded
    # routine shifts its eight related shared-state geometry/position words.
    # Do NOT mistake this for full traction or wall-collision gameplay.
    var cases: Array = [
        [1234, 1234, 5678, 5678],
        [1234, 1235, 5678, 5678],
        [1234, 1234, 5678, 5679],
        [0, 65535, 65535, 0],
        [65535, 0, 0, 65535],
        [32123, 55123, 37128, 61234]
    ]
    for values in cases:
        var original_ram: PackedByteArray = PackedByteArray()
        original_ram.resize(CollisionRetry.LENGTH)
        original_ram.fill(0xA5)
        var old_x: int = values[0]
        var new_x: int = values[1]
        var old_y: int = values[2]
        var new_y: int = values[3]
        CollisionRetry._set16(original_ram, 0xE731, old_x)
        CollisionRetry._set16(original_ram, 0xE98D, new_x)
        CollisionRetry._set16(original_ram, 0xE73B, old_y)
        CollisionRetry._set16(original_ram, 0xE98F, new_y)
        var x_originals: Dictionary = {}
        var y_originals: Dictionary = {}
        var n: int = 0
        for address in CollisionTranslation.ORIGINAL_X_WORDS:
            var old_word: int = (0xFFFE + n * 341) & 65535
            CollisionRetry._set16(original_ram, address, old_word)
            x_originals[address] = old_word
            n += 1
        for address in CollisionTranslation.ORIGINAL_Y_WORDS:
            var old_word: int = (0x00FD + n * 847) & 65535
            CollisionRetry._set16(original_ram, address, old_word)
            y_originals[address] = old_word
            n += 1
        original_ram[0xE600 - 0xE000] = 0xDA
        var result: Dictionary = CollisionTranslation.apply(original_ram)
        var updated: PackedByteArray = result["ram"]
        var dx: int = (new_x - old_x) & 65535
        var dy: int = (new_y - old_y) & 65535
        _verify(result["delta_x"] == dx and result["delta_y"] == dy,
                "original BE0D two independent wrapped 16-bit translation values")
        _verify(result["x_branch"] == (dx != 0) and
                result["y_branch"] == (dy != 0) and
                result["next_pc"] == 0xBCA5,
                "original BE0D zero-delta JR Z paths and retry continuation")
        _verify(CollisionRetry.get16(updated, 0xE731) == new_x and
                CollisionRetry.get16(updated, 0xE73B) == new_y,
                "original collision geometry reference words replaced")
        _verify(CollisionRetry.get16(updated, 0xE98D) == new_x and
                CollisionRetry.get16(updated, 0xE98F) == new_y,
                "original collision target words are never altered")
        for address in CollisionTranslation.ORIGINAL_X_WORDS:
            _verify(CollisionRetry.get16(updated, address) ==
                    ((x_originals[address] + dx) & 65535),
                    "exact original X-axis geometry translation at %04X" % address)
        for address in CollisionTranslation.ORIGINAL_Y_WORDS:
            _verify(CollisionRetry.get16(updated, address) ==
                    ((y_originals[address] + dy) & 65535),
                    "exact original Y-axis geometry translation at %04X" % address)
        _verify(original_ram[0xE600 - 0xE000] == 0xDA and
                updated[0xE600 - 0xE000] == 0xDA,
                "original BE0D cannot change unrelated 256-byte car records")
        _verify(CollisionRetry.get16(original_ram, 0xE731) == old_x and
                CollisionRetry.get16(original_ram, 0xE73B) == old_y,
                "original bounded translation never mutates the input RAM")


func _test_original_velocity_sign_gate() -> void:
    # Exact original Z80 7225..7244 crossing test, not complete
    # acceleration or a guessed physics update rate.
    var pairs: Array = [
        [0x0000, 0x0000, 0x0000, "positive_keep"],
        [0x1234, 0x0001, 0x1233, "positive_keep"],
        [0x0000, 0x0001, 0x0000, "positive_clamp"],
        [0x7FFF, 0xFFFF, 0x0000, "positive_clamp"],
        [0x8000, 0xFFFF, 0x8001, "negative_keep"],
        [0x8000, 0x0001, 0x0000, "negative_clamp"],
        [0x0001, 0xFFFF, 0x0002, "positive_keep"],
        [0xFFFF, 0x0000, 0xFFFF, "negative_keep"]
    ]
    for item in pairs:
        var old_word: int = item[0]
        var delta: int = item[1]
        var expected: int = item[2]
        var expected_path: String = item[3]
        var result: Dictionary = VelocityGate.calculate(old_word, delta)
        _verify(result["stored_e76b"] == expected and
                result["branch"] == expected_path and
                result["next_pc"] == 0x7245,
                "original 7225 signed16 wrapped gate and exact branch")
        _verify(result["de_after"] == expected and
                result["hl_after"] == delta,
                "original EX DE,HL after final E76B store")
        var ram: PackedByteArray = PackedByteArray()
        ram.resize(0x2000)
        ram.fill(0xA6)
        CollisionRetry._set16(ram, 0xE76B, old_word)
        var updated: Dictionary = VelocityGate.apply_to_ram(ram, delta)
        _verify(CollisionRetry.get16(updated["ram"], 0xE76B) == expected,
                "original 7225 E76B low/high bytes stored correctly")
        _verify(CollisionRetry.get16(ram, 0xE76B) == old_word and
                CollisionRetry.get8(updated["ram"], 0xE600) == 0xA6,
                "bounded original motion update preserves input and unrelated state")

    # Exhaust original 16-bit sign boundary neighbourhoods and ensure
    # no floating-point assumptions silently change the Z80 branch.
    for prior in [0, 1, 2, 0x7FFE, 0x7FFF, 0x8000, 0x8001, 0xFFFE, 0xFFFF]:
        for displacement in [0, 1, 2, 0x7FFE, 0x7FFF,
                             0x8000, 0x8001, 0xFFFE, 0xFFFF]:
            var wrapped: int = (prior - displacement) & 65535
            var expected: int = wrapped if (
                ((prior & 0x8000) != 0) == ((wrapped & 0x8000) != 0)
            ) else 0
            _verify(VelocityGate.calculate(prior, displacement)["stored_e76b"] == expected,
                    "original velocity Z80 JP M/JP P 16-bit boundaries")


func _test_original_drive_entry_chain() -> void:
    # Original Z80 71C8–726C: input threshold, unsigned X-ROM
    # displacement, signed byte motion direction, and C-selected path.
    # Original B/C are caller-supplied verified table bytes, not guessed.
    for response in [0, 1, 15, 16, 17, 128, 255]:
        for b in [0, 1, 127, 255]:
            for c in [0, 1, 2, 255]:
                for ix_minus_0b in [0, 1, 127, 255]:
                    for direction in [0, 127, 128, 255]:
                        var gate: Dictionary = Entry.calculate(
                            response, b, c, ix_minus_0b, direction)
                        if response >= 16:
                            if c == 0:
                                _verify(gate["next_pc"] == 0x726D and
                                        gate["de"] == null,
                                        "original high-pedal zero-C bypass to 726D")
                            else:
                                _verify(gate["next_pc"] == 0x71FF and
                                        gate["de"] == 0,
                                        "original high-pedal nonzero-C forces DE=0")
                        else:
                            var product: int = ((b * ix_minus_0b) + 128) >> 8
                            var amount: int = (((product << 1) & 255) << 4) & 65535
                            if (direction & 128) != 0:
                                amount = (-amount) & 65535
                            _verify(gate["de"] == amount,
                                    "original 71D9 signed 8-bit rounded product, byte double and 16-bit wrap")
                            _verify(gate["next_pc"] == (0x7225 if c == 0 else 0x71FF),
                                    "original C-zero skip of 71FA lookup")

    var base_ram: PackedByteArray = PackedByteArray()
    base_ram.resize(0x2000)
    base_ram.fill(0)
    CollisionRetry._set16(base_ram, 0xE76B, 0x8056)
    CollisionRetry._set16(base_ram, 0xE933, 0x0123)
    CollisionRetry._set16(base_ram, 0xE769, 0x1200)
    base_ram[0xE768 - 0xE000] = 35
    # E76C is HIGH(E76B), already 0x80 from the genuine 16-bit motion word.
    base_ram[0xE600 - 0xE000] = 0x5A

    var car: ArcadeCarRecord = Car.new()
    car.write_u8(0x75, 0xFF)
    car.write_u8(Car.FIELD_PEDAL_RESPONSE, 16)
    car.write_u8(0x57, 0xAB)

    var skip_result: Dictionary = MotionChain.advance_from_original_input(
        base_ram, car, 255, 0)
    _verify(skip_result["complete"] and skip_result["motion_update_skipped"] and
            skip_result["next_pc"] == 0x726D,
            "original 71C8 high-response/C-zero direct shortcut")
    _verify(skip_result["ram"] == base_ram and
            CollisionRetry.get16(base_ram, 0xE76B) == 0x8056,
            "original shortcut changes no motion state")
    _verify(car.read_u8(0x57) == 0xAB,
            "original car input mapping protects unrelated physical slot+57")

    # With the same high response but nonzero C, the original does NOT
    # skip: it sets DE=zero and runs the rest of the 71FA–726C chain.
    var forced_zero: Dictionary = MotionChain.advance_from_original_input(
        base_ram, car, 255, 1)
    _verify(forced_zero["entry"]["de"] == 0 and
            forced_zero["entry"]["next_pc"] == 0x71FF and
            not forced_zero["motion_update_skipped"],
            "original high-response nonzero-C enters actual X-ROM stage with DE=0")
    _verify(forced_zero["next_pc"] == 0x726D or
            forced_zero["next_pc"] == 0x1689,
            "original downstream arithmetic cannot take invented PC")

    car.write_u8(Car.FIELD_PEDAL_RESPONSE, 15)
    var negative_motion: Dictionary = MotionChain.advance_from_original_input(
        base_ram, car, 255, 0)
    _verify(negative_motion["entry"]["next_pc"] == 0x7225 and
            not negative_motion["motion_update_skipped"],
            "low-response/C-zero enters original clamp at 7225")
    _verify(negative_motion["next_pc"] == 0x726D and
            negative_motion["complete"],
            "original C-zero branch passes verified 7225 and 7245")
    _verify(CollisionRetry.get8(negative_motion["ram"], 0xE600) == 0x5A and
            CollisionRetry.get16(base_ram, 0xE933) == 0x0123,
            "original connected motion never changes unrelated memory or input RAM")
    _verify(car.read_u8(Car.FIELD_PEDAL_RESPONSE) == 15 and
            car.read_u8(0x57) == 0xAB,
            "connected original stage must not mutate source car record")


func _test_original_angular_motion_limit() -> void:
    # Original 726D..72D2 with its two different signed overflow helpers.
    # These fixed golden outputs came from an independent CPU interpretation
    # of actual original Z80/X-ROM, with SYNTHETIC factor inputs rather
    # than original proprietary 0x2000 lookup-table bytes.
    var golden: Array = [
        # B, factor, E765, E933, E76B, final motion, projected, delta
        [0, 127, 0, 0, 0, 0, 0, 0],
        [99, 56, 65535, 1, 0, 65534, 65534, 65534],
        [25, 127, 0x4000, 0x8000, 0x4000, 16784, 16256, 400],
        [127, 127, 0x7FFF, 0, 0x7FFF, 32767, 32510, 2032],
        [64, 128, 0x8000, 0x7FFF, 0x8000, 32768, 32767, 0],
        [255, 0, 0x8000, 0x7FFF, 0xFFFF, 61455, 0, 61456]
    ]
    for v in golden:
        var b: int = v[0]
        var factor: int = v[1]
        var angular: int = v[2]
        var projection: int = v[3]
        var prior_motion: int = v[4]
        var result: Dictionary = AngularCorrection.calculate(
            b, factor, angular, projection, prior_motion)
        _verify(result["e76b"] == v[5] and
                result["projected"] == v[6] and
                result["change"] == v[7] and
                result["next_pc"] == 0x72D3,
                "original 726D angular damping/limit/overflow golden Z80 values")

        var ram: PackedByteArray = PackedByteArray()
        ram.resize(0x2000)
        ram.fill(0x6B)
        CollisionRetry._set16(ram, 0xE765, angular)
        CollisionRetry._set16(ram, 0xE933, projection)
        CollisionRetry._set16(ram, 0xE76B, prior_motion)
        var before: PackedByteArray = ram.duplicate()
        var changed: Dictionary = AngularCorrection.apply_to_ram(ram,b,factor)
        _verify(CollisionRetry.get16(changed["ram"],0xE76B) == v[5] and
                CollisionRetry.get16(changed["ram"],0xE765) == angular and
                CollisionRetry.get16(changed["ram"],0xE933) == projection,
                "original 726D RAM stores only new motion and retains source geometry")
        _verify(ram == before,
                "original 726D pure CPU state helper leaves supplied RAM unchanged")

    var first_overflow: Dictionary = AngularCorrection.calculate(
        25,127,0x4000,0x8000,0x4000)
    _verify(first_overflow["first_overflow"] and
            first_overflow["difference"] == 0x7FFF,
            "original 0B76 always forces first-stage positive 7FFF")

    var second_overflow: Dictionary = AngularCorrection.calculate(
        127,127,0x7FFF,0,0x7FFF)
    _verify(second_overflow["second_overflow"] and
            second_overflow["e76b"] == 0x7FFF,
            "original 0B6B chooses positive 7FFF for signed final overflow")

    # A direct 71C8 high-response/C-zero branch skips 71FA–726C,
    # but MUST STILL run 726D. All 16-bit state inputs are consistent.
    var master: PackedByteArray = PackedByteArray()
    master.resize(0x2000)
    master.fill(0)
    CollisionRetry._set16(master,0xE765,0x4000)
    CollisionRetry._set16(master,0xE933,0x8000)
    CollisionRetry._set16(master,0xE76B,0x4000)
    var car: ArcadeCarRecord = Car.new()
    car.write_u8(Car.FIELD_PEDAL_RESPONSE,16)
    car.write_u8(0x75,0x7F)
    var complete: Dictionary = MotionChain.advance_through_original_motion_correction(
        master,car,25,0,127)
    _verify(complete["complete"] and
            complete["motion_update_skipped"] and
            complete["next_pc"] == 0x72D3,
            "original direct entry skip still executes verified 726D motion limits")
    _verify(CollisionRetry.get16(complete["ram"],0xE76B) == 16784 and
            CollisionRetry.get16(complete["ram"],0xE933) == 0x8000,
            "connected original 71C8->726D bypass uses exact 726D result")
    _verify(CollisionRetry.get16(master,0xE76B) == 0x4000,
            "connected original physics does not mutate caller input state")

    # Other gate branch still connects into full calculated motion chain.
    car.write_u8(Car.FIELD_PEDAL_RESPONSE,15)
    var non_skipped: Dictionary = MotionChain.advance_through_original_motion_correction(
        master,car,25,0,127)
    _verify(non_skipped["next_pc"] == 0x72D3 and
            not non_skipped["motion_update_skipped"],
            "original low-response entry runs 71D9, 7225, 7245 and 726D")
    _verify(non_skipped["motion_correction"]["next_pc"] == 0x72D3,
            "original 726D normal continuation remains instruction-bound")


func _test_original_steering_7315() -> void:
    ## Original full 7315-7375 bounded angular steering state update.
    ## The original processor has an unusual borrowed carry from 7335
    ## into 733C: the 0xFBFE indexed field is PASSTHROUGH.
    var golden: Array = [
        # E771, E773, input IX+4C word, angular E767,
        # original branch name, resulting car word, resulting E767
        [0x0100, 0x0200, 0x0402, 0xEFAB, "passthrough", 0x0380, 0xF32B],
        [0x0100, 0x0200, 0x0403, 0xEFAB, "positive_clamp", 0x0380, 0xF32B],
        [0x0100, 0x0200, 0x7FFF, 0xEFAB, "positive_clamp", 0x0380, 0xF32B],
        [0x0100, 0x0200, 0x8000, 0xEFAB, "negative_clamp", 0xFC80, 0xEC2B],
        [0x0100, 0x0200, 0xFBFD, 0xEFAB, "negative_clamp", 0xFC80, 0xEC2B],
        [0x0100, 0x0200, 0xFBFE, 0xEFAB, "passthrough", 0xFC7E, 0xEC29],
        [0x0100, 0x0200, 0xFBFF, 0xEFAB, "passthrough", 0xFC7E, 0xEC29],
        [0x0100, 0x0200, 0x0000, 0xEFAB, "passthrough", 0, 0xEFAB]
    ]
    for fields in golden:
        var actual: Dictionary = Steering7315.calculate(
            fields[0], fields[1], fields[2], fields[3], 0x7F)
        _verify(actual["branch"] == fields[4] and
                actual["car4c4d"] == fields[5] and
                actual["e767"] == fields[6] and
                actual["next_pc"] == 0x7530,
                "original 7315 Z80 angular clamp/lookup/16-bit heading parity")
        _verify(actual["addresses"].size() == 2,
                "original 7315 uses two signed-XROM slot0 lookups")

    var first_shortcut: Dictionary = Steering7315.calculate(
        0xFF, 0x0100, 0x4567, 0x789A, 0xB3)
    _verify(first_shortcut["next_pc"] == 0x7376 and
            first_shortcut["car4c4d"] == 0x4567 and
            first_shortcut["e767"] == 0x789A,
            "original 7315 low E771 redirects to 7376 with no writes")
    var second_shortcut: Dictionary = Steering7315.calculate(
        0x0100, 0xFF, 0x4567, 0x789A, 0xB3)
    _verify(second_shortcut["next_pc"] == 0x7381 and
            second_shortcut["a"] == 0xB3,
            "original 7315 low E773 redirects to 7381 with IX+71 in A")

    for ix in CollisionRetry.CAR_POINTERS:
        var ram: PackedByteArray = PackedByteArray()
        ram.resize(0x2000)
        ram.fill(0x75)
        CollisionRetry._set16(ram, 0xE771, 0x0100)
        CollisionRetry._set16(ram, 0xE773, 0x0200)
        CollisionRetry._set16(ram, 0xE767, 0xEFAB)
        CollisionRetry._set16(ram, ix + 0x4C, 0xFBFE)
        ram[ix + 0x71 - 0xE000] = 0xB3
        ram[0xE600 - 0xE000] = 0xC7

        var after: Dictionary = Steering7315.apply_to_ram(ram, ix)
        _verify(after["complete"] and after["next_pc"] == 0x7530 and
                after["branch"] == "passthrough",
                "original complete steering stage enters 7530 from any car")
        _verify(CollisionRetry.get16(after["ram"], ix + 0x4C) == 0xFC7E and
                CollisionRetry.get16(after["ram"], 0xE767) == 0xEC29,
                "original Z80 IX+4C physical state and shared angle updated")
        _verify(CollisionRetry.get16(ram, ix + 0x4C) == 0xFBFE and
                CollisionRetry.get16(ram, 0xE767) == 0xEFAB,
                "pure original steering port never mutates caller RAM")
        _verify(after["ram"][0xE600 - 0xE000] == 0xC7,
                "original bounded stage leaves other game RAM unchanged")

        CollisionRetry._set16(ram, 0xE771, 0xFF)
        var bypass: Dictionary = Steering7315.apply_to_ram(ram, ix)
        _verify(not bypass["complete"] and bypass["next_pc"] == 0x7376 and
                bypass["ram"] == ram,
                "original low-threshold steering branch remains unresolved and immutable")
        CollisionRetry._set16(ram, 0xE771, 0x0100)
        CollisionRetry._set16(ram, 0xE773, 0xFF)
        var alternate: Dictionary = Steering7315.apply_to_ram(ram, ix)
        _verify(not alternate["complete"] and alternate["next_pc"] == 0x7381 and
                alternate["a"] == 0xB3 and alternate["ram"] == ram,
                "original second threshold preserves IX+71 and unchanged RAM")


func _test_original_steering_7376_lookup() -> void:
    # Synthetic table only; no original-game proprietary bytes embedded.
    # The Z80 DOES NOT index all 512 candidate bytes: the 8-bit doubling
    # wraps, making the 128 upper indices aliases for the lower indices.
    var table: PackedByteArray = PackedByteArray()
    for i in range(256):
        table.append((i * 57 + 113) & 255)

    var e773_exact: Dictionary = SteeringLookup.calculate(
        0x7376, 0x0100, 130, 2, table)
    var e773_after: Dictionary = SteeringLookup.calculate(
        0x7376, 0x0101, 130, 2, table)
    _verify(e773_exact["next_pc"] == 0x73CD and
            e773_exact["branch"] == "blended_indices" and
            e773_after["branch"] == "halved_car70",
            "original 7376 inherited Z80 carry distinguishes E773 0100 from 0101")
    _verify(e773_exact["b"] == table[4] and
            e773_after["b"] == (table[4] >> 1),
            "original doubled-byte alias and halved branch result")

    var direct71: Dictionary = SteeringLookup.calculate(
        0x7381, 0x0000, 7, 21, table)
    _verify(direct71["branch"] == "halved_car71" and
            direct71["b"] == (table[42] >> 1) and
            direct71["c"] == (table[43] >> 1),
            "original direct 7381 selects IX+71 and halves each byte")

    var identical: Dictionary = SteeringLookup.calculate(
        0x7394, 0x0000, 27, 27, table)
    _verify(identical["branch"] == "same_index_full" and
            identical["b"] == table[54] and identical["c"] == table[55],
            "original identical steer-control indices preserve full table pair")

    for car70 in [0, 1, 7, 29, 100, 127]:
        for car71 in [0, 1, 8, 37, 127, 255]:
            var blended: Dictionary = SteeringLookup.calculate(
                0x7394, 0, car70, car71, table)
            var first_pair: int = (car70 * 2) & 255
            var second_pair: int = (car71 * 2) & 255
            var expected_b: int = (
                table[first_pair] + table[second_pair]) >> 1
            var expected_c: int = (
                table[first_pair + 1] + table[second_pair + 1]) >> 1
            if car70 == car71:
                expected_b = table[first_pair]
                expected_c = table[first_pair + 1]
            _verify(blended["b"] == expected_b and
                    blended["c"] == expected_c and
                    blended["next_pc"] == 0x73CD,
                    "original Z80 RRA with add carry correctly averages two byte pairs")

    # Full original index domain, including aliasing pairs.
    for index in range(128):
        var selected_low: Dictionary = SteeringLookup.calculate(
            0x7381, 0, 0, index, table)
        var selected_high: Dictionary = SteeringLookup.calculate(
            0x7381, 0, 0, index + 128, table)
        _verify(selected_low["b"] == selected_high["b"] and
                selected_low["c"] == selected_high["c"],
                "original steering two-times-index byte wrap at 128")
    var first_stage: Dictionary = Steering7315.calculate(
        0xFF, 0x100, 0x1234, 0xFABC, 22)
    var composed: Dictionary = SteeringLookup.after_verified_7315(
        first_stage, 0x100, 7, 21, table)
    _verify(composed["next_pc"] == 0x73CD and
            composed["branch"] == "blended_indices",
            "original 7315 early exit enters recovered 7376 lookup stage")


func _test_connected_original_steering_prefix() -> void:
    # Connected verified original 71C8 -> 7315/7376.
    # Every input is synthetic; original ROM table is not distributed.
    var lookup: PackedByteArray = PackedByteArray()
    for i in range(256):
        lookup.append((i * 57 + 113) & 255)

    for ix in CollisionRetry.CAR_POINTERS:
        var master: PackedByteArray = PackedByteArray()
        master.resize(0x2000)
        master.fill(0)
        CollisionRetry._set16(master, 0xE771, 0x0100)
        CollisionRetry._set16(master, 0xE773, 0x0200)
        CollisionRetry._set16(master, ix + 0x4C, 0)
        master[ix + 0x70 - 0xE000] = 130
        master[ix + 0x71 - 0xE000] = 21
        master[0xE600 - 0xE000] = 0xE3

        var car: ArcadeCarRecord = Car.new()
        car.write_u8(Car.FIELD_PEDAL_RESPONSE, 16)
        car.write_u8(0x75, 0)
        var input_copy: PackedByteArray = master.duplicate()

        # This route executes the original 7315 stage and jumps straight
        # to the already opcode-verified coordinate stage at 7530.
        var normal: Dictionary = MotionChain.advance_through_original_steering_selection(
            master, car, ix, 0, 0, 0, 0, lookup)
        _verify(normal["complete"] and normal["next_pc"] == 0x7530 and
                normal["steering_7315"]["branch"] == "passthrough",
                "connected original steering normal route reaches 7530")
        _verify(normal["ram"] == master,
                "zero-motion steering normal stage changes no original RAM")
        _verify(master == input_copy,
                "original verified whole prefix does not mutate input")

        CollisionRetry._set16(master, 0xE771, 0x00FF)
        var first: Dictionary = MotionChain.advance_through_original_steering_selection(
            master, car, ix, 0, 0, 0, 0, lookup)
        _verify(not first["complete"] and
                first["verified_prefix_complete"] and
                first["next_pc"] == 0x73CD and
                first["steering_7315"]["next_pc"] == 0x7376 and
                first["steering_7376"]["branch"] == "halved_car70",
                "original 7315 low E771 to 7376 to 73CD is preserved")
        _verify(first["steering_7376"]["b"] == (lookup[4] >> 1),
                "original car70 130 aliases control-table index 2")
        _verify(first["unverified_downstream"] == "original Z80 73CD-752F",
                "original unknown downstream branch explicitly remains open")

        CollisionRetry._set16(master, 0xE771, 0x0100)
        CollisionRetry._set16(master, 0xE773, 0x00FF)
        var second: Dictionary = MotionChain.advance_through_original_steering_selection(
            master, car, ix, 0, 0, 0, 0, lookup)
        _verify(not second["complete"] and second["next_pc"] == 0x73CD and
                second["steering_7315"]["next_pc"] == 0x7381 and
                second["steering_7376"]["branch"] == "halved_car71",
                "original low E773 selector correctly enters 7381")
        _verify(second["steering_7376"]["c"] == (lookup[43] >> 1),
                "original 7381 chooses second index car+71 and returns exact C")


func _test_original_weighted_steering_73cd() -> void:
    # Exact original 73CD: returning -128 NEG saturation and TWO
    # serial rounded unsigned X-ROM slot1 lookups. We supply synthetic
    # source factor bytes; no original 65-byte ROM table is embedded.
    _verify(SteeringWeighted.FACTOR_TABLE_ENTRIES == 65 and
            SteeringWeighted.FACTOR_TABLE_BASE == 0x7635 and
            SteeringWeighted.RETURN_PC == 0x73F6,
            "original 73CD fixed lookup page and verified return PC")

    for motion in range(256):
        var signed_motion: int = motion if motion < 128 else motion - 256
        var magnitude: int = mini(127,absi(signed_motion))
        var expected_index: int = (magnitude + 1) >> 1
        _verify(SteeringWeighted.original_table_index(motion) == expected_index,
                "original 73CD 256 motion magnitudes including -128 overflow")
    _verify(SteeringWeighted.original_table_index(128) == 64 and
            SteeringWeighted.original_table_index(129) == 64 and
            SteeringWeighted.original_table_index(127) == 64,
            "original NEG -128 overflow helper 1C85 returns magnitude 127")

    var saturated: Dictionary = SteeringWeighted.calculate(
        128,255,255,255)
    _verify(saturated["neg128_saturated"] and
            saturated["table_index"] == 64 and
            saturated["first_low"] == 254 and
            saturated["weighted"] == 253 and
            saturated["next_pc"] == 0x73F6,
            "original 73CD double rounding and returning 1C85 clamp")
    _verify(saturated["xr_addresses"] == [0xFFFF,0xFFFE],
            "original second X-ROM address uses first product low byte")

    for motion in [0,1,2,63,64,127,128,129,192,254,255]:
        for first_operand in [0,1,127,128,255]:
            for car_factor in [0,1,127,128,255]:
                var original_factor: int = (motion+first_operand+car_factor) & 255
                var result: Dictionary = SteeringWeighted.calculate(
                    motion,first_operand,car_factor,original_factor)
                var expected_first: int = (
                    (original_factor*first_operand+128)>>8)
                var expected_second: int = (
                    (car_factor*expected_first+128)>>8)
                _verify(result["first_low"] == expected_first and
                        result["weighted"] == expected_second,
                        "original 73CD X-ROM multiplication is rounded twice")
                _verify(result["xr_addresses"] == [
                    (original_factor<<8)|first_operand,
                    (car_factor<<8)|expected_first
                ],"original 73CD lookup inputs preserve exact byte layout")


func _test_connected_original_weighted_steering() -> void:
    # Original steering prefix connected from 71C8 through 73F6.
    # Actual original B/C and X-ROM factor bytes must be supplied
    # externally. No ROM-table contents or inferred physics here.
    var lookup: PackedByteArray = PackedByteArray()
    for i in range(256):
        lookup.append((i * 57 + 113) & 255)

    for ix in CollisionRetry.CAR_POINTERS:
        var ram: PackedByteArray = PackedByteArray()
        ram.resize(0x2000)
        ram.fill(0)
        CollisionRetry._set16(ram,0xE771,0x00FF)
        CollisionRetry._set16(ram,0xE773,0x0200)
        ram[ix + 0x70 - 0xE000] = 130
        ram[ix + 0x71 - 0xE000] = 21
        ram[ix - 1 - 0xE000] = 255

        var physical: ArcadeCarRecord = Car.new()
        physical.write_u8(Car.FIELD_PEDAL_RESPONSE,16)

        var old_ram: PackedByteArray = ram.duplicate()
        var real_prefix: Dictionary = MotionChain.advance_through_original_weighted_steering(
            ram,physical,ix,0,0,0,0,lookup,255)
        _verify(not real_prefix["complete"] and
                real_prefix["verified_prefix_complete"] and
                real_prefix["next_pc"] == 0x73F6,
                "original low E771 steering prefix reaches 73F6")
        var selected: int = lookup[4] >> 1
        var first: int = ((255 * selected + 128) >> 8)
        var second: int = ((255 * first + 128) >> 8)
        _verify(real_prefix["steering_7376"]["b"] == selected and
                real_prefix["weighted_73cd"]["first_low"] == first and
                real_prefix["weighted_73cd"]["weighted"] == second,
                "original selected B feeds two serial rounded XROM multipliers")
        _verify(real_prefix["unverified_downstream"] == "original Z80 73F6-752F",
                "original 73F6+ physics is not silently approximated")
        _verify(ram == old_ram,
                "original car/physics input buffers are not mutated by prefix")

        CollisionRetry._set16(ram,0xE771,0x0100)
        CollisionRetry._set16(ram,0xE773,0x0100)
        var normal: Dictionary = MotionChain.advance_through_original_weighted_steering(
            ram,physical,ix,0,0,0,0,lookup,255)
        _verify(normal["complete"] and normal["next_pc"] == 0x7530 and
                normal["weighted_73cd"].is_empty(),
                "normal 7315 steering bypass must not execute original 73CD")


func _test_original_steering_control_73f6() -> void:
    # Original 73F6 angular control includes an inherited borrow across
    # two SBC HL,DE operations and the three returning saturation helpers.
    var golden: Array = [
        # Original wrapped word, IX+79 steering sign, angular byte, A output
        [0x0000,0,0,64],
        [0x0000,0x80,0,64],
        [0x0400,0,8,72],
        [0x0400,0x80,8,56],
        [0xFC00,0,-8,56],
        [0xFC00,0x80,-8,72],
        [0x7FFF,0,127,127],
        [0x7FFF,0x80,127,32],
        [0x8000,0,-128,32],
        [0x8000,0x80,-128,127]
    ]
    for item in golden:
        var result: Dictionary = SteeringControl.calculate(
            item[0],0,0,0,item[1])
        _verify(result["wrapped_word"] == item[0] and
                result["angular_sample"] == item[2] and
                result["a"] == item[3] and
                result["next_pc"] == 0x7442,
                "original 73F6 saturated signed control and steering sign")

    var borrowed: Dictionary = SteeringControl.calculate(
        0,0xFFFF,0,0x007F,0)
    _verify(borrowed["borrow_from_first_subtraction"] == 1 and
            borrowed["wrapped_word"] == 0x007F and
            borrowed["a"] == 64,
            "original 73F6 preserves first SBC borrow into second SBC")
    var changed: Dictionary = SteeringControl.calculate(
        0,0xFFFF,0,0x0080,0)
    _verify(changed["wrapped_word"] == 0x0080 and
            changed["a"] == 65,
            "original double-SBC borrow changes angular control threshold")

    for first in [0,1,0x7FFF,0x8000,0xFFFF]:
        for second in [0,1,0x7FFF,0x8000,0xFFFF]:
            for car_bit in [0,0x80]:
                var result: Dictionary = SteeringControl.calculate(
                    first,second,0x1234,0xFEDC,car_bit)
                _verify(result["a"] >= 32 and result["a"] <= 127,
                        "original 0B35/0B3E/1C85 control saturation")

    # Connected control stage: genuine original 7315 low-threshold
    # branches reach 73CD, which generates an A byte for 73F6.
    var table: PackedByteArray = PackedByteArray()
    for i in range(256):
        table.append((i * 57 + 113) & 255)
    for ix in CollisionRetry.CAR_POINTERS:
        var master: PackedByteArray = PackedByteArray()
        master.resize(0x2000)
        master.fill(0)
        CollisionRetry._set16(master,0xE771,0x00FF)
        CollisionRetry._set16(master,0xE773,0x0200)
        CollisionRetry._set16(master,0xE789,0x0800)
        master[ix + 0x70 - 0xE000] = 130
        master[ix + 0x71 - 0xE000] = 21
        master[ix - 1 - 0xE000] = 255
        master[ix + 0x79 - 0xE000] = 0
        var car: ArcadeCarRecord = Car.new()
        car.write_u8(Car.FIELD_PEDAL_RESPONSE,16)
        var before: PackedByteArray = master.duplicate()

        var result: Dictionary = MotionChain.advance_through_original_steering_control(
            master,car,ix,0,0,0,0,table,255)
        _verify(result["verified_prefix_complete"] and
                not result["complete"] and result["next_pc"] == 0x7442,
                "connected verified original physics reaches steering PC 7442")
        _verify(not result["steering_control_73f6"].is_empty() and
                result["steering_control_73f6"]["a"] >= 32 and
                result["steering_control_73f6"]["a"] <= 127,
                "connected steering angular control has original bounded output")
        _verify(result["unverified_downstream"] == "original Z80 7442-752F",
                "the original post-7442 steering mechanics remain explicit")
        _verify(before == master,
                "connected original steering control preserves caller input")

        CollisionRetry._set16(master,0xE771,0x0100)
        var normal: Dictionary = MotionChain.advance_through_original_steering_control(
            master,car,ix,0,0,0,0,table,255)
        _verify(normal["complete"] and normal["next_pc"] == 0x7530 and
                normal["steering_control_73f6"].is_empty(),
                "original 7315 normal route bypasses unneeded steering control")


func _test_original_steering_7442_7463() -> void:
    ## Exact original 7442 signed XROM, 7463 speed limiter, output PC 7499.
    ## The weighted byte comes from the preceding original 73CD AF stack.
    var cases: Array = [
        # original A, IX+79, saved weighted byte, IX+31,
        # original correction, continuation PC
        [64, 0, 0, 0, 0, 0x7463],
        [64, 0, 0, 1, 0, 0x748A],
        [32, 127, 127, 0, 3937, 0x7463],
        [127, 128, 255, 0, 254, 0x7463],
        [32, 255, 128, 1, 65408, 0x748A],
        [127, 255, 255, 0, 65282, 0x7463],
        [64, 128, 128, 0, 57344, 0x7463],
        [127, 127, 127, 255, 16002, 0x748A]
    ]
    for inputs in cases:
        var stage: Dictionary = DoubleProjection.calculate(
            inputs[0], inputs[1], inputs[2], inputs[3])
        _verify(stage["correction"] == inputs[4] and
                stage["next_pc"] == inputs[5],
                "original 7442 double XROM signed product and byte boundary")
        _verify(stage["skip_velocity_limiter"] == ((inputs[3] & 1) != 0),
                "original indexed IX+31 bit0 chooses 7463 vs 748A")
        _verify(stage["first_xrom_address"] == ((inputs[1] << 8) | inputs[0]),
                "original 7442 first signed XROM operand address")

    var limit_cases: Array = [
        [0,0,0,0,0,0],
        [65535,0,0,0,65535,65535],
        [0x1234,0,0xFFFF,0,0x1234,0x1233],
        [0x8000,65535,0,0,0x8000,0x8000],
        [0x3000,0x1234,0xADEF,0,5049,49576],
        [0xFF00,0x8000,0x0102,0,0xFF00,2],
        [0x8000,0x1000,0xFFFF,1,0x8000,0x7FFF]
    ]
    for values in limit_cases:
        var result: Dictionary = SpeedLimiter.calculate(
            values[0],values[1],values[2],values[3])
        _verify(result["car4c4d"] == values[4] and
                result["heading_e767"] == values[5] and
                result["next_pc"] == 0x7499,
                "original 7463 inherited-carry speed limit and E767 update")
        _verify(result["limiter_bypassed"] == ((values[3] & 1) != 0),
                "original 7463/748A bit0 skip matches Z80 branch")

    var table: PackedByteArray = PackedByteArray()
    for i in range(256):
        table.append((i * 57 + 113) & 255)
    for ix in CollisionRetry.CAR_POINTERS:
        for bypass_status in [0, 1]:
            var memory: PackedByteArray = PackedByteArray()
            memory.resize(0x2000)
            memory.fill(0)
            CollisionRetry._set16(memory,0xE771,0x00FF)
            CollisionRetry._set16(memory,0xE773,0x0200)
            CollisionRetry._set16(memory,0xE789,0x0800)
            CollisionRetry._set16(memory,0xE767,0xDFFE)
            CollisionRetry._set16(memory,0xE76B,0x7FFE)
            memory[ix + 0x70 - 0xE000] = 130
            memory[ix + 0x71 - 0xE000] = 21
            memory[ix - 1 - 0xE000] = 255
            memory[ix + 0x79 - 0xE000] = 0x80
            memory[ix + 0x31 - 0xE000] = bypass_status
            memory[0xE600 - 0xE000] = 0xA5
            var car: ArcadeCarRecord = Car.new()
            car.write_u8(Car.FIELD_PEDAL_RESPONSE,16)

            var before: PackedByteArray = memory.duplicate()
            var after: Dictionary = MotionChain.advance_through_original_steering_speed_limit(
                memory,car,ix,0,0,0,0,table,255)
            _verify(after["verified_prefix_complete"] and
                    not after["complete"] and after["next_pc"] == 0x7499,
                    "original connected physics proceeds through 7442 to 7499")
            _verify(after["double_projection_7442"]["next_pc"] ==
                    (0x748A if bypass_status == 1 else 0x7463),
                    "real car IX+31 steering limiter branch preserved")
            var limited: Dictionary = after["speed_limiter_7463"]
            _verify(limited["limiter_bypassed"] == (bypass_status == 1) and
                    CollisionRetry.get16(after["ram"],ix + 0x4C) == limited["car4c4d"] and
                    CollisionRetry.get16(after["ram"],0xE767) == limited["heading_e767"],
                    "original signed projection stored to physical car+CC and shared E767")
            _verify(memory == before and car.read_u8(Car.FIELD_PEDAL_RESPONSE) == 16,
                    "connected original steering never mutates caller inputs")
            _verify(CollisionRetry.get8(after["ram"],0xE600) == 0xA5,
                    "original 7442/7463 leaves unrelated shared RAM unchanged")

    ## Original 7315 normal steering branch jumps to 7530, skipping
    ## 7376/73CD/73F6/7442/7463 entirely.
    var normal_ram: PackedByteArray = PackedByteArray()
    normal_ram.resize(0x2000)
    normal_ram.fill(0)
    CollisionRetry._set16(normal_ram,0xE771,0x0100)
    CollisionRetry._set16(normal_ram,0xE773,0x0200)
    var normal_car: ArcadeCarRecord = Car.new()
    normal_car.write_u8(Car.FIELD_PEDAL_RESPONSE,16)
    var normal: Dictionary = MotionChain.advance_through_original_steering_speed_limit(
        normal_ram,normal_car,0xE080,0,0,0,0,table,255)
    _verify(normal["next_pc"] == 0x7530 and
            normal["double_projection_7442"].is_empty() and
            normal["speed_limiter_7463"].is_empty(),
            "original 7315 normal route never fabricates extra steering corrections")


func _test_portrait_camera() -> void:
    # Camera code must parse and instantiate without touching car physics.
    var world: Node2D = Node2D.new()
    root.add_child(world)
    var car: Node2D = Node2D.new()
    car.position = Vector2(1200, 1400)
    world.add_child(car)
    var camera = PortraitCamera.new()
    world.add_child(camera)
    camera.follow_target = car
    camera.configure_track_bounds(Rect2(Vector2.ZERO, Vector2(4096, 4096)))
    camera._physics_process(1.0 / 60.0)
    _verify(camera.global_position.distance_to(car.global_position) < 0.1,
            "first camera frame follows vehicle")

    var initial_x: float = camera.global_position.x
    car.position.x += 600
    for i in range(90):
        camera._physics_process(1.0 / 60.0)
    _verify(camera.global_position.x > initial_x + 5.0,
            "camera pans after vehicle exits deadzone")
    _verify(car.position.x == 1800.0,
            "presentation-only camera leaves car's world geometry unchanged")
    world.queue_free()
