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
    fresh[0xE768 - 0xE000] = 0xD6
    for n in range(CollisionRetry.COPY_PAIRS.size()):
        var pair: Array = CollisionRetry.COPY_PAIRS[n]
        var saved_word: int = (0x1234 + 0x0137 * n) & 0xFFFF
        fresh[pair[0] - 0xE000] = saved_word & 255
        fresh[pair[0] - 0xE000 + 1] = saved_word >> 8
        fresh[pair[1] - 0xE000] = 0
        fresh[pair[1] - 0xE000 + 1] = 0

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
