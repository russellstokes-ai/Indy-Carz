extends SceneTree

# Godot 4.4 headless functional checks — no original ROMs, reconstructed
# copyrighted binary blobs, track sprites or speculative car physics needed.
# This intentionally verifies only the recovered input stages and camera pan.

const Wheel = preload("res://scripts/mechanics/ArcadeWheelInput.gd")
const Steering = preload("res://scripts/mechanics/ArcadeSteeringState.gd")
const Pedal = preload("res://scripts/mechanics/ArcadePedalInput.gd")
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
