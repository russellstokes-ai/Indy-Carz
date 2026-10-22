# Original 2AD1 entry gate and safe return to 709B

**22 October 2026 — five genuine 1991 master Z80 instruction bytes.** The original `7098 CALL C,2AD1`, reached directly from slow-driving control or after a returned `7E5E` call, begins with `BIT 0,(IX+31)` followed by `RET NZ` at `2AD5`.

The exact authenticated instruction window `2AD1–2AD5` has SHA-256 `989b44feeff748361f08fa51bddd4608c6ebfe4ba08bfe8c3b329d41e9bb31ba`; owner master SHA-256 is `521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7`.

`tools/arcade_drive_2ad1_gate.py` compares the original opcodes with an independent bit-gate model using **100,000 cases, zero mismatches** (50,000 immediate returns, 50,000 stops at the authentic `2AD6` continuation). Its test vector inputs are synthetic; the proprietary CPU image stays private.

- When bit 0 is set, the original returns to `709B POP BC`, restoring the previously saved B before continuing at `709C`. The Godot `ArcadeDriveExternal2AD1.gd` applies no fictitious memory changes on that route.
- When bit 0 is clear, execution stops at `2AD6` **before** original ROM table copies, bank selectors and writes through CPU port `F4`. The much larger `2AD6–2BCC` function is not recovered by this five-byte proof.

`ArcadeVerifiedVehiclePhysicsPrefix.run_verified_original_slot_from_7017` now connects both `2AD1` entry routes, including the one reached after an authentic early return from `7E5E`. Its downstream tests exercise all five original physical car slots and verify that unknown event dispatch never triggers scratch saveback.

**Still open:** full 2AD6 banked event copy, 7EA3 event dispatch, original MAME full-frame parity, collision aftermath, the per-frame callback scheduler and race progression. No original circuit or camera change, source ROM bytes, speculative physics or commercial release claim is included.
