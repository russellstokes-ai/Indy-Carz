class_name ArcadeVerifiedMotionChain
extends RefCounted

## Authentic bounded original master Z80 motion sequence 71FA -> 7225 ->
## 7245 -> 726D. This is a deterministic low-level physics CHAIN, not
## a finished full arcade per-car simulation or independent frame scheduler.
##
## It reuses separately genuine original opcode-verified calculations.
## Only genuine original E76B and E933 RAM words are changed here.
## The original nonlocal CALL PE 1689 traps outside the normal chain:
## NEVER guess a motion value or advance 7225 on that route.

const State = preload("res://scripts/mechanics/ArcadeCollisionRetry.gd")
const Xrom = preload("res://scripts/mechanics/ArcadeDriveXromAccumulator.gd")
const Velocity = preload("res://scripts/mechanics/ArcadeVelocitySignGate.gd")
const Heading = preload("res://scripts/mechanics/ArcadeDriveHeadingProjection.gd")
const Entry = preload("res://scripts/mechanics/ArcadeDriveEntryGate.gd")
const Correction = preload("res://scripts/mechanics/ArcadeDriveMotionCorrection.gd")
const Angular = preload("res://scripts/mechanics/ArcadeDriveAngularUpdate.gd")
const Car = preload("res://scripts/mechanics/ArcadeCarRecord.gd")
const DriveBC = preload("res://scripts/mechanics/ArcadeDriveControlSelector.gd")
const Source7124 = preload("res://scripts/mechanics/ArcadeDriveCarryProjection.gd")
const Steering7315 = preload("res://scripts/mechanics/ArcadeSteeringAngularStage.gd")
const SteeringLookup = preload("res://scripts/mechanics/ArcadeSteeringLookupStage.gd")
const Weighted = preload("res://scripts/mechanics/ArcadeSteeringWeightedInput.gd")
const Control = preload("res://scripts/mechanics/ArcadeSteeringControlAngle.gd")
const DoubleProjection = preload("res://scripts/mechanics/ArcadeSteeringDoubleProjection.gd")
const SpeedLimiter = preload("res://scripts/mechanics/ArcadeSteeringSpeedLimiter.gd")
const SecondProjection = preload("res://scripts/mechanics/ArcadeSteeringSecondProjection.gd")
const SteeringDecay = preload("res://scripts/mechanics/ArcadeSteeringDecay.gd")

const E76B: int = 0xE76B
const E768: int = 0xE768
const E769: int = 0xE769
const E933: int = 0xE933
const CONTINUE_PC: int = 0x726D
const NONLOCAL_PC: int = 0x1689


static func advance_verified_segment(master_ram: PackedByteArray,
                                     original_c: int,
                                     incoming_de: int) -> Dictionary:
    assert(master_ram.size() == State.LENGTH,
           "Expected the original E000-FFFF 8192-byte master RAM view")
    assert(original_c >= 0 and original_c <= 255)
    assert(incoming_de >= 0 and incoming_de <= 65535)

    var prior_e933: int = State.get16(master_ram, E933)
    var stage_71fa: Dictionary = Xrom.calculate(original_c, prior_e933, incoming_de)
    if stage_71fa["next_pc"] == NONLOCAL_PC:
        # Original CALL PE 1689 takes over CPU flow; this stage is NOT
        # a normal returned car update. Preserve caller state untouched.
        return {
            "complete": false,
            "next_pc": NONLOCAL_PC,
            "ram": master_ram.duplicate(),
            "xrom": stage_71fa,
            "motion": {},
            "heading_projection": {}
        }
    assert(stage_71fa["next_pc"] == 0x7225)

    var old_motion: int = State.get16(master_ram, E76B)
    var motion: Dictionary = Velocity.calculate(old_motion, stage_71fa["de"])
    assert(motion["next_pc"] == 0x7245)

    # The original EX DE,HL leaves DE equal to the signed-clamped motion
    # word that the NEXT original trigonometric projection consumes.
    var projection: Dictionary = Heading.calculate(
        State.get8(master_ram, E768),
        State.get16(master_ram, E769),
        motion["de_after"])
    assert(projection["next_pc"] == CONTINUE_PC)
    var out: PackedByteArray = master_ram.duplicate()
    State._set16(out, E76B, motion["stored_e76b"])
    State._set16(out, E933, projection["e933"])

    return {
        "complete": true,
        "next_pc": CONTINUE_PC,
        "ram": out,
        "xrom": stage_71fa,
        "motion": motion,
        "heading_projection": projection
    }



static func advance_from_original_input(master_ram: PackedByteArray,
                                        physical_car: ArcadeCarRecord,
                                        original_b: int,
                                        original_c: int) -> Dictionary:
    ## Composed original 71C8–726C. Original B/C come from the earlier
    ## per-car/course table-selection code; they must NOT be guessed.
    ## This method intentionally does not alter the supplied car record.
    assert(master_ram.size() == State.LENGTH)
    assert(original_b >= 0 and original_b <= 255)
    assert(original_c >= 0 and original_c <= 255)

    var entry: Dictionary = Entry.calculate(
        physical_car.read_u8(Car.FIELD_PEDAL_RESPONSE), original_b,
        original_c, physical_car.read_u8(0x75),
        State.get8(master_ram, 0xE76C))

    if entry["next_pc"] == 0x726D:
        # Original Z80 JP Z,726D: skips 71FA, 7225 and 7245.
        # Unrelated master RAM and caller's physical car stay unchanged.
        return {
            "complete": true,
            "motion_update_skipped": true,
            "next_pc": CONTINUE_PC,
            "ram": master_ram.duplicate(),
            "entry": entry,
            "xrom": {},
            "motion": {},
            "heading_projection": {}
        }

    assert(entry["next_pc"] == 0x71FF or entry["next_pc"] == 0x7225)
    # If entry is 7225, original C is zero: the 71FA helper itself
    # takes the zero-C branch to 7225 without the X-ROM lookup.
    var continuation: Dictionary = advance_verified_segment(
        master_ram, original_c, entry["de"])
    continuation["entry"] = entry
    continuation["motion_update_skipped"] = false
    return continuation



static func advance_through_original_motion_correction(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_b: int,
        original_c: int,
        original_2000_rom_factor: int) -> Dictionary:
    ## Connected bounded original 71C8–72D2 physics. Both the original
    ## selected B/C bytes and original 0x2000+IX+3C table factor MUST be
    ## supplied by an authenticated earlier original-compatible stage.
    ##
    ## The direct skip at 71C8 jumps TO 726D, so 726D DOES still run.
    ## A CALL PE 1689, by contrast, never reaches 726D normally.
    ## This distinction is essential: direct skip is NOT an early
    ## return from the whole physics update.
    assert(master_ram.size() == State.LENGTH)
    assert(original_b >= 0 and original_b <= 255)
    assert(original_c >= 0 and original_c <= 255)
    assert(original_2000_rom_factor >= 0 and original_2000_rom_factor <= 255)

    var first: Dictionary = advance_from_original_input(
        master_ram, physical_car, original_b, original_c)
    if not first["complete"]:
        # Non-local original diagnostic/overflow handler; no invented
        # continuation into collision/motion/steering is allowed.
        first["motion_correction"] = {}
        return first
    assert(first["next_pc"] == 0x726D)
    var correction: Dictionary = Correction.apply_to_ram(
        first["ram"], original_b, original_2000_rom_factor)
    assert(correction["next_pc"] == 0x72D3)
    first["ram"] = correction["ram"]
    first["motion_correction"] = correction
    first["next_pc"] = 0x72D3
    return first



static func advance_through_original_angular_update(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_b: int,
        original_c: int,
        original_direct_factor: int,
        original_reverse_factor: int) -> Dictionary:
    ## Fully bounded original 71C8–7314 CPU math, including:
    ## - original pedal/C-byte 71C8 short-circuit
    ## - signed displacement 71D9 and X-ROM 71FA
    ## - E76B clamp 7225 and heading projection 7245
    ## - E76B correction 726D with 0B76/0B6B saturations
    ## - E765 angular update 72D3 with 0B7D and 1689 escapes
    ##
    ## B/C and BOTH original 0x2000 ROM factors must be supplied from
    ## confirmed earlier original state/ROM-bank lookup. This method
    ## does not guess horsepower, tyre friction, track or AI values.
    var previous: Dictionary = advance_through_original_motion_correction(
        master_ram, physical_car, original_b, original_c,
        original_direct_factor)

    if not previous["complete"]:
        previous["angular_update"] = {}
        return previous
    assert(previous["next_pc"] == 0x72D3)

    # Original 72D3 still has DE from the 726D selected change. Do NOT
    # accidentally use freshly updated E76B as the second X-ROM operand.
    var original_de: int = previous["motion_correction"]["change"]
    var stage: Dictionary = Angular.apply_to_ram(
        previous["ram"], original_reverse_factor, original_de)
    previous["ram"] = stage["ram"]
    previous["angular_update"] = stage
    previous["next_pc"] = stage["next_pc"]
    if stage["next_pc"] == 0x1689:
        # E76B already changed at 726D. E765 was NOT stored yet.
        # Preserve those authentic partial effects, do not roll back
        # the preceding stage or forge a normal steering continuation.
        previous["complete"] = false
    else:
        assert(stage["next_pc"] == 0x7315)
    return previous



static func advance_through_original_steering_selection(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_ix: int,
        original_b: int,
        original_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        external_control_table: PackedByteArray) -> Dictionary:
    ## The verified original CPU path now reaches steering PCs:
    ## 71C8 -> 72D3 -> 7315 -> either 7530 or 7376/7381 -> 73CD.
    ##
    ## Caller supplies the authentic E000-FFFF master working RAM, an
    ## original car record for the indexed B/C input routines, the
    ## actual original IX and TWO 0x2000 ROM factor lookups. The
    ## 256-byte E96D control table is separately supplied; no
    ## original proprietary ROM/RAM table contents ship in this app.
    ##
    ## Original downstream 73CD-752F remains unverified on the
    ## low-threshold branch: return verified prefix and PC=73CD,
    ## but NEVER fabricate vehicle position/heading state after it.
    assert(State.CAR_POINTERS.has(original_ix))
    assert(external_control_table.size() == 256)

    var previous: Dictionary = advance_through_original_angular_update(
        master_ram, physical_car, original_b, original_c,
        original_direct_factor, original_reverse_factor)
    if not previous["complete"]:
        previous["steering_7315"] = {}
        previous["steering_7376"] = {}
        return previous

    assert(previous["next_pc"] == 0x7315)
    var first_stage: Dictionary = Steering7315.apply_to_ram(
        previous["ram"], original_ix)
    previous["ram"] = first_stage["ram"]
    previous["steering_7315"] = first_stage

    if first_stage["next_pc"] == 0x7530:
        previous["steering_7376"] = {}
        previous["next_pc"] = 0x7530
        previous["complete"] = true
        return previous

    assert(first_stage["next_pc"] == 0x7376 or
           first_stage["next_pc"] == 0x7381)
    var current_ram: PackedByteArray = previous["ram"]
    var selector: Dictionary = SteeringLookup.after_verified_7315(
        first_stage,
        State.get16(current_ram, 0xE773),
        State.get8(current_ram, original_ix + 0x70),
        State.get8(current_ram, original_ix + 0x71),
        external_control_table)
    previous["steering_7376"] = selector
    previous["next_pc"] = selector["next_pc"]
    previous["complete"] = false
    previous["verified_prefix_complete"] = true
    previous["unverified_downstream"] = "original Z80 73CD-752F"
    return previous



static func advance_through_original_weighted_steering(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_ix: int,
        original_b: int,
        original_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## Continue exact original low-threshold steering lookup to original
    ## weighted byte at 73CD–73F5; normal original 7315 jumps DIRECTLY
    ## to 7530 and must NOT execute these intermediate routines.
    ##
    ## original_weighting_factor is the genuine 65-entry table output at
    ## 7635 + ceil(min(abs(signed(E76C)),127)/2), supplied externally.
    ## No proprietary program/data bytes are embedded in this project.
    assert(original_weighting_factor >= 0 and original_weighting_factor <= 255)

    var prior: Dictionary = advance_through_original_steering_selection(
        master_ram, physical_car, original_ix,
        original_b, original_c,
        original_direct_factor, original_reverse_factor,
        control_table_256)
    prior["weighted_73cd"] = {}

    if prior["next_pc"] == 0x7530:
        assert(prior["complete"])
        return prior

    if prior["next_pc"] == NONLOCAL_PC:
        assert(not prior["complete"])
        return prior

    # Both original 7315 low-threshold entry routes converge at 73CD
    # after loading B,C from original table via 7376..73CC.
    assert(prior["next_pc"] == 0x73CD)
    var selected_b: int = prior["steering_7376"]["b"]
    var final_ram: PackedByteArray = prior["ram"]
    var weighted: Dictionary = Weighted.calculate(
        State.get8(final_ram, 0xE76C),
        selected_b,
        State.get8(final_ram, original_ix - 1),
        original_weighting_factor)

    assert(weighted["next_pc"] == 0x73F6)
    prior["weighted_73cd"] = weighted
    prior["next_pc"] = 0x73F6
    # 73F6–752F is still not reconstructed: preserve any authentic
    # earlier E76B/E765/E767 and car-slot writes as already applied,
    # but do NOT invent additional heading, speed or angle updates.
    prior["complete"] = false
    prior["verified_prefix_complete"] = true
    prior["unverified_downstream"] = "original Z80 73F6-752F"
    return prior



static func advance_through_original_steering_control(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_ix: int,
        original_b: int,
        original_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## Verified original Z80 driving/steering prefix 71C8–7441.
    ## The 7315 normal route jumps straight to 7530 and does NOT
    ## execute 73CD or this control computation.
    ##
    ## The alternate 7376 / 7381 paths share this exact 73F6
    ## angular control stage. No original ROM or proprietary table
    ## values are stored: caller must provide original-compatible
    ## selected factor bytes and control table.
    var previous: Dictionary = advance_through_original_weighted_steering(
        master_ram, physical_car, original_ix,
        original_b, original_c, original_direct_factor,
        original_reverse_factor, control_table_256,
        original_weighting_factor)
    previous["steering_control_73f6"] = {}
    if previous["next_pc"] != 0x73F6:
        # May already have reached verified 7530 or the truly
        # nonlocal original 1689; no imaginary extra writes.
        return previous

    var ram: PackedByteArray = previous["ram"]
    var control: Dictionary = Control.calculate(
        State.get16(ram, 0xE789),
        State.get16(ram, 0xE773),
        State.get16(ram, 0xE787),
        State.get16(ram, 0xE771),
        State.get8(ram, original_ix + 0x79))
    assert(control["next_pc"] == 0x7442)
    previous["steering_control_73f6"] = control
    previous["next_pc"] = control["next_pc"]
    previous["complete"] = false
    previous["verified_prefix_complete"] = true
    previous["unverified_downstream"] = "original Z80 7442-752F"
    return previous



static func advance_through_original_steering_speed_limit(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_ix: int,
        original_b: int,
        original_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## Complete bounded genuine original steering chain up to original
    ## 7499 on the 7376/7381 route. The other authentic 7315
    ## continuation goes straight to 7530 and SKIPS 7376–7498.
    ##
    ## This is NOT a full original simulation frame. The intermediate
    ## B/C selector, 0x2000 original ROM factors and E96D control table
    ## are caller-supplied, never guessed in this pure physical state API.
    var earlier: Dictionary = advance_through_original_steering_control(
        master_ram, physical_car, original_ix, original_b, original_c,
        original_direct_factor, original_reverse_factor,
        control_table_256, original_weighting_factor)
    earlier["double_projection_7442"] = {}
    earlier["speed_limiter_7463"] = {}

    if earlier["next_pc"] != 0x7442:
        # Authentic original 7315 normal exit (7530), or original
        # nonlocal 1689. Do not invent a steering extension.
        return earlier

    var memory: PackedByteArray = earlier["ram"]
    var control_a: int = earlier["steering_control_73f6"]["a"]
    var weighted_a: int = earlier["weighted_73cd"]["weighted"]
    var car_heading_flag: int = State.get8(memory, original_ix + 0x79)
    var car_status: int = State.get8(memory, original_ix + 0x31)

    var projection: Dictionary = DoubleProjection.calculate(
        control_a, car_heading_flag, weighted_a, car_status)
    assert(projection["next_pc"] == 0x7463 or
           projection["next_pc"] == 0x748A)
    earlier["double_projection_7442"] = projection

    # The original BIT 0 at 745D either executes 7463–7489 or
    # jumps directly to 748A. The speed limiter chooses exactly
    # the same branch from the original status byte and then always
    # writes original IX+4C/4D and shared angular E767.
    var limited: Dictionary = SpeedLimiter.apply_to_ram(
        memory, original_ix, projection["correction"])
    assert(limited["limiter_bypassed"] ==
           projection["skip_velocity_limiter"])
    assert(limited["next_pc"] == 0x7499)

    earlier["ram"] = limited["ram"]
    earlier["speed_limiter_7463"] = limited
    earlier["next_pc"] = 0x7499
    earlier["complete"] = false
    earlier["verified_prefix_complete"] = true
    earlier["unverified_downstream"] = "original Z80 7499–752F"
    return earlier



static func advance_through_original_steering_decay(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_ix: int,
        original_b: int,
        original_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## Complete bounded original Z80 maths from 71C8 to the original
    ## car-movement entry 7530, including distinct 7315 jump paths.
    ##
    ## This only runs the verified ORIGINAL code stages. The physics
    ## update scheduler, prior original B/C selectors, original ROM
    ## factors and control table MUST be supplied by a separately
    ## authenticated input path. Do not inject arbitrary tuning.
    ##
    ## Normal 7315 route jumps directly to 7530 and skips all
    ## 7376–752F steering operations. Original 1689 also halts this
    ## bounded chain rather than fabricating a continuation.
    var previous: Dictionary = advance_through_original_steering_speed_limit(
        master_ram, physical_car, original_ix,
        original_b, original_c,
        original_direct_factor, original_reverse_factor,
        control_table_256, original_weighting_factor)
    previous["second_projection_7499"] = {}
    previous["steering_decay_74d8"] = {}

    if previous["next_pc"] != 0x7499:
        # Either original direct 7315->7530, or nonlocal 1689.
        assert(previous["next_pc"] == 0x7530 or
               previous["next_pc"] == NONLOCAL_PC)
        return previous

    var current_ram: PackedByteArray = previous["ram"]
    var original_selected_c: int = previous["steering_7376"]["c"]
    var original_car_byte: int = State.get8(current_ram, original_ix + 0x00)
    var next_projection: Dictionary = SecondProjection.calculate(
        original_selected_c,
        original_car_byte,
        State.get16(current_ram, 0xE767),
        State.get16(current_ram, 0xE769))
    assert(next_projection["next_pc"] == 0x74D8)
    previous["second_projection_7499"] = next_projection

    var next_decay: Dictionary = SteeringDecay.apply_to_ram(
        current_ram, original_ix, next_projection["de_projection"])
    assert(next_decay["next_pc"] == 0x7530)
    previous["steering_decay_74d8"] = next_decay
    previous["ram"] = next_decay["ram"]
    previous["next_pc"] = 0x7530
    previous["complete"] = true
    previous["verified_prefix_complete"] = true
    previous["unverified_downstream"] = "original per-car 7530+ geometry and collision scheduling"
    return previous



static func advance_using_verified_714e_selector(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_ix: int,
        original_table_257: PackedByteArray,
        inherited_carry: int,
        inherited_b: int,
        inherited_c: int,
        original_direct_factor: int,
        original_reverse_factor: int,
        steering_control_table_256: PackedByteArray,
        original_weighting_factor: int) -> Dictionary:
    ## The 714E stage is the original source of B/C consumed by the
    ## 71C8 driving and 7315 steering stages.
    ##
    ## The table is 257 authentic bytes starting from the original
    ## E96B CPU pointer, NOT original ROM code copied into the app.
    ## The 7148 carry flag is a genuine prior-state input, not zero.
    ##
    ## A 714E -> 7315 bypass MUST SKIP all of 71C8–7314; this helper
    ## preserves that original branch and stops at 7315 instead of
    ## erroneously running acceleration. Remaining 7315 steering can
    ## be handled separately by the corresponding verified stage.
    assert(master_ram.size() == State.LENGTH)
    assert(State.CAR_POINTERS.has(original_ix))
    var selected: Dictionary = DriveBC.select_from_original_state(
        master_ram, physical_car, original_table_257,
        inherited_b, inherited_c, inherited_carry)
    if selected["next_pc"] == 0x7315:
        return {
            "complete": false,
            "verified_prefix_complete": true,
            "original_714e_bypass": true,
            "next_pc": 0x7315,
            "ram": master_ram.duplicate(),
            "bc_selection": selected,
            "unverified_downstream": "original 7315 onward needs separate steering stage"
        }
    assert(selected["next_pc"] == 0x71C8)
    var continuation: Dictionary = advance_through_original_steering_decay(
        master_ram, physical_car, original_ix,
        selected["b"], selected["c"],
        original_direct_factor, original_reverse_factor,
        steering_control_table_256, original_weighting_factor)
    continuation["bc_selection"] = selected
    continuation["original_714e_bypass"] = false
    return continuation


static func advance_from_verified_7124_carry_source(
        master_ram: PackedByteArray,
        physical_car: ArcadeCarRecord,
        original_ix: int,
        table_257: PackedByteArray,
        inherited_b: int,
        inherited_c: int,
        direct_factor: int,
        reverse_factor: int,
        table_256: PackedByteArray,
        weighting_factor: int) -> Dictionary:
    ## 7124 writes E933 and produces carry; 714E consumes both.
    ## No caller-supplied guess for carry; the original branch to
    ## 7315 still skips the earlier acceleration calculations.
    var prior: Dictionary = Source7124.apply_to_ram(master_ram)
    var result: Dictionary = advance_using_verified_714e_selector(
        prior["ram"], physical_car, original_ix, table_257,
        prior["carry"], inherited_b, inherited_c,
        direct_factor, reverse_factor, table_256, weighting_factor)
    result["heading_source_7124"] = prior
    result["used_carry"] = prior["carry"]
    return result
