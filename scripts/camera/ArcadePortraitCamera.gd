class_name ArcadePortraitCamera
extends Camera2D

## Presentation-only camera for Indy Carz.
## Keeps original arcade circuit geometry, positions, orientation and scale.
## Adds gentle bounded follow-pan for portrait phones / Fold closed mode.
## Does NOT change racing speed, physics, coordinates or track layout.
##
## Set follow_target to the player car and call configure_track_bounds()
## after the original circuit has been reconstructed in world coordinates.

@export var follow_target: Node2D
@export_range(0.05, 0.45, 0.01) var deadzone_x_fraction: float = 0.25
@export_range(0.05, 0.45, 0.01) var deadzone_y_fraction: float = 0.27
@export_range(0.15, 0.47, 0.01) var visibility_limit_fraction: float = 0.43
@export_range(0.1, 10.0, 0.1) var follow_smoothing: float = 3.0
@export_range(0.0, 0.5, 0.01) var lookahead_seconds: float = 0.12

var _bounds: Rect2 = Rect2()
var _bounds_available: bool = false
var _last_target_position: Vector2 = Vector2.ZERO
var _initialized_target: bool = false


func configure_track_bounds(original_track_bounds: Rect2) -> void:
    # Bounds must describe the ORIGINAL track/world; never rescale tracks
    # to achieve a better portrait fit.
    _bounds = original_track_bounds
    _bounds_available = (
        original_track_bounds.size.x > 0.0 and original_track_bounds.size.y > 0.0
    )


func _physics_process(delta: float) -> void:
    if not is_instance_valid(follow_target) or delta <= 0.0:
        return

    var target: Vector2 = follow_target.global_position
    if not _initialized_target:
        _last_target_position = target
        global_position = _clamp_to_original_bounds(target)
        _initialized_target = true
        return

    var target_velocity: Vector2 = (target - _last_target_position) / delta
    _last_target_position = target
    var screen_half: Vector2 = _visible_world_half_extents()
    var deadzone: Vector2 = screen_half * Vector2(
        deadzone_x_fraction, deadzone_y_fraction
    ) * 2.0

    var predicted: Vector2 = target + (
        target_velocity * lookahead_seconds
    ).limit_length(screen_half.length() * 0.15)
    var offset: Vector2 = predicted - global_position
    var desired: Vector2 = global_position

    if absf(offset.x) > deadzone.x:
        desired.x += offset.x - signf(offset.x) * deadzone.x
    if absf(offset.y) > deadzone.y:
        desired.y += offset.y - signf(offset.y) * deadzone.y

    desired = _clamp_to_original_bounds(desired)
    var blend: float = 1.0 - exp(-follow_smoothing * delta)
    var next_camera: Vector2 = global_position.lerp(desired, blend)

    # Safety: keep the player within the viewport even during original
    # turbo boosts. This may override gentle motion to avoid losing the car.
    var safety_half: Vector2 = screen_half * (visibility_limit_fraction * 2.0)
    var relative: Vector2 = target - next_camera
    if relative.x > safety_half.x:
        next_camera.x += relative.x - safety_half.x
    elif relative.x < -safety_half.x:
        next_camera.x += relative.x + safety_half.x
    if relative.y > safety_half.y:
        next_camera.y += relative.y - safety_half.y
    elif relative.y < -safety_half.y:
        next_camera.y += relative.y + safety_half.y

    global_position = _clamp_to_original_bounds(next_camera)


func _visible_world_half_extents() -> Vector2:
    var size: Vector2 = get_viewport_rect().size
    return Vector2(
        size.x / maxf(absf(zoom.x), 0.001),
        size.y / maxf(absf(zoom.y), 0.001)
    ) * 0.5


func _clamp_to_original_bounds(candidate: Vector2) -> Vector2:
    if not _bounds_available:
        return candidate
    var half: Vector2 = _visible_world_half_extents()
    var center: Vector2 = _bounds.position + _bounds.size * 0.5
    var result: Vector2 = candidate

    if _bounds.size.x <= half.x * 2.0:
        result.x = center.x
    else:
        result.x = clampf(candidate.x, _bounds.position.x + half.x,
                          _bounds.end.x - half.x)

    if _bounds.size.y <= half.y * 2.0:
        result.y = center.y
    else:
        result.y = clampf(candidate.y, _bounds.position.y + half.y,
                          _bounds.end.y - half.y)
    return result
