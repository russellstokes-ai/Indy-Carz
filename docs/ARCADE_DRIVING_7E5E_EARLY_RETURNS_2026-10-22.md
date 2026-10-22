# Original 7E5E bounded event-gate early returns

**22 October 2026 — checksum-authenticated 1991 master Z80 recovery.** After original `7049` slow-driving arithmetic borrows and reaches its `708E CALL 7E5E`, the called routine has four genuine early returns before its larger event/collision dispatch begins at `7EA3`.

`tools/arcade_drive_7e5e_returns.py` interprets the exact original bounded `7E5E–7EA2` instructions, including the real Z80 sign flag for `JP P`, and compares their effects against a separate data-flow/branch model. Original master SHA-256: `521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7`. Bounded 69-byte window SHA-256: `3cd3606a7aef94188d2d9e33a7dd6f44baec5a1ba7a59f25a16392a3388fc22f`.

**100,000 owner-ROM instruction comparisons, zero mismatches**, with deliberately stratified synthetic inputs covering each original exit:

| Original exit | Cases | Exact consequence |
| --- | ---: | --- |
| Already set `IX+31` bit 6 | 16,667 | Immediate `RET` at `7E62`, preserving RAM |
| Special signed comparison | 16,667 | Write `0x48` to `IX+3A`, then `RET` at `7E8F` |
| `E639 == IX+02` | 16,667 | `RET Z` at `7E96` |
| Adjacent position and `IX+51 >= 0x1E` | 16,666 | `RET NC` at `7EA2` |
| Remaining cases | 33,333 | Stop at `7EA3`, **before** unverified event dispatch |

The Godot `ArcadeDriveExternal7E5E.gd` follows only those instructions. On verified early return, `ArcadeVerifiedVehiclePhysicsPrefix.run_verified_original_slot_from_7017` executes the original `7091 POP BC` effect (preserving saved B), evaluates the true `7092–709B` `IX-03` conditional gate, and resumes already recovered `709C→75F1` if the original skips `CALL 2AD1` or takes its separately recovered [bit-0 immediate return](ARCADE_DRIVING_2AD1_EARLY_RETURN_2026-10-22.md).

The original `7EA3` event branch is **not** approximated. It leads to indexed status changes, multiple external routines (`8022`, `8659`, `1767`, `174E`), IY event records and further collision/race logic. Those effects remain unverified, as does the `2AD6–2BCC` banked event continuation beyond the five-byte `2AD1` gate. Neither unresolved path commits a fake 48-word scratch storeback.

No original executable, X-ROM table, circuit art, gameplay asset, or tuneable collision approximation is distributed. The same unchanged circuit layout and slow bounded portrait camera are preserved. This is a bounded recovery milestone, not a completed driving frame or game.
