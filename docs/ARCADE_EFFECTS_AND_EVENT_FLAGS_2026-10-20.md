# Indy Carz — Original arcade effect, audio event and flag-source recovery

**Evidence date:** 20 October 2026  
**Original reference:** SHA-256-verified 1991 `indyheat` arcade master Z80 ROM, locally reconstructed according to the MAME bank map.  
**Status:** Original executable instructions and isolated allocator arithmetic verified. **Full original racing mechanics and event semantics are not yet recovered.** Engine-extraction Gate A remains open.

## 1. Original sixteen-record effects system

The original Z80 allocator in **master bank 0, PC 8659–8693** manages RAM `E800–E8FF`: **16 fixed 16-byte records**. The status byte at `record+00` indicates vacancy when zero. The `record+01` byte participates in the requested-priority and lifetime/tick logic.

Allocator input: unsigned byte priority in register **B**. On success, the selected record address is returned in **IY**.

1. Scan 16 records in increasing address order, choosing the **first status==0** record, regardless of priorities elsewhere. Write requested priority to `record+01`; return **A=01**.
2. Only if every slot is occupied, find the **lowest unsigned priority** in existing `record+01` values. Preserve the first match on a tie. If new priority **exceeds** that minimum, select that record and replace its priority; return **A=00**. The caller must update the record's other fields.
3. When new priority is less than or equal to the minimum, reject without modifying any record; return **A=FF**. This is why handlers test `RET M` after the call.

**Validation:** The independent allocator model was compared against a bounded interpreter executing the actual original Z80 instructions on **17,536 diverse pool/request states**, with **zero mismatches**: 5,400 free-slot allocations, 11,497 priority replacements, 639 rejections. These include all requested priorities, first-vacancy positions, saturation/ties and deterministically seeded random occupied pools.

Private report: `local/engine-extraction/effect_allocator_opcode_parity.json`. Public reproducible checker: `tools/arcade_effect_allocator_opcode_parity.py`. All original ROM bytes are excluded from GitHub.

### Per-frame effect-object lifecycle

Master routine `8694–86F4` traverses the same 16 × 16-byte pool:

| Status at record+00 | Original update branch | What is confirmed |
|---|---|---|
| 0 or 1 | `8694→869C` | Issues standard output/cleanup command through `D958`, then writes status=0 |
| 2 | `86AD→86B0` | Advances record tick and handles fixed data/output payload from fields +02 onward |
| 3 or higher | `86D7→86E7` | Decrements/normalises tick, reads a 16-bit callback at `record+02/+03`, executes via `CALL 18C0` / `JP (HL)` |

Routine `8700` sets status=0 and issues the same output/cleanup command, releasing a record. The precise graphics/animation primitives passed through `D958` remain unclassified.

The allocator's effect priority and the updater's tick both use `record+01`; therefore **do not replace them with a generic modern particle system** or assume priority/lifetime are independent. Recovered behaviour must be preserved in the eventual Godot implementation.

## 2. Original nine car-event consumer paths

Every handler begins at the original program address listed below. The effect-allocation call sites and shared handler paths were validated against the executable's Z80 instructions. Their gameplay causes are **not yet proven**.

| Trigger car-record bit | Handler PC | Effect-object action | Direct sound command |
|---|---|---|---|
| IX+32, bit 5 | `6C1C` | Allocates at `6C2A`, populates an effect with a follow-up callback | `0BA6` (command via lookup) |
| IX+32, bit 3 | `6DFA` | Jumps into shared `6E0F` allocator at `6E12` | Not direct |
| IX+32, bit 4 | `6E06` | Falls into the same `6E0F` allocation logic | Not direct |
| IX+31, bit 5 | `6EA6` | Allocates at `6EB1` | `0B98` (conditional gateway) |
| IX+7E, bit 2 | `6A18` | May allocate **two** effects at `6A1E` and `6A2D` | Not direct |
| IX+31, bit 4 | `6A3A` | Conditional allocation at `6A46` | Not direct |
| IX+32, bit 6 | `6B61` | Updates an existing object and allocates at `6B8F` | May reach sound indirectly |
| IX+32, bit 7 | `6BA2` | Updates an existing `E8xx` effect via the pointer in IX+30 | Not direct |
| IX+33, bit 3 | `6A51` | Allocates at `6A69`, installing an effect callback | `0BA6` (command B=29h) |

Thus **eight of the nine handlers can allocate/reuse records** (eight distinct allocator call locations because two handlers share one), while the ninth services an existing record. Seven of the nine handlers immediately clear their own triggering event flag; the other two take alternative paths.

### Original sound command transport

The original master `0BA6` wrapper switches the master ROM bank using port `F4` and calls the **bank-3 program at `2000`**, then restores the previous bank. The latter sends command bytes to the original 80186 sound interface through I/O ports **05 (command-high)** and **06 (command-low)**, with a command/acknowledgement handshake.

This is not a recovered music engine or a complete mapping of which sound plays for each game event. Command-code meanings, sound chip scheduling and replacement commercial audio remain separate extraction work.

## 3. Original event-flag producers — work upstream from visual effects

The earlier consumer at `3006–3044` can now be linked to several source instructions, including events set in *another master ROM bank*. These are confirmed **static SET instructions**, not evidence that every site executes in the same race state.

| Consumed flag | Instruction-aligned SET producer sites |
|---|---|
| IX+32 bit 5 | Master bank1 `3B89`, `454E`, `5697` |
| IX+32 bit 3 | Master bank1 `50F7` |
| IX+32 bit 4 | Master bank1 `526A` |
| IX+31 bit 5 | Master bank0 `2AB8` |
| IX+7E bit 2 | Master bank0 `5BC9` |
| IX+31 bit 4 | Master bank0 `7083` |
| IX+32 bit 6 | Master bank1 `3BE7` |
| IX+32 bit 7 | Master bank0 `6B86` (set by the preceding event handler) |
| IX+33 bit 3 | Master bank1 `3736`; additionally bank1 `375A` sets the same flag on the **IY-indexed** record |

**Eleven IX-addressed producer instructions** were specifically identified and checked. Original code also writes whole indexed bytes, and untraced branches can supply additional sources; this is **not** a complete producer list.

The bank1 `50F7` and `526A` sites occur near reads of the recovered vehicle geometry state, making them priority candidates for following geometry→event causation. The bank1 `3736/375A` sequence sets the same status flag in two car-related records. Neither the exact impact threshold nor the event's gameplay interpretation has been established.

Verified bank-aware source scanner: `tools/arcade_event_flag_provenance.py`. Private original-derived reports and test data remain outside GitHub.

## Gate A: what's next

1. Run original game under **debugger-enabled MAME** and track these 11 producers to their nine consumer paths under controlled collision, wall contact, boosting and pit scenarios.
2. Trace the geometry-conditioned bank1 code feeding `50F7` and `526A`, including all branches and RAM/movement thresholds.
3. Recover the complete original physics/collision response (position/velocity updates, damage, grip and obstacle behaviour), not merely its visual effects.
4. Correlate effect IDs, original `D958` output paths and 80186 sound commands with in-game events and replacement art/audio.
5. Preserve the approved **original-engine-first rule**. No speculative physics, Godot gameplay development, concept builds or release-readiness claim yet.

**Validation limits:** These results establish static code structure and isolated original opcode parity. Emulator-level executed event coverage has **not** yet been obtained.
