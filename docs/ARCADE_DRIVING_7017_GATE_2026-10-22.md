# Original 7017 checkpoint and 701A–7048 per-car control gate

**22 October 2026 — bounded original 1991 arcade CPU recovery.**

The original master Z80 enters `7017` by calling `75F2`, which snapshots eleven collision/geometry backup words, then continues at `701A`. The previously verified 75F2 stage is now connected to the newly recovered original 701A branch logic. The original master bytes came from the owner's **private, checksum-authenticated** archived listing; original executable bytes and assets are not in this public repository.

## Original instruction-exact routes

`tools/arcade_drive_701a_control.py` interprets the real original 701A–7048 Z80 opcodes, independently compared with a separate branch/arithmetic model across **100,000 cases, zero mismatches**:

| Condition after authentic `75F2` return | Original result | Cases |
| --- | --- | ---: |
| `IX+5C` bit 0 set | Enter original `CALL 7D4C`; this control-gate verifier stops at call entry, with no imagined return | 33,334 |
| Otherwise `IX+31` bit 4 or `IX+33` bit 0 set | Increment `IX-1D` modulo 256, multiply original `IX+57` by `0x60` using the *known exact* X-ROM slot1-low byte, set original B and continue at `709C` | 33,333 |
| Neither flag set | Set original `IX-1D` to zero and enter original `7049` slow branch (now recovered separately) | 33,333 |

This **bounded gate verifier** stops at the `7D4C` call or `7049` branch instead of inventing side effects. Separate authenticated successors now cover both; original per-car offsets refer to the physical `IX` pointer, not a generic vehicle acceleration model.

## Connected Godot pipeline

`ArcadeDriveGate701A.gd` reproduces these bounded original input decisions. `ArcadeVerifiedVehiclePhysicsPrefix.run_verified_original_slot_from_7017` now:

1. Loads the original selected physical car's 48 scratch words **once**;
2. Runs real `75F2` geometry checkpoint before the `701A` gate;
3. On the authentic fast branch, carries original B to the recovered `709C` speed stage and then continues the already verified `7124→714E→71C8/7315→7530→7572→75F1` geometry/storeback chain;
4. On the original `7D4C` branch, bit-1-set direct-centre or bit-1-clear `7D65–7E35` smoothing returns through genuine `7024→7572` geometry without normal speed integration;
5. On original `7049`, applies the exact X-ROM/borrow calculations, continuing to `709C` directly or through the separately recovered early-return routes inside `7E5E`. It still stops BEFORE unverified `7EA3`/`2AD1` effects, without a fabricated scratch save.

Tests independently compose the staged original operations for **all five physical slots**, verify source RAM is not mutated, test `IX-1D` counter wrap and fast-branch X-ROM rounding, and ensure deferred original branches fail closed.

## Still open

True earlier full `601E` callback scheduling and control sources, **effects beyond original `7EA3` event dispatch and inside `2AD1`**, real MAME full-frame input-output parity, steering table provenance, AI, collision/terrain consequences, fourteen dynamic circuit QRAM maps, pits/fuel/turbo, championship, audio and Android release. See [7D4C direct-position recovery](ARCADE_DRIVING_7D4C_DIRECT_2026-10-22.md), [7049/7D65 recovery](ARCADE_DRIVING_7049_7D65_RECOVERY_2026-10-22.md) and [7E5E early-return recovery](ARCADE_DRIVING_7E5E_EARLY_RETURNS_2026-10-22.md). Original circuits and approved camera remain unchanged.

This is an extension of authentic arcade arithmetic and branching, **not a completed game or Android APK**.
