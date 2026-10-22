# Original 7D4C short positioning path and 7024→7572 continuation

**22 October 2026.** Newly recovered original Z80 branch, built only from privately authenticated original arcade instructions.

The original drive gate's `701A` status bit 0 selects `CALL 7D4C`. Within that call, `BIT 1,(IX+5C)` chooses between two fundamentally different paths:

- **Bit 1 set:** original `7D52–7D64` loads a 16-bit destination Y from `IX+65/66` and X from `IX+67/68`, writes original scratch `E72B` and `E735`, and returns at `7024`. The genuine caller then executes `JP 7572`: eight-word oriented geometry recalculation *without 709C speed or 7530 centre integration*. Only after original `75F1` does the verified 48-word storeback run.
- **Bit 1 clear:** original branches to `7D65`, which performs five independently authenticated fixed-point smoothing updates through `7E35`, then returns at `7024`. This longer branch was recovered separately; the **standalone short-branch API** still stops at its precise `7D65` boundary, but the connected pipeline now resumes it.

`tools/arcade_drive_7d4c_direct.py` executes actual original `7D4C–7D64` instructions and compares against a distinct data-flow model. The private authenticated run covered **100,000 original-Z80 cases, zero mismatches**, evenly split between direct return and unresolved slow branch.

`scripts/mechanics/ArcadeDriveSpecial7D4C.gd` implements those two original boundaries. The connected `ArcadeVerifiedVehiclePhysicsPrefix.run_verified_original_slot_from_7017` additionally invokes separate recovered `7049–709B` and `7D65–7E35` arithmetic, preserving genuine original calls and the geometry-only `7024→7572` continuation. The longer stage matched **100,000 additional original-Z80 cases, zero mismatches**. See [7049/7D65 recovery](ARCADE_DRIVING_7049_7D65_RECOVERY_2026-10-22.md). It does not pretend these routines are a full car/race update.

Original chip bytes and the recovered private master remain off-repository. Public tests use synthetic car states. Original track maps, post-collision consequences, pit/fuel/turbo, full AI and championship systems, sound and Android product completeness remain OPEN.
