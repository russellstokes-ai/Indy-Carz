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
const DriveBC = preload("res://scripts/mechanics/ArcadeDriveControlSelector.gd")
const DriveCarry = preload("res://scripts/mechanics/ArcadeDriveCarryProjection.gd")
const Speed709C = preload("res://scripts/mechanics/ArcadeDriveSpeed709C.gd")
const Gate701A = preload("res://scripts/mechanics/ArcadeDriveGate701A.gd")
const Slow7049 = preload("res://scripts/mechanics/ArcadeDriveSlow7049.gd")
const External7E5E = preload("res://scripts/mechanics/ArcadeDriveExternal7E5E.gd")
const External2AD1 = preload("res://scripts/mechanics/ArcadeDriveExternal2AD1.gd")
const Special7D4C = preload("res://scripts/mechanics/ArcadeDriveSpecial7D4C.gd")
const Smooth7D65 = preload("res://scripts/mechanics/ArcadeDriveSmooth7D65.gd")
const CollisionCheckpoint = preload("res://scripts/mechanics/ArcadeCollisionGeometryCheckpoint.gd")
const SteeringLookup = preload("res://scripts/mechanics/ArcadeSteeringLookupStage.gd")
const SteeringWeighted = preload("res://scripts/mechanics/ArcadeSteeringWeightedInput.gd")
const SteeringControl = preload("res://scripts/mechanics/ArcadeSteeringControlAngle.gd")
const DoubleProjection = preload("res://scripts/mechanics/ArcadeSteeringDoubleProjection.gd")
const SpeedLimiter = preload("res://scripts/mechanics/ArcadeSteeringSpeedLimiter.gd")
const SecondProjection = preload("res://scripts/mechanics/ArcadeSteeringSecondProjection.gd")
const SteeringDecay = preload("res://scripts/mechanics/ArcadeSteeringDecay.gd")
const PhysicsPrefix = preload("res://scripts/mechanics/ArcadeVerifiedVehiclePhysicsPrefix.gd")
const ScratchSerializer = preload("res://scripts/mechanics/ArcadeScratchSerializer.gd")
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
    # SceneTree._initialize runs before the root has entered the tree.
    # Start checks once Camera2D can safely query the real viewport.
    call_deferred("_run_checks")


func _run_checks() -> void:
    _verify(root.is_inside_tree(),
            "headless test runner must execute with a live scene tree")
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
    _test_original_steering_7499_74d8()
    _test_original_vehicle_physics_prefix()
    _test_original_scratch_serializer_and_car_state()
    _test_original_714e_control_selector()
    _test_original_7124_carry_and_714e_pipeline()
    _test_original_709c_speed_stage()
    _test_original_709c_to_per_car_slot()
    _test_original_7049_slow_stage()
    _test_original_7e5e_early_returns_stage()
    _test_original_2ad1_original_bit_gate()
    _test_original_7d65_smoothing_stage()
    _test_original_701a_gate_and_7017_fast_path()
    _test_original_7315_resume_equivalence()
    _test_original_slot_carry_selected_driving_pipeline()
    _test_original_geometry_checkpoint_and_restore()
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


func _test_original_steering_7499_74d8() -> void:
    ## These are original bounded CPU stage outputs, not a game-wide
    ## new physics timestep, throttle constant or tyre friction model.
    var projection_golden: Array = [
        # C, original car IX+00, E767, E769,
        # output DE, unsigned slot1 B, 0B6B saturation
        [64, 255, 28672, 0, 14336, 64, false],
        [255, 255, 0, 0, 0, 127, false],
        [127, 128, 65535, 0, 65532, 64, false],
        [0, 255, 65534, 4096, 0, 0, false],
        [200, 255, 32767, 65535, 32768, 99, true]
    ]
    for item in projection_golden:
        var p: Dictionary = SecondProjection.calculate(
            item[0],item[1],item[2],item[3])
        _verify(p["de_projection"] == item[4] and
                p["factor_b"] == item[5] and
                p["overflow_saturated"] == item[6] and
                p["next_pc"] == 0x74D8,
                "original 7499 3-XROM and returning 0B6B saturation parity")
        _verify(p["slot1_address"] == ((item[0] << 8) | item[1]),
                "original 7499 unsigned slot1 multiplier address")
        _verify(p["first_slot0_address"] >= 0 and
                p["first_slot0_address"] <= 65535 and
                p["second_slot0_address"] >= 0 and
                p["second_slot0_address"] <= 65535,
                "original 7499 separate signed slot0 XROM address domains")

    var decay_golden: Array = [
        # original projection, motion, E769, E767, IX+41, IX+31,
        # final DE, updated E769, updated E767, new IX+41
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [8192, 0, 0, 0, 0, 0, 1408, 5632, 64128, 0],
        [8192, 0, 0, 0, 1, 0, 5632, 2816, 59904, 0],
        [12288, 4660, 44527, 64188, 3, 0, 5048, 47051, 59140, 2],
        [32768, 65535, 65535, 1, 128, 1, 32768, 49151, 32769, 127],
        [12288, 4660, 44527, 64188, 128, 0, 5048, 47051, 59140, 127],
        [12288, 4660, 44527, 64188, 129, 0, 1262, 49576, 62926, 129]
    ]
    for item in decay_golden:
        var d: Dictionary = SteeringDecay.calculate(
            item[0],item[1],item[2],item[3],item[4],item[5])
        _verify(d["final_de"] == item[6] and
                d["e769"] == item[7] and
                d["e767"] == item[8] and
                d["car41"] == item[9] and
                d["next_pc"] == 0x7530,
                "original 74D8 16-bit signed steering decay and counter outputs")

    # Important original DEC A; JP M status boundary: 0 and 129..255
    # skip the countdown write, whereas 1..128 decrement the counter.
    for car_counter in range(256):
        var d: Dictionary = SteeringDecay.calculate(
            0x3000,0x1234,0xADEF,0xFABC,car_counter,1)
        var expected_write: bool = (((car_counter - 1) & 255) & 128) == 0
        _verify(d["counter_decremented"] == expected_write and
                d["car41"] == (((car_counter - 1) & 255)
                    if expected_write else car_counter),
                "original 74D8 signed 8-bit DEC A/JPM counter boundary")

    # Execute the entire verified original motion/steering prefix on
    # each of the five original car records with both bit0 limiter
    # branches and key original countdown boundaries.
    var table: PackedByteArray = PackedByteArray()
    for i in range(256):
        table.append((i * 57 + 113) & 255)
    for ix in CollisionRetry.CAR_POINTERS:
        for status in [0, 1]:
            for counter in [0, 1, 128, 129]:
                var ram: PackedByteArray = PackedByteArray()
                ram.resize(0x2000)
                ram.fill(0)
                CollisionRetry._set16(ram,0xE771,0x00FF)
                CollisionRetry._set16(ram,0xE773,0x0200)
                CollisionRetry._set16(ram,0xE789,0x0800)
                CollisionRetry._set16(ram,0xE767,0xDFFE)
                CollisionRetry._set16(ram,0xE769,0x1FFE)
                CollisionRetry._set16(ram,0xE76B,0x7FFE)
                ram[ix + 0x70 - 0xE000] = 130
                ram[ix + 0x71 - 0xE000] = 21
                ram[ix - 1 - 0xE000] = 255
                ram[ix + 0x79 - 0xE000] = 0x80
                ram[ix + 0x31 - 0xE000] = status
                ram[ix + 0x41 - 0xE000] = counter
                ram[ix + 0x00 - 0xE000] = 0xC1
                ram[0xE600 - 0xE000] = 0xA6
                var original_copy: PackedByteArray = ram.duplicate()
                var car: ArcadeCarRecord = Car.new()
                car.write_u8(Car.FIELD_PEDAL_RESPONSE,16)
                var result: Dictionary = MotionChain.advance_through_original_steering_decay(
                    ram,car,ix,0,0,0,0,table,255)
                _verify(result["next_pc"] == 0x7530 and
                        result["verified_prefix_complete"] and result["complete"],
                        "original connected 71C8-752F steering reaches original 7530")
                _verify(result["second_projection_7499"]["next_pc"] == 0x74D8 and
                        result["steering_decay_74d8"]["next_pc"] == 0x7530,
                        "original 7499/74D8 stages remain in correct Z80 order")
                _verify(CollisionRetry.get16(result["ram"],0xE769) ==
                        result["steering_decay_74d8"]["e769"] and
                        CollisionRetry.get16(result["ram"],0xE767) ==
                        result["steering_decay_74d8"]["e767"] and
                        CollisionRetry.get8(result["ram"],ix + 0x41) ==
                        result["steering_decay_74d8"]["car41"],
                        "original 74D8 RAM stores match isolated verified state")
                _verify(ram == original_copy and
                        CollisionRetry.get8(result["ram"],0xE600) == 0xA6,
                        "connected original steering must preserve caller RAM and unrelated state")

    # The normal 7315 original steering route bypasses ALL intermediate
    # 7376–752F arithmetic, so its post-7499 fields MUST remain empty.
    var normal_ram: PackedByteArray = PackedByteArray()
    normal_ram.resize(0x2000)
    normal_ram.fill(0)
    CollisionRetry._set16(normal_ram,0xE771,0x0100)
    CollisionRetry._set16(normal_ram,0xE773,0x0200)
    var normal_car: ArcadeCarRecord = Car.new()
    normal_car.write_u8(Car.FIELD_PEDAL_RESPONSE,16)
    var normal: Dictionary = MotionChain.advance_through_original_steering_decay(
        normal_ram,normal_car,0xE080,0,0,0,0,table,255)
    _verify(normal["next_pc"] == 0x7530 and
            normal["second_projection_7499"].is_empty() and
            normal["steering_decay_74d8"].is_empty(),
            "original 7315 normal route skips the other steering stages")


func _test_original_vehicle_physics_prefix() -> void:
    ## Shared original master CPU E72B/E735 working state is distinct
    ## from the physical five 256-byte car slots at E000,E100... .
    ## Two legitimate CPU entries: PC7530 integrates+footprint, while
    ## PC7572 ONLY recalculates footprint at the existing centre.
    var baseline: PackedByteArray = PackedByteArray()
    baseline.resize(0x2000)
    baseline.fill(0)
    CollisionRetry._set16(baseline,0xE735,0x1000)
    CollisionRetry._set16(baseline,0xE72B,0xB000)
    CollisionRetry._set16(baseline,0xE767,0x2400)
    CollisionRetry._set16(baseline,0xE769,0x4000)
    CollisionRetry._set16(baseline,0xE76B,0x3F00)
    baseline[0xE600 - 0xE000] = 0xA7

    var expectation: Dictionary = Motion.integrate_center(
        CollisionRetry.get8(baseline,0xE76A),
        CollisionRetry.get8(baseline,0xE76C),
        CollisionRetry.get16(baseline,0xE735),
        CollisionRetry.get16(baseline,0xE72B))
    var actual: Dictionary = PhysicsPrefix.apply_original_7530_to_75f1(baseline)
    _verify(actual["next_pc"] == 0x75F1 and actual["integrated"] and
            CollisionRetry.get16(actual["ram"],0xE735) == expectation["x"] and
            CollisionRetry.get16(actual["ram"],0xE72B) == expectation["y"],
            "original 7530 movement writes exact 16-bit working RAM centre")
    var original_footprint: Dictionary = Motion.footprint(
        CollisionRetry.get8(baseline,0xE768),expectation["x"],expectation["y"])
    for offset in original_footprint.keys():
        _verify(CollisionRetry.get16(actual["ram"],0xE72B+offset) ==
                original_footprint[offset],
                "original 7572 eight-footprint-word geometry and RAM offsets")
    _verify(baseline[0xE600 - 0xE000] == 0xA7 and
            actual["ram"][0xE600 - 0xE000] == 0xA7 and
            CollisionRetry.get16(baseline,0xE735) == 0x1000,
            "pure original 7530 calculation retains input and unrelated state")

    var geometrical: Dictionary = PhysicsPrefix.apply_original_7572_geometry_only(baseline)
    _verify(not geometrical["integrated"] and
            geometrical["movement"].is_empty() and
            geometrical["next_pc"] == 0x75F1 and
            CollisionRetry.get16(geometrical["ram"],0xE735) == 0x1000 and
            CollisionRetry.get16(geometrical["ram"],0xE72B) == 0xB000,
            "original 7572 geometry-only path never invents displacement")
    var only_footprint: Dictionary = Motion.footprint(
        CollisionRetry.get8(baseline,0xE768),0x1000,0xB000)
    for offset in only_footprint.keys():
        _verify(CollisionRetry.get16(geometrical["ram"],0xE72B+offset) ==
                only_footprint[offset],
                "original no-motion geometry recalculation exact in master RAM")

    var table: PackedByteArray = PackedByteArray()
    for i in range(256):
        table.append((i * 57 + 113) & 255)

    for ix in CollisionRetry.CAR_POINTERS:
        for low_steering in [false,true]:
            var state: PackedByteArray = baseline.duplicate()
            CollisionRetry._set16(state,0xE771,0x00FF if low_steering else 0x0100)
            CollisionRetry._set16(state,0xE773,0x0200)
            CollisionRetry._set16(state,0xE789,0x0800)
            state[ix + 0x70 - 0xE000] = 130
            state[ix + 0x71 - 0xE000] = 21
            state[ix - 1 - 0xE000] = 255
            state[ix + 0x79 - 0xE000] = 0x80
            state[ix + 0x31 - 0xE000] = 0
            state[ix + 0x41 - 0xE000] = 1
            state[ix + 0x00 - 0xE000] = 0xC1

            var physical_car: ArcadeCarRecord = Car.new()
            physical_car.write_u8(Car.FIELD_PEDAL_RESPONSE,16)
            var before_ram: PackedByteArray = state.duplicate()
            var driven: Dictionary = PhysicsPrefix.run_verified_prefix(
                state,physical_car,ix,0,0,0,0,table,255)

            _verify(driven["next_pc"] == 0x75F1 and driven["complete"] and
                    driven["original_movement_7530"]["next_pc"] == 0x75F1,
                    "connected original 71C8-75F0 CPU physics reaches RET at 75F1")
            var operation: Dictionary = driven["original_movement_7530"]
            var movement: Dictionary = operation["movement"]
            _verify(CollisionRetry.get16(driven["ram"],0xE735) == movement["x"] and
                    CollisionRetry.get16(driven["ram"],0xE72B) == movement["y"],
                    "original shared RAM movement matches verified connected Z80 projection")
            _verify(before_ram == state and
                    physical_car.read_u8(Car.FIELD_PEDAL_RESPONSE) == 16 and
                    CollisionRetry.get8(driven["ram"],0xE600) == 0xA7,
                    "complete bounded original driving prefix does not mutate inputs")
            _verify(driven["unverified_downstream"].contains("callback"),
                    "full vehicle callback/terrain scheduler remains an explicit boundary")


func _test_original_scratch_serializer_and_car_state() -> void:
    ## Exact original 48-word load/store-back copy and the SIX original
    ## records including auxiliary E500. Only five are racing cars.
    var seed: PackedByteArray = PackedByteArray()
    seed.resize(0x2000)
    seed.fill(0x52)
    for i in range(ScratchSerializer.SLOT_STARTS.size()):
        var slot: int = ScratchSerializer.SLOT_STARTS[i]
        var state: PackedByteArray = seed.duplicate()
        for j in range(96):
            state[slot - 0xE000 + j] = (j * 7 + i) & 255
        state[slot - 0xE000 + 0xD7] = 0xBA
        var before: PackedByteArray = state.duplicate()
        var loaded: PackedByteArray = ScratchSerializer.load_slot_to_scratch(state,slot)
        for n in range(96):
            _verify(loaded[0xE72B - 0xE000 + n] ==
                    state[slot - 0xE000 + n],
                    "original 48-word POP maps all 96 bytes into E72B scratch")
        _verify(loaded[slot - 0xE000 + 0xD7] == 0xBA and
                state == before,
                "original scratch LOAD preserves physical high state and caller RAM")

        for n in range(96):
            loaded[0xE72B - 0xE000 + n] = (n * 11 + i + 1) & 255
        var restored: PackedByteArray = ScratchSerializer.save_scratch_to_slot(
            loaded,slot)
        for n in range(96):
            _verify(restored[slot - 0xE000 + n] ==
                    loaded[0xE72B - 0xE000 + n],
                    "original reverse 48 PUSH words restore physical low slot")
        _verify(restored[slot - 0xE000 + 0xD7] == 0xBA and
                restored[slot - 0xE000 + 0x60] == 0x52,
                "original scratch serializer NEVER overwrites upper 160 slot bytes")
        _verify(ScratchSerializer.physical_slot_for_ix(slot + 0x80) == slot,
                "original Z80 IX remains 0x80 into six physical record slots")

    var table: PackedByteArray = PackedByteArray()
    for i in range(256):
        table.append((i * 57 + 113) & 255)

    # The original arithmetic prefix is now exercised between the same
    # master 61CE/629A scratch transfers the arcade uses. B/C/ROM
    # factors are caller-supplied; this is not a claim that all original
    # CALL 601E effects and track collisions have been recovered.
    for ix in CollisionRetry.CAR_POINTERS:
        var slot: int = ScratchSerializer.physical_slot_for_ix(ix)
        for low_branch in [false,true]:
            var original_ram: PackedByteArray = PackedByteArray()
            original_ram.resize(0x2000)
            original_ram.fill(0)
            # Physical low 96 bytes are the source of E72B..E78A.
            CollisionRetry._set16(original_ram,slot + 0x00,0xB000) # E72B Y
            CollisionRetry._set16(original_ram,slot + 0x0A,0x1000) # E735 X
            CollisionRetry._set16(original_ram,slot + 0x3C,0x2400) # E767
            CollisionRetry._set16(original_ram,slot + 0x3E,0x4000) # E769/E76A
            CollisionRetry._set16(original_ram,slot + 0x40,0x3F00) # E76B/E76C
            CollisionRetry._set16(original_ram,slot + 0x46,
                0x00FF if low_branch else 0x0100) # E771
            CollisionRetry._set16(original_ram,slot + 0x48,0x0200) # E773
            CollisionRetry._set16(original_ram,slot + 0x5E,0x0800) # E789
            original_ram[ix + 0x57 - 0xE000] = 16       # pedal IX+57
            original_ram[ix + 0x70 - 0xE000] = 130
            original_ram[ix + 0x71 - 0xE000] = 21
            original_ram[ix - 1 - 0xE000] = 255
            original_ram[ix + 0x79 - 0xE000] = 0x80
            original_ram[ix + 0x31 - 0xE000] = 0
            original_ram[ix + 0x41 - 0xE000] = 1
            original_ram[ix + 0x00 - 0xE000] = 0xC1
            original_ram[slot - 0xE000 + 0x63] = 0xAB
            original_ram[0xE600 - 0xE000] = 0xA6
            var previous: PackedByteArray = original_ram.duplicate()

            var complete: Dictionary = PhysicsPrefix.run_verified_original_slot_stage(
                original_ram,ix,0,0,0,0,table,255)
            _verify(complete["scratch_loaded"] and
                    complete["scratch_saved"] and complete["complete"] and
                    complete["next_pc"] == 0x75F1,
                    "original 48-word load → verified physics → 48-word save path")
            var changed: PackedByteArray = complete["ram"]
            for n in range(96):
                _verify(changed[slot - 0xE000 + n] ==
                        changed[0xE72B - 0xE000 + n],
                        "updated original per-car motion state persisted in physical slot")
            _verify(changed[ix + 0x57 - 0xE000] == 16 and
                    changed[slot - 0xE000 + 0x63] == 0xAB,
                    "original input/status bytes beyond first 96 preserved")
            _verify(changed[0xE600 - 0xE000] == 0xA6 and
                    original_ram == previous,
                    "original bounded slot model preserves unrelated working RAM and caller input")
            _verify(complete["physical_slot"] == slot,
                    "original selected IX maps the correct physical racing record")


func _test_original_714e_control_selector() -> void:
    # All source table bytes are synthetic. Actual original ROM/runtime
    # data are owner-supplied outside the public GitHub project.
    var fake_table: PackedByteArray = PackedByteArray()
    fake_table.resize(257)
    for n in range(257):
        fake_table[n] = (17 * n + 29) & 255

    var shortcut: Dictionary = DriveBC.select_bc(
        0x0100, 0x0100, 1, 3, 128, fake_table, 0xAB, 0xCD, 0)
    _verify(shortcut["next_pc"] == 0x7315 and
            shortcut["b"] == 0xAB and shortcut["c"] == 0xCD and
            not shortcut["overridden"],
            "original 714E shortcut goes directly to steering without table override")

    var inherited_borrow: Dictionary = DriveBC.select_bc(
        0x0100, 0x0100, 1, 3, 0, fake_table, 0xAB, 0xCD, 1)
    _verify(inherited_borrow["next_pc"] == 0x71C8 and
            inherited_borrow["path"] == "rotated_blend",
            "original 714E inherited carry changes 256 threshold routing")

    var direct: Dictionary = DriveBC.select_bc(
        0x0110, 0x00FF, 1, 19, 0, fake_table)
    _verify(direct["path"] == "direct_6f" and
            direct["b"] == (fake_table[38] >> 1) and
            direct["c"] == fake_table[39],
            "original 714E direct branch shifts B but not C")

    for index in range(128):
        var low: Dictionary = DriveBC.select_bc(
            0, 0, index, index, 0, fake_table)
        var high: Dictionary = DriveBC.select_bc(
            0, 0, index + 128, index + 128, 0, fake_table)
        _verify(low["b"] == high["b"] and low["c"] == high["c"] and
                low["path"] == "matching_indices",
                "original doubled byte selector aliases its upper 128 entries")

    for i in [0, 1, 127, 128, 255]:
        for j in [0, 1, 127, 128, 255]:
            var blend: Dictionary = DriveBC.select_bc(
                0, 0, i, j, 0, fake_table)
            var ai: int = (2 * i) & 255
            var aj: int = (2 * j) & 255
            var wanted_b: int = fake_table[ai]
            var wanted_c: int = fake_table[ai + 1]
            if i != j:
                var sum_b: int = (fake_table[ai] + fake_table[aj]) & 255
                var sum_c: int = (fake_table[ai + 1] + fake_table[aj + 1]) & 255
                wanted_b = ((sum_b >> 1) | ((sum_b & 1) << 7)) & 255
                wanted_c = ((sum_c >> 1) | ((sum_c & 1) << 7)) & 255
            _verify(blend["b"] == wanted_b and blend["c"] == wanted_c,
                    "original RRCA of wrapped byte sum, never an integer average")

    var override: Dictionary = DriveBC.select_bc(
        0, 0, 2, 5, 255, fake_table)
    _verify(override["overridden"] and
            override["b"] == fake_table[0] and
            override["c"] == fake_table[1],
            "original negative E76C overrides both physics B/C bytes")

    var master: PackedByteArray = PackedByteArray()
    master.resize(0x2000)
    master.fill(0)
    CollisionRetry._set16(master, 0xE76D, 0x0110)
    CollisionRetry._set16(master, 0xE76F, 0x00FF)
    var car: ArcadeCarRecord = Car.new()
    car.write_u8(0xEE, 1)
    car.write_u8(0xEF, 19)
    var selected: Dictionary = DriveBC.select_from_original_state(
        master, car, fake_table)
    _verify(selected["b"] == direct["b"] and
            selected["c"] == direct["c"] and
            selected["next_pc"] == 0x71C8,
            "physical slot+EE/+EF map to original Z80 IX+6E/+6F")

    CollisionRetry._set16(master, 0xE76D, 0x0100)
    CollisionRetry._set16(master, 0xE76F, 0x0100)
    var steer_table: PackedByteArray = PackedByteArray()
    steer_table.resize(256)
    steer_table.fill(0)
    var result: Dictionary = MotionChain.advance_using_verified_714e_selector(
        master, car, 0xE080, fake_table, 0,
        0xAB, 0xCD, 127, 127, steer_table, 127)
    _verify(result["original_714e_bypass"] and
            result["next_pc"] == 0x7530 and result["complete"] and
            CollisionRetry.get16(result["ram"],0xE76B) ==
            CollisionRetry.get16(master,0xE76B),
            "original bypass resumes at 7315 without preceding drive calculations")


func _test_original_7124_carry_and_714e_pipeline() -> void:
    # Exact 7124 E933 outgoing carry is the input carry of 714E.
    # No original proprietary tuning data or ROM samples in these tests.
    var motion: Dictionary = DriveCarry.calculate(0, 0, 0x1234)
    _verify(motion["e933"] == 4622 and motion["carry"] == 1 and
            motion["next_pc"] == 0x714E,
            "original 7124 X-ROM result and genuine outgoing CPU carry")
    _verify(motion["xrom"][0] == 0x127F and
            motion["xrom"][1] == 0x1A7F,
            "original two signed slot0 X-ROM lookup addresses")

    var zero: Dictionary = DriveCarry.calculate(0, 0, 0)
    _verify(zero["e933"] == 0 and zero["carry"] == 0,
            "original zero-motion path does not manufacture carry")

    var state: PackedByteArray = PackedByteArray()
    state.resize(0x2000)
    state.fill(0)
    CollisionRetry._set16(state, 0xE76B, 0x1234)
    CollisionRetry._set16(state, 0xE769, 0)
    CollisionRetry._set16(state, 0xE933, 0xFFFF)
    CollisionRetry._set16(state, 0xE76D, 0x0100)
    CollisionRetry._set16(state, 0xE76F, 0x0100)
    state[0xE600 - 0xE000] = 0xCE
    var entered: Dictionary = DriveCarry.apply_to_ram(state)
    _verify(entered["carry"] == 1 and
            CollisionRetry.get16(entered["ram"], 0xE933) == 4622,
            "authentic 7124 E933 write and flag-C from same state")
    _verify(CollisionRetry.get16(state, 0xE933) == 0xFFFF and
            state[0xE600 - 0xE000] == 0xCE,
            "7124 stage does not mutate input RAM or unrelated bytes")

    var table_257: PackedByteArray = PackedByteArray()
    table_257.resize(257)
    for i in range(257):
        table_257[i] = (17 * i + 29) & 255
    var car: ArcadeCarRecord = Car.new()
    car.write_u8(0xEE, 1)
    car.write_u8(0xEF, 19)
    var selection: Dictionary = DriveBC.select_from_original_state(
        entered["ram"], car, table_257, 0xAB, 0xCD, entered["carry"])
    _verify(selection["next_pc"] == 0x71C8 and
            selection["path"] == "rotated_blend",
            "7124 carried borrow forces original 714E blended B/C path")

    CollisionRetry._set16(state, 0xE76B, 0)
    CollisionRetry._set16(state, 0xE933, 0xFFFF)
    var steering_table: PackedByteArray = PackedByteArray()
    steering_table.resize(256)
    steering_table.fill(0)
    var bypass: Dictionary = MotionChain.advance_from_verified_7124_carry_source(
        state, car, 0xE080, table_257, 0xAB, 0xCD,
        127, 127, steering_table, 127)
    _verify(bypass["next_pc"] == 0x7530 and bypass["complete"] and
            bypass["original_714e_bypass"] and
            bypass["used_carry"] == 0,
            "real 7124 zero-carry gate resumes steering at 7315")
    _verify(CollisionRetry.get16(bypass["ram"], 0xE933) == 0 and
            CollisionRetry.get16(state, 0xE933) == 0xFFFF,
            "original 7124 E933 effect precedes 714E shortcut without mutating input")


func _test_original_7315_resume_equivalence() -> void:
    ## The same original 7315 input must give exactly the same output
    ## whether earlier 71C8–7314 ran normally or 714E jumped over it.
    ## Compare two independently composed routes over both steering exits.
    var table: PackedByteArray = PackedByteArray()
    for n in range(256):
        table.append((57 * n + 113) & 255)
    for ix in CollisionRetry.CAR_POINTERS:
        for low_steering in [false, true]:
            var master: PackedByteArray = PackedByteArray()
            master.resize(0x2000)
            master.fill(0)
            CollisionRetry._set16(master,0xE735,0x1000)
            CollisionRetry._set16(master,0xE72B,0xB000)
            CollisionRetry._set16(master,0xE767,0x2400)
            CollisionRetry._set16(master,0xE769,0x4000)
            CollisionRetry._set16(master,0xE76B,0x3F00)
            CollisionRetry._set16(master,0xE771,
                0x00FF if low_steering else 0x0100)
            CollisionRetry._set16(master,0xE773,0x0200)
            CollisionRetry._set16(master,0xE789,0x0800)
            master[ix + 0x70 - 0xE000] = 130
            master[ix + 0x71 - 0xE000] = 21
            master[ix - 1 - 0xE000] = 255
            master[ix + 0x79 - 0xE000] = 0x80
            master[ix + 0x31 - 0xE000] = 0
            master[ix + 0x41 - 0xE000] = 1
            master[ix + 0x00 - 0xE000] = 0xC1
            var car: ArcadeCarRecord = Car.new()
            car.write_u8(Car.FIELD_PEDAL_RESPONSE,16)
            var start: Dictionary = MotionChain.advance_through_original_angular_update(
                master,car,0,0,0,0)
            var existing: Dictionary = MotionChain.advance_through_original_steering_decay(
                master,car,ix,0,0,0,0,table,255)
            var resumed: Dictionary = MotionChain.advance_from_original_7315(
                start["ram"],ix,table,255)
            _verify(start["next_pc"] == 0x7315 and
                    existing["next_pc"] == 0x7530 and
                    resumed["next_pc"] == 0x7530 and
                    resumed["complete"] and
                    resumed["ram"] == existing["ram"],
                    "original 7315 resume matches existing full steering suffix")
            _verify(resumed["steering_7315"]["next_pc"] ==
                    (0x7376 if low_steering else 0x7530),
                    "original 7315 direct and low-threshold branches stay distinct")


func _test_original_slot_carry_selected_driving_pipeline() -> void:
    ## Composition test: the original six-slot serializer, authentic
    ## 7124 carry, 714E B/C selector and previously verified 71C8-75F0
    ## arithmetic must agree with the same independently staged calls.
    ## Synthetic table contents test the pipeline, NOT real-race parity.
    var source_table: PackedByteArray = PackedByteArray()
    source_table.resize(257)
    source_table.fill(0)
    source_table[2] = 8
    source_table[3] = 4
    var steering_table: PackedByteArray = PackedByteArray()
    steering_table.resize(256)
    steering_table.fill(0)

    for ix in CollisionRetry.CAR_POINTERS:
        var slot: int = ScratchSerializer.physical_slot_for_ix(ix)
        for carry_case in [true, false]:
            var original_ram: PackedByteArray = PackedByteArray()
            original_ram.resize(0x2000)
            original_ram.fill(0)
            CollisionRetry._set16(original_ram,slot + 0x00,0xB000)
            CollisionRetry._set16(original_ram,slot + 0x0A,0x1000)
            # E768 is the HIGH byte of the E767 word. Keep it zero
            # for the known cosine/carry test vector at heading zero.
            CollisionRetry._set16(original_ram,slot + 0x3C,0x0000)
            CollisionRetry._set16(original_ram,slot + 0x3E,0x0000)
            CollisionRetry._set16(original_ram,slot + 0x40,
                0x1234 if carry_case else 0)
            CollisionRetry._set16(original_ram,slot + 0x42,0x0100)
            CollisionRetry._set16(original_ram,slot + 0x44,0x0100)
            CollisionRetry._set16(original_ram,slot + 0x46,0x0100)
            CollisionRetry._set16(original_ram,slot + 0x48,0x0200)
            CollisionRetry._set16(original_ram,slot + 0x5E,0x0800)
            original_ram[ix + 0x57 - 0xE000] = 16
            original_ram[ix + 0x70 - 0xE000] = 1
            original_ram[ix + 0x71 - 0xE000] = 19
            original_ram[ix + 0x6E - 0xE000] = 1
            original_ram[ix + 0x6F - 0xE000] = 19
            original_ram[ix + 0x79 - 0xE000] = 0x80
            original_ram[0xE600 - 0xE000] = 0xC6
            CollisionRetry._set16(original_ram,0xE933,0xDEAD)
            var unchanged: PackedByteArray = original_ram.duplicate()

            var actual: Dictionary = PhysicsPrefix.run_verified_original_slot_from_7124(
                original_ram,ix,source_table,0xAB,0xCD,
                0,0,steering_table,255)
            var loaded: PackedByteArray = ScratchSerializer.load_slot_to_scratch(
                original_ram,slot)
            var projection: Dictionary = DriveCarry.apply_to_ram(loaded)
            var car: ArcadeCarRecord = Car.new(loaded.slice(
                slot - 0xE000,slot - 0xE000 + 256))
            var selected: Dictionary = DriveBC.select_from_original_state(
                projection["ram"],car,source_table,
                0xAB,0xCD,projection["carry"])

            _verify(projection["carry"] == int(carry_case),
                    "known original 7124 source vector exercises both carry values")
            _verify(actual["used_carry"] == projection["carry"] and
                    actual["bc_selection"]["next_pc"] == selected["next_pc"] and
                    actual["scratch_loaded"] and
                    actual["physical_slot"] == slot,
                    "per-slot original 7124 carry feeds genuine 714E selector")
            _verify(original_ram == unchanged and
                    CollisionRetry.get8(actual["ram"],0xE600) == 0xC6,
                    "verified original slot pipeline retains caller and unrelated RAM")

            if carry_case:
                _verify(selected["next_pc"] == 0x71C8 and
                        selected["b"] == 4 and selected["c"] == 2,
                        "authentic carried-borrow blend supplies nonzero B/C")
                var staged: Dictionary = PhysicsPrefix.run_verified_original_slot_stage(
                    projection["ram"],ix,selected["b"],selected["c"],
                    0,0,steering_table,255)
                _verify(actual["complete"] and actual["scratch_saved"] and
                        actual["next_pc"] == 0x75F1 and
                        actual["ram"] == staged["ram"],
                        "7124->714E->71C8->75F1 completes original 48-word storeback")
            else:
                var resumed: Dictionary = MotionChain.advance_from_original_7315(
                    projection["ram"],ix,steering_table,255)
                var movement: Dictionary = PhysicsPrefix.apply_original_7530_to_75f1(
                    resumed["ram"])
                var stored: PackedByteArray = ScratchSerializer.save_scratch_to_slot(
                    movement["ram"],slot)
                _verify(selected["next_pc"] == 0x7315 and
                        actual["complete"] and actual["scratch_saved"] and
                        actual["original_714e_bypass"] and
                        actual["next_pc"] == 0x75F1 and
                        CollisionRetry.get16(resumed["ram"],0xE76B) == 0 and
                        actual["ram"] == stored,
                        "original 7315 bypass completes geometry without invented drive motion")


func _test_original_709c_speed_stage() -> void:
    ## The original 709C stage consumes the original previous control B,
    ## current E765 word, indexed car bytes and the 2000–20FF ROM page.
    ## No generated steering, fuel, fabricated friction or track speed.
    var table: PackedByteArray = PackedByteArray()
    table.resize(256)
    table.fill(0)
    table[0] = 127
    var car: ArcadeCarRecord = Car.new()
    car.write_u8(0xBC, 0)  # original IX+3C source-table index
    car.write_u8(0xD4, 0)  # original IX+54 bias
    car.write_u8(0x60, 10) # original IX-20, plus-branch multiplier
    car.write_u8(0x61, 101)# original IX-1F, minus-branch multiplier
    var ram: PackedByteArray = PackedByteArray()
    ram.resize(CollisionRetry.LENGTH)
    ram.fill(0)

    CollisionRetry._set16(ram,0xE765,0x7F00)
    var before: PackedByteArray = ram.duplicate()
    var add: Dictionary = Speed709C.apply_original_709c(ram,car,255,table)
    _verify(add["branch"] == "add" and add["threshold_b"] == 165 and
            add["e765"] == 0x7FFF and add["next_pc"] == 0x7124,
            "original 709C positive speed addition saturates on Z80 overflow")
    _verify(CollisionRetry.get16(add["ram"],0xE765) == 0x7FFF and
            ram == before,"original E765 speed stage writes only cloned master RAM")

    CollisionRetry._set16(ram,0xE765,0x4000)
    car.write_u8(0xD4,10)
    car.write_u8(0x60,1)
    var normal: Dictionary = Speed709C.apply_original_709c(ram,car,120,table)
    _verify(normal["branch"] == "add" and normal["e765"] == 16471 and
            normal["b"] == 88,
            "original 709C normal 16-bit signed-slot0 correction")

    car.write_u8(0xD4,0)
    CollisionRetry._set16(ram,0xE765,0xFF00)
    var subtract: Dictionary = Speed709C.apply_original_709c(ram,car,0,table)
    _verify(subtract["branch"] == "subtract" and subtract["e765"] == 13244 and
            subtract["b"] == 255 and subtract["threshold_b"] == 0,
            "original 709C negative correction and prior-speed B difference")

    CollisionRetry._set16(ram,0xE765,0)
    table.fill(0)
    var equal: Dictionary = Speed709C.apply_original_709c(ram,car,0,table)
    _verify(equal["branch"] == "equal" and equal["e765"] == 0 and
            equal["next_pc"] == 0x7124,
            "original 709C equality bypass returns to original 7124")

    # All five original records share identical arithmetic, while the
    # caller must still supply its authentic physical slot and lookup page.
    for slot in range(5):
        car = Car.new()
        car.write_u8(0xD4,slot * 17)
        car.write_u8(0xBC,slot * 9)
        car.write_u8(0x60,slot * 53)
        car.write_u8(0x61,255 - slot * 37)
        for input_b in range(0,256,17):
            CollisionRetry._set16(ram,0xE765,(slot * 13291 + input_b * 241) & 65535)
            var value: Dictionary = Speed709C.apply_original_709c(ram,car,input_b,table)
            var threshold: int = min(255,((input_b * 166 + 128) >> 8) + slot * 17)
            _verify(value["threshold_b"] == threshold and
                    value["next_pc"] == 0x7124 and
                    CollisionRetry.get16(value["ram"],0xE765) == value["e765"],
                    "five-slot original 709C threshold and E765 store")


func _test_original_709c_to_per_car_slot() -> void:
    ## Independently compose each preloaded original slot: ROM-free
    ## 709C speed, 7124 projection, 714E selector and 75F1 storeback.
    var speed_table: PackedByteArray = PackedByteArray()
    speed_table.resize(256)
    var select_table: PackedByteArray = PackedByteArray()
    select_table.resize(257)
    var steer_table: PackedByteArray = PackedByteArray()
    steer_table.resize(256)
    for i in range(256):
        speed_table[i] = (i * 71 + 33) & 255
        select_table[i] = (i * 19 + 17) & 255
        steer_table[i] = (i * 53 + 99) & 255
    select_table[256] = 14

    for index in range(5):
        var original_ix: int = CollisionRetry.CAR_POINTERS[index]
        var slot: int = ScratchSerializer.physical_slot_for_ix(original_ix)
        for bypass in [false,true]:
            var ram: PackedByteArray = PackedByteArray()
            ram.resize(CollisionRetry.LENGTH)
            ram.fill(0)
            CollisionRetry._set8(ram,slot + 0xBC,12 + index)
            CollisionRetry._set8(ram,slot + 0xD4,30 + index * 7)
            CollisionRetry._set8(ram,slot + 0x60,75 + index)
            CollisionRetry._set8(ram,slot + 0x61,102 + index)
            CollisionRetry._set8(ram,slot + 0xD7,32)  # pedal response
            CollisionRetry._set8(ram,slot + 0xEE,3)
            CollisionRetry._set8(ram,slot + 0xEF,7)
            CollisionRetry._set16(ram,slot + 0x3A,0x3200 + index * 219)
            CollisionRetry._set16(ram,slot + 0x42,0x0130 if bypass else 0)
            CollisionRetry._set16(ram,slot + 0x44,0x0140 if bypass else 0)
            var initial_snapshot: PackedByteArray = ram.duplicate()

            var prepared: PackedByteArray = ScratchSerializer.load_slot_to_scratch(ram,slot)
            var car_bytes: PackedByteArray = prepared.slice(
                slot - CollisionRetry.BASE,
                slot - CollisionRetry.BASE + ScratchSerializer.ORIGINAL_SLOT_LENGTH)
            var car: ArcadeCarRecord = Car.new(car_bytes)
            var speed: Dictionary = Speed709C.apply_original_709c(
                prepared,car,53 + index,speed_table)
            var projection: Dictionary = DriveCarry.apply_to_ram(speed["ram"])
            var selected: Dictionary = MotionChain.advance_from_verified_7124_carry_source(
                speed["ram"],car,original_ix,select_table,
                speed["b"],projection["cos"],33,27,steer_table,19)

            var actual: Dictionary = PhysicsPrefix.run_verified_original_slot_from_709c(
                ram,original_ix,53 + index,speed_table,select_table,
                33,27,steer_table,19)
            _verify(actual["original_speed_709c"]["e765"] == speed["e765"] and
                    actual["original_speed_709c"]["threshold_b"] == speed["threshold_b"] and
                    ram == initial_snapshot,
                    "original 709C stage composes without mutating five source records")
            _verify(actual["used_carry"] == selected["used_carry"] and
                    actual["original_714e_bypass"] == selected["original_714e_bypass"],
                    "original speed register B and projected C reach real 714E selector")
            if selected["next_pc"] == 0x7530:
                var moved: Dictionary = PhysicsPrefix.apply_original_7530_to_75f1(selected["ram"])
                var expected_ram: PackedByteArray = ScratchSerializer.save_scratch_to_slot(
                    moved["ram"],slot)
                _verify(actual["ram"] == expected_ram and actual["next_pc"] == 0x75F1 and
                        actual["scratch_saved"] and actual["complete"],
                        "original 709C update commits through 75F1 storeback")
            else:
                _verify(selected["next_pc"] == 0x1689 and
                        actual["next_pc"] == 0x1689 and
                        not actual["scratch_saved"] and not actual["complete"],
                        "original 1689 escape stops without fabricating a slot save")


func _test_original_7049_slow_stage() -> void:
    for index in range(5):
        var ix: int = CollisionRetry.CAR_POINTERS[index]
        for route in ["no_borrow", "borrow", "bit4", "external_7e5e", "external_2ad1"]:
            var ram: PackedByteArray = PackedByteArray()
            ram.resize(CollisionRetry.LENGTH)
            ram.fill(0)
            var borrow: bool = route != "no_borrow"
            var source_b: int = 255 if borrow else 0
            CollisionRetry._set16(ram,0xE765,0x7FFF if borrow else 0)
            CollisionRetry._set8(ram,ix + 0x3B,255)
            CollisionRetry._set8(ram,ix + 0x39,0 if borrow else 201)
            CollisionRetry._set8(ram,ix + 0x3A,
                1 if route == "bit4" else (3 if route.begins_with("external") else 7))
            CollisionRetry._set8(ram,ix + 0x31,0x81 if route == "bit4" else 0)
            CollisionRetry._set8(ram,ix - 3,2 if route == "external_2ad1" else 3)
            CollisionRetry._set8(ram,0xE94D,3 if route == "external_7e5e" else 0)
            var snapshot: PackedByteArray = ram.duplicate()
            var result: Dictionary = Slow7049.apply_from_original_7049(ram,ix,source_b)
            _verify(snapshot == ram and result["b"] == source_b and
                    result["subtrahend"] == (157 if borrow else 16),
                    "original 7049 stage has immutable inputs and authentic X-ROM LOW")
            _verify(CollisionRetry.get8(result["ram"],ix + 0x39) ==
                    (99 if borrow else 185),
                    "original 7049 writes the original IX+39 decrement")
            if route == "no_borrow":
                _verify(result["next_pc"] == 0x709C and result["complete"] and
                        CollisionRetry.get8(result["ram"],ix + 0x3A) == 7,
                        "original 7049 no-borrow continues at 709C")
            elif route == "borrow":
                _verify(result["next_pc"] == 0x709C and result["complete"] and
                        CollisionRetry.get8(result["ram"],ix + 0x3A) == 6,
                        "original 7049 normal borrow adjusts high byte and continues")
            elif route == "bit4":
                _verify(result["next_pc"] == 0x709C and result["complete"] and
                        CollisionRetry.get8(result["ram"],ix + 0x3A) == 0 and
                        CollisionRetry.get8(result["ram"],ix + 0x31) == 0x91,
                        "original 7049 zero high byte sets physical-car status bit")
            elif route == "external_7e5e":
                _verify(result["next_pc"] == 0x7E5E and not result["complete"] and
                        CollisionRetry.get8(result["ram"],ix + 0x3A) == 2,
                        "original 7049 stops before unknown 7E5E call")
            else:
                _verify(result["next_pc"] == 0x2AD1 and not result["complete"] and
                        CollisionRetry.get8(result["ram"],ix + 0x3A) == 2,
                        "original 7049 stops before unknown 2AD1 call")


func _test_original_7e5e_early_returns_stage() -> void:
    for index in range(5):
        var ix: int = CollisionRetry.CAR_POINTERS[index]
        for route in ["return_flag", "return_special", "return_equal",
                      "return_neighbor", "dispatch_7ea3"]:
            var ram: PackedByteArray = PackedByteArray()
            ram.resize(CollisionRetry.LENGTH)
            ram.fill(0)
            CollisionRetry._set8(ram,ix + 0x31,0x40 if route == "return_flag" else 0)
            CollisionRetry._set8(ram,0xE603,1 if route == "dispatch_7ea3" else 0)
            CollisionRetry._set8(ram,ix - 3,4 if route == "return_special" else 3)
            CollisionRetry._set8(ram,0xE602,0)
            CollisionRetry._set8(ram,0xE674,1)
            CollisionRetry._set8(ram,0xE638,128)
            CollisionRetry._set8(ram,0xE639,11 if route == "return_neighbor" else 10)
            CollisionRetry._set8(ram,ix + 2,10)
            CollisionRetry._set8(ram,ix + 0x51,30)
            CollisionRetry._set8(ram,ix + 0x3A,3)
            var before: PackedByteArray = ram.duplicate()
            var actual: Dictionary = External7E5E.apply_from_original_call(ram,ix)
            _verify(ram == before and actual["branch"] == route and
                    actual["next_pc"] == (0x7EA3 if route == "dispatch_7ea3" else 0x7091) and
                    actual["complete"] == (route != "dispatch_7ea3"),
                    "original 7E5E authentic early-return and opaque-dispatch routing")
            _verify(CollisionRetry.get8(actual["ram"],ix + 0x3A) ==
                    (0x48 if route == "return_special" else 3),
                    "original 7E5E only modifies physical high byte on signed special return")


func _test_original_2ad1_original_bit_gate() -> void:
    for index in range(5):
        var ix: int = CollisionRetry.CAR_POINTERS[index]
        for status in [0, 1, 0xA4, 0xEF]:
            var ram: PackedByteArray = PackedByteArray()
            ram.resize(CollisionRetry.LENGTH)
            ram.fill(0xA5)
            CollisionRetry._set8(ram,ix + 0x31,status)
            var before: PackedByteArray = ram.duplicate()
            var actual: Dictionary = External2AD1.apply_from_original_call(ram,ix)
            var accepted: bool = (status & 1) != 0
            _verify(actual["ram"] == before and ram == before and
                    actual["next_pc"] == (0x709B if accepted else 0x2AD6) and
                    actual["complete"] == accepted,
                    "original 2AD1 ROM BIT0 branch returns safely or stops before banked events")


func _test_original_7d65_smoothing_stage() -> void:
    for index in range(5):
        var ix: int = CollisionRetry.CAR_POINTERS[index]
        var ram: PackedByteArray = PackedByteArray()
        ram.resize(CollisionRetry.LENGTH)
        ram.fill(0)
        CollisionRetry._set16(ram,ix + 0x65,0x1010)
        CollisionRetry._set16(ram,ix + 0x67,0x1FF0)
        CollisionRetry._set16(ram,0xE72B,0x1000)
        CollisionRetry._set16(ram,0xE735,0x2000)
        CollisionRetry._set8(ram,0xE93B,0x20)
        CollisionRetry._set16(ram,0xE767,0x1000)
        CollisionRetry._set16(ram,0xE769,0x9999)
        CollisionRetry._set16(ram,0xE76B,0x0200)
        CollisionRetry._set16(ram,0xE765,0x1000)
        var before: PackedByteArray = ram.duplicate()
        var result: Dictionary = Smooth7D65.apply_after_original_7d4c(ram,ix)
        var updated: PackedByteArray = result["ram"]
        _verify(ram == before and result["branch"] == "smooth_7024" and
                result["next_pc"] == 0x7024 and result["complete"],
                "original 7D65 complete smoothing returns to actual 7024 without mutating caller")
        _verify(CollisionRetry.get16(updated,0xE72B) == 0x1002 and
                CollisionRetry.get16(updated,0xE735) == 0x1FFE,
                "original 7D65 signed Y/X interpolation uses original integer rounding")
        _verify(CollisionRetry.get16(updated,0xE767) == 0x1180 and
                CollisionRetry.get16(updated,0xE769) == 0x1180,
                "original 7D65 writes equal heading words with 12/128 projection")
        _verify(CollisionRetry.get16(updated,0xE76B) == 0x01D0 and
                CollisionRetry.get16(updated,0xE765) == 0x0E80,
                "original 7D65 independently decays both movement and speed words")


func _test_original_701a_gate_and_7017_fast_path() -> void:
    var speed_table: PackedByteArray = PackedByteArray()
    speed_table.resize(256)
    var select_table: PackedByteArray = PackedByteArray()
    select_table.resize(257)
    var steer_table: PackedByteArray = PackedByteArray()
    steer_table.resize(256)
    for k in range(256):
        speed_table[k] = (k * 17 + 31) & 255
        select_table[k] = (k * 7 + 63) & 255
        steer_table[k] = (k * 37 + 5) & 255
    select_table[256] = 203

    for index in range(5):
        var ix: int = CollisionRetry.CAR_POINTERS[index]
        var slot: int = ScratchSerializer.physical_slot_for_ix(ix)
        for route in ["fast", "slow", "slow_7e5e", "slow_7e5e_return",
                      "slow_7e5e_flag_return", "slow_7e5e_special_return",
                      "slow_7e5e_return_to_2ad1", "slow_7e5e_return_to_2ad1_return",
                      "slow_2ad1", "slow_2ad1_return",
                      "special", "special_direct"]:
            var ram: PackedByteArray = PackedByteArray()
            ram.resize(CollisionRetry.LENGTH)
            ram.fill(0)
            CollisionRetry._set8(ram,ix + 0x5C,
                3 if route == "special_direct" else (1 if route == "special" else 0))
            CollisionRetry._set8(ram,ix + 0x31,0x10 if route == "fast" else 0)
            CollisionRetry._set8(ram,ix + 0x33,0)
            CollisionRetry._set8(ram,ix + 0x57,255 - index * 21)
            CollisionRetry._set8(ram,ix - 0x1D,255 if route == "fast" else 0xA7)
            CollisionRetry._set8(ram,slot + 0xBC,index * 4 + 1)
            CollisionRetry._set8(ram,slot + 0xD4,54 + index)
            CollisionRetry._set8(ram,slot + 0x60,88)
            CollisionRetry._set8(ram,slot + 0x61,67)
            CollisionRetry._set16(ram,slot + 0x3A,0x1245 + index * 422)
            CollisionRetry._set8(ram,slot + 0xEE,3)
            CollisionRetry._set8(ram,slot + 0xEF,3)
            CollisionRetry._set16(ram,ix + 0x65,0x1122 + index * 7)
            CollisionRetry._set16(ram,ix + 0x67,0x3344 + index * 11)
            if route.begins_with("slow_"):
                CollisionRetry._set16(ram,slot + 0x3A,0x7FFF)
                CollisionRetry._set8(ram,ix + 0x3B,255)
                CollisionRetry._set8(ram,ix + 0x39,0)
                CollisionRetry._set8(ram,ix + 0x3A,3)
                CollisionRetry._set8(ram,ix - 3,
                    2 if route in ["slow_2ad1", "slow_2ad1_return",
                    "slow_7e5e_return_to_2ad1", "slow_7e5e_return_to_2ad1_return"] else 3)
                CollisionRetry._set8(ram,0xE94D,3 if route == "slow_7e5e" else 0)
                if route.begins_with("slow_7e5e"):
                    CollisionRetry._set8(ram,0xE94D,3)
                    CollisionRetry._set8(ram,0xE603,1 if route == "slow_7e5e" else 0)
                if route == "slow_7e5e_flag_return":
                    CollisionRetry._set8(ram,ix + 0x31,0x40)
                if route == "slow_7e5e_special_return":
                    CollisionRetry._set8(ram,ix - 3,4)
                    CollisionRetry._set8(ram,0xE638,128)
                    CollisionRetry._set8(ram,0xE602,0)
                    CollisionRetry._set8(ram,0xE674,1)
                if route in ["slow_2ad1_return", "slow_7e5e_return_to_2ad1_return"]:
                    CollisionRetry._set8(ram,ix + 0x31,
                        CollisionRetry.get8(ram,ix + 0x31) | 1)
            var original: PackedByteArray = ram.duplicate()
            var prepared: PackedByteArray = ScratchSerializer.load_slot_to_scratch(ram,slot)
            var checkpoint: Dictionary = CollisionCheckpoint.snapshot(prepared)
            var preflight: Dictionary = Gate701A.apply_after_75f2(checkpoint["ram"],ix)
            var actual: Dictionary = PhysicsPrefix.run_verified_original_slot_from_7017(
                ram,ix,speed_table,select_table,33,27,steer_table,19)
            _verify(original == ram and actual["checkpoint_75f2"]["original_saved_words"] == 11 and
                    actual["preflight_701a"]["branch"] == preflight["branch"],
                    "original 7017 checkpoint precedes 701A five-slot gate")

            if route == "fast":
                _verify(preflight["next_pc"] == 0x709C and preflight["counter"] == 0 and
                        preflight["b"] == ((255 - index * 21) * 96 + 128) >> 8,
                        "original fast pedal slot1 multiplication and counter wrap")
                var car_bytes: PackedByteArray = preflight["ram"].slice(
                    slot - CollisionRetry.BASE,
                    slot - CollisionRetry.BASE + ScratchSerializer.ORIGINAL_SLOT_LENGTH)
                var car: ArcadeCarRecord = Car.new(car_bytes)
                var speed: Dictionary = Speed709C.apply_original_709c(
                    preflight["ram"],car,preflight["b"],speed_table)
                var source: Dictionary = DriveCarry.apply_to_ram(speed["ram"])
                var selected: Dictionary = MotionChain.advance_from_verified_7124_carry_source(
                    speed["ram"],car,ix,select_table,speed["b"],source["cos"],
                    33,27,steer_table,19)
                _verify(actual["preflight_701a"]["b"] == preflight["b"] and
                        actual["original_speed_709c"]["e765"] == speed["e765"] and
                        actual["used_carry"] == selected["used_carry"],
                        "original 7017 fast route supplies authentic B to 709C and 714E")
                if selected["next_pc"] == 0x7530:
                    var moved: Dictionary = PhysicsPrefix.apply_original_7530_to_75f1(selected["ram"])
                    var stored: PackedByteArray = ScratchSerializer.save_scratch_to_slot(moved["ram"],slot)
                    _verify(actual["ram"] == stored and actual["scratch_saved"] and
                            actual["next_pc"] == 0x75F1,
                            "original 7017 fast branch completes correct 75F1 save")
                else:
                    _verify(actual["next_pc"] == 0x1689 and not actual["scratch_saved"],
                            "original 7017 branch preserves nonlocal 1689 escape")
            elif route == "slow":
                var original_slow: Dictionary = Slow7049.apply_from_original_7049(
                    preflight["ram"],ix,preflight["b"])
                _verify(preflight["next_pc"] == 0x7049 and
                        original_slow["next_pc"] == 0x709C and
                        actual["original_slow_7049"]["next_pc"] == 0x709C and
                        CollisionRetry.get8(actual["ram"],ix - 0x1D) == 0,
                        "original 701A slow route reaches genuine 7049 arithmetic and 709C")
                var slower_car_bytes: PackedByteArray = original_slow["ram"].slice(
                    slot - CollisionRetry.BASE,
                    slot - CollisionRetry.BASE + ScratchSerializer.ORIGINAL_SLOT_LENGTH)
                var slower_car: ArcadeCarRecord = Car.new(slower_car_bytes)
                var slower_speed: Dictionary = Speed709C.apply_original_709c(
                    original_slow["ram"],slower_car,original_slow["b"],speed_table)
                _verify(actual["original_speed_709c"]["e765"] == slower_speed["e765"],
                        "original 7049 slow path sends inherited B into verified 709C speed")
                _verify(actual["next_pc"] in [0x75F1,0x1689] and
                        (actual["scratch_saved"] == (actual["next_pc"] == 0x75F1)),
                        "original 7049 normal branch preserves 75F1 or 1689 termination")
            elif route in ["slow_7e5e", "slow_2ad1"]:
                var target: int = 0x7EA3 if route == "slow_7e5e" else 0x2AD6
                _verify(preflight["next_pc"] == 0x7049 and
                        actual["next_pc"] == target and not actual["complete"] and
                        not actual["scratch_saved"] and
                        actual["original_slow_7049"]["next_pc"] ==
                            (0x7E5E if route == "slow_7e5e" else 0x2AD1) and
                        CollisionRetry.get8(actual["ram"],ix + 0x3A) == 2,
                        "original 7049 stops safely at 7EA3 or banked 2AD6 dispatch")
            elif route == "slow_7e5e_return_to_2ad1":
                _verify(actual["original_slow_7049"]["next_pc"] == 0x7E5E and
                        actual["original_external_7e5e"]["branch"] == "return_equal" and
                        actual["original_external_2ad1"]["next_pc"] == 0x2AD6 and
                        actual["next_pc"] == 0x2AD6 and not actual["complete"] and
                        not actual["scratch_saved"],
                        "original returned 7E5E exposes real 7098 CP03/2AD1 event gate")
            elif route in ["slow_2ad1_return", "slow_7e5e_return_to_2ad1_return"]:
                _verify(actual["original_external_2ad1"]["branch"] == "return_709b" and
                        actual["original_external_2ad1"]["next_pc"] == 0x709B and
                        actual["next_pc"] in [0x75F1,0x1689] and
                        (actual["scratch_saved"] == (actual["next_pc"] == 0x75F1)),
                        "original 2AD1 bit0 early return resumes real 709B POP BC/709C")
            elif route.begins_with("slow_7e5e_"):
                var expected_early_return: String = (
                    "return_special" if route == "slow_7e5e_special_return" else
                    "return_flag" if route == "slow_7e5e_flag_return" else
                    "return_equal")
                _verify(actual["original_slow_7049"]["next_pc"] == 0x7E5E and
                        actual["original_external_7e5e"]["branch"] == expected_early_return and
                        actual["original_external_7e5e"]["next_pc"] == 0x7091 and
                        actual["next_pc"] in [0x75F1,0x1689] and
                        (actual["scratch_saved"] == (actual["next_pc"] == 0x75F1)),
                        "original 7E5E bounded return resumes 7091 POP BC and 709C")
                _verify(CollisionRetry.get8(actual["ram"],ix + 0x3A) ==
                        (0x48 if route == "slow_7e5e_special_return" else 2),
                        "original returned 7E5E changes only real indexed car bytes")
            elif route == "special":
                var intermediate: Dictionary = Special7D4C.apply_from_original_call(
                    preflight["ram"],ix)
                var smoothed: Dictionary = Smooth7D65.apply_after_original_7d4c(
                    intermediate["ram"],ix)
                var smooth_geom: Dictionary = PhysicsPrefix.apply_original_7572_geometry_only(
                    smoothed["ram"])
                var expected_smooth_ram: PackedByteArray = ScratchSerializer.save_scratch_to_slot(
                    smooth_geom["ram"],slot)
                _verify(intermediate["next_pc"] == 0x7D65 and
                        smoothed["next_pc"] == 0x7024 and
                        actual["original_smoothing_7d65"]["e765"] == smoothed["e765"] and
                        actual["original_speed_709c"].is_empty() and
                        actual["next_pc"] == 0x75F1 and actual["complete"] and
                        actual["scratch_saved"] and actual["ram"] == expected_smooth_ram,
                        "original 7D4C smoothing branch returns via 7024/7572 without 709C")
            else:
                var direct: Dictionary = Special7D4C.apply_from_original_call(
                    preflight["ram"],ix)
                var geom: Dictionary = PhysicsPrefix.apply_original_7572_geometry_only(
                    direct["ram"])
                var expected_ram: PackedByteArray = ScratchSerializer.save_scratch_to_slot(
                    geom["ram"],slot)
                _verify(direct["next_pc"] == 0x7024 and
                        actual["original_special_7d4c"]["branch"] == "direct_7024" and
                        actual["next_pc"] == 0x75F1 and actual["complete"] and
                        actual["scratch_saved"] and actual["ram"] == expected_ram,
                        "original special 7D4C direct-centre branch resumes authentic 7572 geometry")


func _test_original_geometry_checkpoint_and_restore() -> void:
    ## Genuine original 75F2-7634 saves 11 independent words.
    ## Original BC8C/C468 fallback restores them later. The caller,
    ## not this helper, owns the original collision call scheduling.
    var input_ram: PackedByteArray = PackedByteArray()
    input_ram.resize(0x2000)
    input_ram.fill(0xA5)
    var golden: Dictionary = {}
    for index in range(CollisionCheckpoint.SOURCE_TO_BACKUP.size()):
        var pair: Array = CollisionCheckpoint.SOURCE_TO_BACKUP[index]
        var word: int = (0x9A50 + index * 381) & 65535
        CollisionRetry._set16(input_ram, pair[0], word)
        CollisionRetry._set16(input_ram, pair[1], 0x1234)
        golden[pair[0]] = word

    var before: PackedByteArray = input_ram.duplicate()
    var checkpoint: Dictionary = CollisionCheckpoint.snapshot(input_ram)
    var saved: PackedByteArray = checkpoint["ram"]
    _verify(checkpoint["original_saved_words"] == 11 and
            checkpoint["next_pc"] == 0x7634 and
            checkpoint["writes"].size() == 11,
            "original 75F2 saves all 11 words and returns at 7634")
    for pair in CollisionCheckpoint.SOURCE_TO_BACKUP:
        _verify(CollisionRetry.get16(saved, pair[1]) == golden[pair[0]],
                "original collision checkpoint copy matches exact source")
    _verify(input_ram == before,
            "original geometry checkpoint returns a snapshot without mutating input")

    var collided: PackedByteArray = saved.duplicate()
    for pair in CollisionCheckpoint.SOURCE_TO_BACKUP:
        CollisionRetry._set16(collided, pair[0], 0)
    collided[0xE92E - 0xE000] = 17
    var original_reset: Dictionary = CollisionRetry.retry(collided, 0xE080)
    var final_state: PackedByteArray = original_reset["ram"]
    _verify(original_reset["next_pc"] == 0xBC9E and
            original_reset["words_restored"] == 11,
            "authentic count18 triggers original 11-word rollback")
    for pair in CollisionCheckpoint.SOURCE_TO_BACKUP:
        _verify(CollisionRetry.get16(final_state, pair[0]) == golden[pair[0]],
                "original 75F2 checkpoint survives genuine C468 state restoration")
    _verify(CollisionRetry.get16(collided, 0xE72B) == 0,
            "original rollback does not mutate the pre-reset memory buffer")


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
