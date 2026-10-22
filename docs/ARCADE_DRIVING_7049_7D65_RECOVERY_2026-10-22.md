# Original 7049 slow-drive and 7D65 special smoothing recovery

**22 October 2026 — 1991 original master Z80 opcode parity, two complete bounded instruction windows.** Original executable bytes and the owner's recovered archive remain private and are not part of this repository.

## 7049–709B: original slow-pedal arithmetic

`tools/arcade_drive_7049_slow.py` independently interprets the exact original `7049–709B` CPU instructions and compares them with a separate integer model. The master ROM SHA-256 is pinned to `521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7` and the 83-byte window to `c96cdfcf07c85b7c0456e31589dcf44fa7860be2cf65ec31736c63dfb3577925`.

**100,000 privately run original-Z80 comparisons, zero mismatches:**

| Authentic exit | Cases | Handling |
| --- | ---: | --- |
| `709C` | 93,584 | Continue with preserved original B into verified speed/movement pipeline |
| Conditional `CALL 7E5E` | 6,334 | Preserve already-proven `IX+39/3A/31` writes; stop BEFORE external call effects |
| Conditional `CALL 2AD1` | 82 | Preserve already-proven writes; stop BEFORE external call effects |

The stage uses the original E765 doubled-high byte, two nested *unsigned X-ROM slot1 LOW* products, original `SRL/ADC` carry, saturating `B+0x80` helper, an indexed IX+3B X-ROM product, and the exact borrow/status-bit and external-call gates. **The unknown X-ROM slot1 HIGH is not used:** each high-byte read is overwritten or abandoned before arithmetic. No original clock rate, tyre friction, collision side effect, or guessed external return has been introduced.

Godot: `ArcadeDriveSlow7049.gd`, integrated into `ArcadeVerifiedVehiclePhysicsPrefix.run_verified_original_slot_from_7017` after the original `75F2→701A` slow gate.

## 7D65–7E35: original five-part special smoothing

`tools/arcade_drive_7d65_smoothing.py` runs all exact original instructions from `7D65` through the real `7E35 RET` against a separately written fixed-point model. The authenticated 209-byte instruction-window SHA-256 is `520a88bae57f74b059dc1590b17462be31a5ce52714f004362a93c96e205b240`.

**100,000 privately run original-Z80 comparisons, zero mismatches:** all returned through the actual caller at `7024`.

The five original stages are:

1. Y centre at `E72B` approaches original physical `IX+65/66` with signed X-ROM factor `0x10`.
2. X centre at `E735` approaches original physical `IX+67/68` with factor `0x10`.
3. Heading word `E767` approaches `E93B<<8` using factor `0x0C`; exactly the same result is written to `E769`.
4. `E76B` movement word is decremented by its own factor-`0x0C` signed projection.
5. `E765` speed word is independently decremented by its factor-`0x0C` signed projection.

Each projection uses two original X-ROM slot0 signed, doubled-products (including the second result HIGH byte obtained by rewriting address `FFFD`), then exact low-byte carry and high-byte sign adjustment, with 16-bit wrapping. This is **original fixed-point CPU arithmetic**, not a floating-point interpolation or invented easing law.

Godot: `ArcadeDriveSmooth7D65.gd`. The original standalone `ArcadeDriveSpecial7D4C.gd` still exposes its precise branch boundary at `7D65`; the connected pipeline now continues that branch to `7E35 RET→7024 JP7572`, recalculates the original collision footprint **without invoking `709C` or `7530`**, and saves its 48 working words through the verified `75F1` return path. Bit-1-set direct-centre behavior is preserved.

## Tests and boundary of proof

- `tests/test_arcade_drive_7049_slow.py` and `tests/test_arcade_drive_7d65_smoothing.py` use synthetic, distributable input vectors. The two private original-Z80 parity runners are opt-in and require the owner's checksum-verified master region.
- `tests/godot/test_mechanics.gd` checks the two isolated new stages and their composition across all five physical car slots, including both unresolved external calls, direct positioning, smoothing, verified speed continuation and conditional saveback.
- The original circuit geometry, pit locations and approved slow bounded portrait camera remain **untouched**.

**Still open:** actual behavior of external routines `7E5E` and `2AD1`; full original `601E` callback scheduling, original per-frame MAME live trace comparison, remaining collision/terrain results, steering and accelerator table provenance, all 14 live QRAM circuit maps, AI, pits/fuel/turbo, campaign/economy, audio and production release. A verified bounded driving chain **is not a playable or fully decompiled game**.
