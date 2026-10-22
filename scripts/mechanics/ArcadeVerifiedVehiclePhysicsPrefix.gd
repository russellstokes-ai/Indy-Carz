class_name ArcadeVerifiedVehiclePhysicsPrefix
extends RefCounted

## BOUNDED, original-compatible arcade Z80 CPU pipeline: master 71C8
## through the movement and vehicle geometry stage ending at 75F1.
##
## All arithmetic stages in this chain were independently verified
## against the user's original 1991 Indy Heat rev1 Z80 and signed XROM:
##   71C8–752F input/acceleration/steering routing and angular updates
##   7530–7571 original trig/XROM coordinate integration
##   7572–75F0 original eight-word oriented collision footprint
##
## The game runs these later stages against SHARED E72B/E735/E76A
## working RAM, NOT directly against the physical E000+i*100 car record.
## Original six-slot serializer/callback scheduling is EXTERNAL.
## Caller must supply actual verified original B/C, ROM factors,
## E96D lookup, and source car record. Never guess vehicle speed,
## friction, track barriers, or game update rates.
##
## Original Z80 CALL PE,1689 and other incomplete paths fail closed:
## this helper preserves any proven earlier state without fabricating
## a full car update. A successful return reaches PC 75F1 (original
## RET), not the game's entire collision/AI/results processing.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const Chain = preload("res://scripts/mechanics/ArcadeVerifiedMotionChain.gd")
const Motion = preload("res://scripts/mechanics/ArcadeMotionGeometry.gd")
const Serializer = preload("res://scripts/mechanics/ArcadeScratchSerializer.gd")
const Car = preload("res://scripts/mechanics/ArcadeCarRecord.gd")
const Speed709C = preload("res://scripts/mechanics/ArcadeDriveSpeed709C.gd")
const Carry7124 = preload("res://scripts/mechanics/ArcadeDriveCarryProjection.gd")
const Gate701A = preload("res://scripts/mechanics/ArcadeDriveGate701A.gd")
const Slow7049 = preload("res://scripts/mechanics/ArcadeDriveSlow7049.gd")
const External7E5E = preload("res://scripts/mechanics/ArcadeDriveExternal7E5E.gd")
const External2AD1 = preload("res://scripts/mechanics/ArcadeDriveExternal2AD1.gd")
const Checkpoint75F2 = preload("res://scripts/mechanics/ArcadeCollisionGeometryCheckpoint.gd")
const Special7D4C = preload("res://scripts/mechanics/ArcadeDriveSpecial7D4C.gd")
const Smooth7D65 = preload("res://scripts/mechanics/ArcadeDriveSmooth7D65.gd")

const ORIGINAL_MOVE_START: int = 0x7530
const ORIGINAL_FOOTPRINT_START: int = 0x7572
const ORIGINAL_RETURN_PC: int = 0x75F1
const SCRATCH_Y: int = 0xE72B
const SCRATCH_X: int = 0xE735
const MOTION_HEADING: int = 0xE76A
const MOTION_BYTE: int = 0xE76C
const BODY_HEADING: int = 0xE768


static func apply_original_7530_to_75f1(master_ram: PackedByteArray) -> Dictionary:
    ## The previous physics chain MUST have landed at PC7530. There
    ## is no 60fps time step: these are exactly the original arithmetic
    ## instructions for ONE invocation of the CPU movement stage.
    assert(master_ram.size() == State.LENGTH)
    var x: int = State.get16(master_ram, SCRATCH_X)
    var y: int = State.get16(master_ram, SCRATCH_Y)
    var heading: int = State.get8(master_ram, MOTION_HEADING)
    var signed_motion: int = State.get8(master_ram, MOTION_BYTE)
    var step: Dictionary = Motion.integrate_center(heading, signed_motion, x, y)

    var updated: PackedByteArray = master_ram.duplicate()
    State._set16(updated, SCRATCH_X, step["x"])
    State._set16(updated, SCRATCH_Y, step["y"])

    var footprint: Dictionary = Motion.footprint(
        State.get8(updated, BODY_HEADING), step["x"], step["y"])
    for offset in footprint.keys():
        # ArcadeMotionGeometry returns offsets from original E72B scratch
        # base. These are NOT physical car+offset addresses.
        State._set16(updated, SCRATCH_Y + offset, footprint[offset])
    return {
        "ram": updated,
        "movement": step,
        "footprint": footprint,
        "integrated": true,
        "next_pc": ORIGINAL_RETURN_PC
    }


static func apply_original_7572_geometry_only(master_ram: PackedByteArray) -> Dictionary:
    ## MAME live tracing confirmed that the original CPU may execute
    ## car-footprint geometry WITHOUT first updating its centre.
    ## This entry is for a caller which AUTHENTICALLY reached PC7572.
    assert(master_ram.size() == State.LENGTH)
    var x: int = State.get16(master_ram, SCRATCH_X)
    var y: int = State.get16(master_ram, SCRATCH_Y)
    var footprint: Dictionary = Motion.footprint(
        State.get8(master_ram, BODY_HEADING),x,y)
    var updated: PackedByteArray = master_ram.duplicate()
    for offset in footprint.keys():
        State._set16(updated, SCRATCH_Y + offset, footprint[offset])
    return {
        "ram": updated,
        "movement": {},
        "footprint": footprint,
        "integrated": false,
        "next_pc": ORIGINAL_RETURN_PC
    }


static func run_verified_prefix(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_ix: int,
        original_b: int,
        original_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## 71C8 → ... → 752F → 7530 → 75F1, unless the REAL original
    ## Z80 calls 1689. We never run 7530 on that exceptional route.
    assert(master_ram.size() == State.LENGTH)
    var prior: Dictionary = Chain.advance_through_original_steering_decay(
        master_ram,physical_car,original_ix,original_b,original_c,
        original_direct_factor,original_reverse_factor,
        control_table_256,original_weighting_factor)
    prior["original_movement_7530"] = {}
    if prior["next_pc"] != ORIGINAL_MOVE_START:
        assert(prior["next_pc"] == 0x1689)
        prior["complete"] = false
        return prior

    var movement: Dictionary = apply_original_7530_to_75f1(prior["ram"])
    prior["ram"] = movement["ram"]
    prior["original_movement_7530"] = movement
    prior["next_pc"] = ORIGINAL_RETURN_PC
    prior["complete"] = true
    prior["verified_prefix_complete"] = true
    prior["unverified_downstream"] = "original Z80 75F1 RET, six-slot callback scheduling, car and terrain collisions"
    return prior



static func run_verified_original_slot_stage(
        master_ram: PackedByteArray,
        original_ix: int,
        original_b: int,
        original_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## A caller which has AUTHENTICALLY selected original IX can
    ## use the recovered master 61CE loader, execute the verified
    ## 71C8–75F0 arithmetic prefix, and run original 629A saver.
    ##
    ## Importantly, this is NOT a simulated full CALL 601E:
    ## additional original effects before/after the recovered block
    ## and the six-slot scheduling logic are still unverified.
    ## B/C, two ROM factors and control-table inputs are supplied,
    ## never generated by arbitrary tuning.
    assert(State.CAR_POINTERS.has(original_ix))
    assert(master_ram.size() == State.LENGTH)
    var physical_slot: int = Serializer.physical_slot_for_ix(original_ix)

    # A physical car record includes 0x100 bytes. The snapshot copies
    # only its LOW 0x60 into E72B scratch; IX+31/+57/+79 are read from
    # the HIGH part of the persistent slot without rewriting them.
    var prepared: PackedByteArray = Serializer.load_slot_to_scratch(
        master_ram, physical_slot)
    var physical_bytes: PackedByteArray = prepared.slice(
        physical_slot - State.BASE,
        physical_slot - State.BASE + Serializer.ORIGINAL_SLOT_LENGTH)
    var original_car: ArcadeCarRecord = Car.new(physical_bytes)

    var result: Dictionary = run_verified_prefix(
        prepared,original_car,original_ix,
        original_b,original_c,original_direct_factor,
        original_reverse_factor,control_table_256,
        original_weighting_factor)
    result["physical_slot"] = physical_slot
    result["scratch_loaded"] = true
    result["scratch_saved"] = false

    if result["next_pc"] == ORIGINAL_RETURN_PC:
        # Original save reverses the 48-word PUSH sequence: output
        # slot+00..+5F gets the just-computed E72B..E78A words.
        # Its upper 160 bytes are preserved except original verified
        # indexed writes already made during 71C8–75F0.
        result["ram"] = Serializer.save_scratch_to_slot(
            result["ram"],physical_slot)
        result["scratch_saved"] = true
    else:
        # A real nonlocal 1689 escape never reaches the normal
        # 75F1 return. Do not force original storeback or undo
        # earlier independently verified changes.
        assert(result["next_pc"] == 0x1689)
        result["complete"] = false

    return result


static func run_verified_original_slot_from_7124(
        master_ram: PackedByteArray,
        original_ix: int,
        original_control_window_257: PackedByteArray,
        inherited_b: int,
        inherited_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        steering_control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## Connect the already opcode-verified original 7124/714E selector
    ## to the authentic 71C8–75F0 per-car motion/geometry prefix.
    ## First load the selected physical car's 48 original working words,
    ## then produce the real carry and B/C bytes before the drive stages.
    ## All lookup bytes/factors still come from an authenticated caller.
    ## This is NOT the full arcade frame/collision scheduler.
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var physical_slot: int = Serializer.physical_slot_for_ix(original_ix)
    var prepared: PackedByteArray = Serializer.load_slot_to_scratch(
        master_ram, physical_slot)
    var physical_bytes: PackedByteArray = prepared.slice(
        physical_slot - State.BASE,
        physical_slot - State.BASE + Serializer.ORIGINAL_SLOT_LENGTH)
    var original_car: ArcadeCarRecord = Car.new(physical_bytes)

    return _finish_loaded_original_slot_from_7124(
        prepared, original_car, original_ix,
        original_control_window_257, inherited_b, inherited_c,
        original_direct_factor, original_reverse_factor,
        steering_control_table_256, original_weighting_factor)


static func run_verified_original_slot_from_709c(
        master_ram: PackedByteArray,
        original_ix: int,
        original_b_at_709c: int,
        original_rom_2000_table_256: PackedByteArray,
        original_control_window_257: PackedByteArray,
        original_direct_factor: int,
        original_reverse_factor: int,
        steering_control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## Authentically extend the car chain backwards to 709C. The genuine
    ## 709C–7123 speed arithmetic determines E765 and the outgoing B
    ## register. Original 7124's cosine ROM load sets the outgoing C.
    ## This replaces no original 7017–709B input/scheduling behaviour.
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var physical_slot: int = Serializer.physical_slot_for_ix(original_ix)
    var prepared: PackedByteArray = Serializer.load_slot_to_scratch(
        master_ram,physical_slot)
    var physical_bytes: PackedByteArray = prepared.slice(
        physical_slot - State.BASE,
        physical_slot - State.BASE + Serializer.ORIGINAL_SLOT_LENGTH)
    var original_car: ArcadeCarRecord = Car.new(physical_bytes)

    var speed: Dictionary = Speed709C.apply_original_709c(
        prepared,original_car,original_b_at_709c,original_rom_2000_table_256)
    var real_projection: Dictionary = Carry7124.calculate(
        State.get8(speed["ram"],Carry7124.HEADING),
        State.get16(speed["ram"],Carry7124.ANGULAR_WORD),
        State.get16(speed["ram"],Carry7124.MOTION_WORD))

    var result: Dictionary = _finish_loaded_original_slot_from_7124(
        speed["ram"], original_car, original_ix,
        original_control_window_257,
        speed["b"], real_projection["cos"],
        original_direct_factor, original_reverse_factor,
        steering_control_table_256, original_weighting_factor)
    result["original_speed_709c"] = speed
    result["inherited_714e_b"] = speed["b"]
    result["inherited_714e_c"] = real_projection["cos"]
    result["unverified_upstream"] = "original 7017–709B inputs, controls, timing and calls"
    return result


static func run_verified_original_slot_from_7017(
        master_ram: PackedByteArray,
        original_ix: int,
        original_rom_2000_table_256: PackedByteArray,
        original_control_window_257: PackedByteArray,
        original_direct_factor: int,
        original_reverse_factor: int,
        steering_control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## Only an authenticated original 7017 entry may use this method.
    ## It loads the original car record ONCE, runs original CALL 75F2
    ## geometry checkpoint, then original 701A status gate.
    ##
    ## FAST 7036->709C branch resumes the fully proven per-car chain.
    ## SPECIAL 7D4C BIT1 direct-centre route returns at 7024 and genuinely
    ## JP7572, skipping speed integration but updating the footprint.
    ## SLOW 7049 now computes genuine Z80 fixed-point decrements and
    ## continues at 709C; the separate bounded 7E5E early-return
    ## verifier may also resume it; 2AD1 now has its original BIT0
    ## immediate return. 7EA3 and 2AD6 event dispatch remain opaque.
    ## The original 7D65 smoothing branch also authentically returns
    ## to 7024 then skips 7530 via the original JP7572 geometry path.
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var physical_slot: int = Serializer.physical_slot_for_ix(original_ix)
    var loaded: PackedByteArray = Serializer.load_slot_to_scratch(master_ram,physical_slot)
    var saved: Dictionary = Checkpoint75F2.snapshot(loaded)
    var preflight: Dictionary = Gate701A.apply_after_75f2(saved["ram"],original_ix)

    if preflight["next_pc"] == Gate701A.OPAQUE_CALL_PC:
        var special: Dictionary = Special7D4C.apply_from_original_call(
            preflight["ram"],original_ix)
        var special_ram: PackedByteArray = special["ram"]
        var smoothing: Dictionary = {}
        if special["next_pc"] == Special7D4C.UNRESOLVED_PC:
            smoothing = Smooth7D65.apply_after_original_7d4c(
                special_ram,original_ix)
            assert(smoothing["next_pc"] == Special7D4C.NORMAL_CALL_RETURN)
            special_ram = smoothing["ram"]
        else:
            assert(special["next_pc"] == Special7D4C.NORMAL_CALL_RETURN)
        # Real return to 7024 executes JP7572. The original directly
        # updates footprint geometry here, WITHOUT 709C–7530 speed motion;
        # the longer branch has ALREADY updated genuine E765/E76B.
        var footprint: Dictionary = apply_original_7572_geometry_only(special_ram)
        var completed_ram: PackedByteArray = Serializer.save_scratch_to_slot(
            footprint["ram"],physical_slot)
        return {
            "ram": completed_ram, "complete": true,
            "next_pc": ORIGINAL_RETURN_PC, "physical_slot": physical_slot,
            "scratch_loaded": true, "scratch_saved": true,
            "verified_prefix_complete": true,
            "checkpoint_75f2": saved, "preflight_701a": preflight,
            "original_special_7d4c": special,
            "original_smoothing_7d65": smoothing,
            "original_speed_709c": {},
            "original_movement_7530": footprint,
            "unverified_downstream": "original post-75F1 collision and callback scheduling"
        }

    var drive_ram: PackedByteArray = preflight["ram"]
    var inherited_b: int = preflight["b"]
    var slow: Dictionary = {}
    var external: Dictionary = {}
    var external2: Dictionary = {}
    var pending_pc: int = -1
    if preflight["next_pc"] == Slow7049.ENTRY_PC:
        slow = Slow7049.apply_from_original_7049(
            drive_ram,original_ix,inherited_b)
        drive_ram = slow["ram"]
        inherited_b = slow["b"]
        if slow["next_pc"] == External7E5E.ENTRY_PC:
            # Original 708D PUSH BC; 708E CALL 7E5E. For a real
            # early return, 7091 POP BC restores inherited B before
            # the genuine 7092 IX-03 gate (possibly CALL 2AD1).
            external = External7E5E.apply_from_original_call(
                drive_ram,original_ix)
            drive_ram = external["ram"]
            if external["next_pc"] == External7E5E.OPAQUE_DISPATCH_PC:
                pending_pc = External7E5E.OPAQUE_DISPATCH_PC
            else:
                assert(external["next_pc"] == External7E5E.NORMAL_CALL_RETURN)
                if State.get8(drive_ram,original_ix - 3) < 3:
                    pending_pc = Slow7049.EXTERNAL_2AD1
        elif slow["next_pc"] == Slow7049.EXTERNAL_2AD1:
            pending_pc = Slow7049.EXTERNAL_2AD1
        else:
            assert(slow["next_pc"] == Speed709C.ENTRY_PC)
        if pending_pc == External2AD1.ENTRY_PC:
            # Original 7092 PUSH BC; 7098 CALL C,2AD1. Its REAL
            # 2AD5 RET NZ on bit0 returns to 709B POP BC, restoring
            # inherited B and continuing to 709C. Do not execute the
            # large unverified banked event side effects from 2AD6.
            external2 = External2AD1.apply_from_original_call(
                drive_ram,original_ix)
            drive_ram = external2["ram"]
            pending_pc = (-1 if external2["next_pc"] ==
                External2AD1.NORMAL_CALL_RETURN else External2AD1.OPAQUE_DISPATCH_PC)
        if pending_pc != -1:
            return {
                "ram": drive_ram, "complete": false,
                "next_pc": pending_pc, "physical_slot": physical_slot,
                "scratch_loaded": true, "scratch_saved": false,
                "checkpoint_75f2": saved, "preflight_701a": preflight,
                "original_slow_7049": slow, "original_speed_709c": {},
                "original_external_7e5e": external,
                "original_external_2ad1": external2,
                "pending_original_call": "%04X" % pending_pc,
                "unverified_downstream": "original 7EA3/2AD6 event dispatch side effects"
            }
    else:
        assert(preflight["next_pc"] == Speed709C.ENTRY_PC)

    # Original IX-1D may have been incremented by the 7036 branch.
    # Construct this original physical car view AFTER that write.
    var physical_bytes: PackedByteArray = drive_ram.slice(
        physical_slot - State.BASE,
        physical_slot - State.BASE + Serializer.ORIGINAL_SLOT_LENGTH)
    var original_car: ArcadeCarRecord = Car.new(physical_bytes)
    var speed: Dictionary = Speed709C.apply_original_709c(
        drive_ram,original_car,inherited_b,original_rom_2000_table_256)
    var real_projection: Dictionary = Carry7124.calculate(
        State.get8(speed["ram"],Carry7124.HEADING),
        State.get16(speed["ram"],Carry7124.ANGULAR_WORD),
        State.get16(speed["ram"],Carry7124.MOTION_WORD))

    var result: Dictionary = _finish_loaded_original_slot_from_7124(
        speed["ram"],original_car,original_ix,
        original_control_window_257,
        speed["b"],real_projection["cos"],
        original_direct_factor,original_reverse_factor,
        steering_control_table_256,original_weighting_factor)
    result["checkpoint_75f2"] = saved
    result["preflight_701a"] = preflight
    result["original_slow_7049"] = slow
    result["original_external_7e5e"] = external
    result["original_external_2ad1"] = external2
    result["original_speed_709c"] = speed
    result["inherited_714e_b"] = speed["b"]
    result["inherited_714e_c"] = real_projection["cos"]
    result["unverified_upstream"] = "original selection/callbacks before 7017"
    return result


static func _finish_loaded_original_slot_from_7124(
        prepared: PackedByteArray,
        original_car: ArcadeCarRecord,
        original_ix: int,
        original_control_window_257: PackedByteArray,
        inherited_b: int,
        inherited_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        steering_control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## Common verified 7124 continuation. Preserves the caller's
    ## ALREADY LOADED scratch RAM, including a new 709C E765 update.
    assert(prepared.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var physical_slot: int = Serializer.physical_slot_for_ix(original_ix)

    var result: Dictionary = Chain.advance_from_verified_7124_carry_source(
        prepared, original_car, original_ix,
        original_control_window_257, inherited_b, inherited_c,
        original_direct_factor, original_reverse_factor,
        steering_control_table_256, original_weighting_factor)
    result["physical_slot"] = physical_slot
    result["scratch_loaded"] = true
    result["scratch_saved"] = false
    result["original_movement_7530"] = {}

    if result["next_pc"] != ORIGINAL_MOVE_START:
        # The authentic 714E->7315 bypass now resumes the verified
        # steering suffix and reaches 7530. Only original nonlocal
        # CALL PE 1689 escapes; never fake a 75F1 scratch save there.
        assert(result["next_pc"] == 0x1689)
        result["complete"] = false
        result["verified_prefix_complete"] = true
        result["unverified_downstream"] = "original nonlocal 1689 diagnostic continuation"
        return result

    var movement: Dictionary = apply_original_7530_to_75f1(result["ram"])
    result["ram"] = Serializer.save_scratch_to_slot(
        movement["ram"], physical_slot)
    result["original_movement_7530"] = movement
    result["next_pc"] = ORIGINAL_RETURN_PC
    result["scratch_saved"] = true
    result["complete"] = true
    result["verified_prefix_complete"] = true
    result["unverified_downstream"] = (
        "original post-75F1 callbacks, car/terrain collisions and race scheduling")
    return result
