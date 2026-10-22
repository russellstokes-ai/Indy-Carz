# Original Indy Heat 709C–7123 — recovered speed-word correction

**22 October 2026.** Bounded original arcade driving recovery, not full race-engine parity.

## Authenticated private source

The owner's previously saved **private** v8 whole-ROM static listing was used to reconstruct the actual master CPU image, without downloading a third-party ROM. The resulting 589,824-byte private image matched the earlier authenticated 1991 rev1 master SHA-256 **`521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7`**. The exact original 709C–7123 byte window also passed its separate `STAGE_SHA` check. This original program, its static listings and all proprietary media are **outside GitHub**.

The original X-ROM's slot0 signed saturated product and slot1 **low-byte** unsigned rounded product were already exhaustively characterized. Although the original slot1 high-byte table is still unknown, this recovered segment **never uses it**: each original `LD HL,(FFFE)` is immediately followed by an instruction replacing H before the next arithmetic use. The bounded interpreter explicitly enforces those four valid sites.

## Exact recovered sequence

Starting at authentic original master-bank0 PC `709C` with caller-supplied B and original per-car data:

1. The original X-ROM multiplication of `B` by `0xA6`, rounded by `(x*y+128)>>8`, is added to the physical car's `IX+54`; unsigned carry saturates B to 255 via original fixed helper `0A9C`.
2. Compare resulting B to the **high byte** of original shared word `E765`.
3. **Equal:** jump directly to `7124`; `E765` stays unchanged.
4. **Higher:** original ROM page `2000–20FF` is indexed by negated `IX+3C`; two rounded slot1 products and a signed slot0 product use the real `IX-20` byte. `SRL H; RR L; ADC HL,DE` increases the 16-bit E765 word, with original `CALL PE,1C88` signed-overflow clamp to `0x7FFF`.
5. **Lower:** original `NEG A; LD B,A` replaces B with the difference, then the same ROM-page input follows a separate route using `IX-1F`, slot1/slot0 arithmetic and an inherited Z80 carry. `SBC HL,DE` and original `CALL M,0AA0` clamp a negative result to zero.
6. All valid branches reach **`7124`**, where the previously recovered original heading/carry selector resumes. The source RAM is copied, never modified in place.

`tools/arcade_drive_709c_speed.py` independently implements the integer arithmetic and interprets the **real original Z80 opcode bytes**; the authenticated private run tested **100,000 cases, zero mismatches**: 57,719 add, 35,207 subtract, 7,074 equal. The case inputs challenge saturation, both original table-lookup paths, IX-indexed operands, carry inheritance, 16-bit wrap and clipping. The table and original executable bytes are not committed.

`scripts/mechanics/ArcadeDriveSpeed709C.gd` ports the same proven arithmetic to Godot without ROM assets or floating-point approximations. `ArcadeVerifiedVehiclePhysicsPrefix.run_verified_original_slot_from_709c` now continues one authentic preloaded car record through:

`61CE scratch load -> 709C–7123 speed -> 7124–714D heading/carry -> 714E original B/C selector -> normal 71C8 or genuine 7315 bypass -> 7530 movement -> 7572 footprint -> 75F1 return -> 629A scratch storeback`.

The wrapper forwards **the actual 709C outgoing B** and **the actual 7124 cosine C**, including the special subtract B change and the 714E bypass. It retains fail-closed `1689` behavior and saves the 48 words only after genuine normal return. The separately tested `run_verified_original_slot_from_7124` API is preserved.

## Still unknown — original-completion gate OPEN

- Original pre-709C caller control and full `7017–709B` accelerator/steering/auxiliary-call sequence and exact source B for every frame.
- Authentic per-track/page table sourcing and dynamic input cadence; public tests use **synthetic** tables, not proprietary original ROM data.
- Complete `601E`/callback/six-slot scheduling, collision and terrain response, all fourteen original dynamic QRAM circuits, full AI, pits, upgrades, fuel, turbo, championship/economy, audio, and commercial Android release QA.
- A continuous real MAME input-to-output trace covering this new combined `709C→75F1` path, not merely individually opcode-verified subroutines.

Do not claim the entire 1991 engine has been recovered or introduce placeholder mechanics. Original track geometry remains unchanged; the approved portrait camera uses only a gentle bounded pan.
