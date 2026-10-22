class_name ArcadeSteeringState
extends RefCounted

## Two verified, independent steering-state stages reconstructed from the
## original 1991 Indy Heat arcade Z80 executable.
##
## ORIGINAL BANK 0: master CPU $341E, X-ROM input (IX+$7A) and state (IX+$7B)
## ORIGINAL BANK 3: master CPU $7519, direct input (IX+$79), state (IX+$7B)
##
## This module *only* computes the accumulator change and whether the
## original branch into additional handling is taken. Calling that branch
## a collision, or treating this as complete vehicle yaw, is premature.
##
## Local parity harness compared 20,992 cases against actual Z80 bytecode
## using the authenticated 1991 ROM: 0 accumulator-value mismatches.

enum Path {
    XROM_BANK_0,
    DIRECT_BANK_3,
}

const VALID_MAGNITUDES := [
    0, 12, 20, 26, 30, 32, 34, 36, 38, 40,
    42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 62,
]


static func _xrom_steer_upper_byte(original_input: int) -> int:
    # For all 41 response values reachable from the arcade steering LUT,
    # the original X-ROM lookup at (response << 8 | $7F) has this output.
    # Outside these values, exact X-ROM behaviour is unverified.
    assert(VALID_MAGNITUDES.has(absi(original_input)), "Unverified steering sample")
    var mapped: int = original_input - 1 if original_input > 0 else original_input
    return mapped & 0xFF


static func advance(original_input: int, previous_state: int, path: Path) -> Dictionary:
    assert(previous_state >= 0 and previous_state <= 255, "8-bit original state required")
    var steering_step: int
    var centring_bias: int

    if path == Path.XROM_BANK_0:
        steering_step = (_xrom_steer_upper_byte(original_input) * 2) & 0xFF
        centring_bias = 4
    elif path == Path.DIRECT_BANK_3:
        assert(original_input >= -128 and original_input <= 127, "8-bit input required")
        steering_step = (original_input * 2) & 0xFF
        centring_bias = 8
    else:
        assert(false, "Unknown arcade steering path")
        return {}

    var unwrapped: int = steering_step + previous_state
    var updated: int = unwrapped & 0xFF
    var carry: bool = unwrapped > 255
    var step_negative: bool = (steering_step & 0x80) != 0

    # Branch results directly reflect the Z80 ADD/CARRY/JP M/JR NC
    # chain at $341E...$344B or $7519...$754D.
    var branch_taken: bool = (
        (step_negative and not carry) or
        (not step_negative and carry)
    )
    if branch_taken:
        updated ^= 0x80
    elif (updated & 0x80) != 0:
        updated = (updated - centring_bias) & 0xFF
    else:
        updated = (updated + centring_bias) & 0xFF

    return {
        "state_byte": updated,
        "overflow_branch": branch_taken,
        "pre_bias_step": steering_step,
        "source": path,
    }
