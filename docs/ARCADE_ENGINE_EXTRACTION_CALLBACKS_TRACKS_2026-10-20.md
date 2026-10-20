# Original arcade engine recovery — callback and course data milestone

**Recorded 20 October 2026** against original checksum-verified 1991 `indyheat` arcade ROM. Engine extraction gate remains OPEN. No new Godot gameplay work or concept build.

## 1. Two concrete original per-car callback targets

Master Z80 bank-0 initializer `0x601E`, instruction sequence `0x611D–0x612F`:

- First callback: `0x2EAF`, stored in each slot at `IX+0x14/0x15` (actual slot offset `0x94/0x95`).
- Second callback: `0x2F1E`, stored at `IX+0x16/0x17` (slot offset `0x96/0x97`).
- Six-slot first-phase callback dispatch at `0x2D87–0x2E0D`; second at `0x2E0E–0x2E91`. Both load the slot's 96-byte working state, call the pointer via `JP (HL)` at `0x18C0`, and save the working state.
- The first pass is gated by global `E67D`; the second can be reached by both branches. Actual per-frame invocation cadence still needs MAME tracing.

**New dynamic continuation discovery (master bank 3):** helper at `0x77BE` executes `POP HL; LD (IX+0x15),H; LD (IX+0x14),L; RET`. It takes the return address pushed by a `CALL 0x77BE`, stores that next instruction as the car's first callback, then returns to the prior caller. This is a resumable, stack-based state machine. Exactly **34 static CALL signatures** found in bank 3, with their potential continuation addresses enumerated privately; dynamic execution and reachability remain unverified.

Bank-3 code at `0x756B` and `0x7594` explicitly changes first callback to `0x74C9`. The two default callbacks must therefore **not** be treated as permanent. Several bank-3 event loops also read callbacks for three player slots; their runtime bank context remains open.

Verified extractor: `tools/arcade_callback_recovery.py`.

## 2. All fourteen course starting grids: 70 records

The master ROM contains a **14-pointer table at 0x6382**, pointing to 14 grids beginning at `0x639E`, each grid exactly 25 bytes. Every grid has five 5-byte car positions:

1. Little-endian 16-bit value copied to shared state `E72B`
2. Little-endian 16-bit value copied to shared state `E735`
3. 8-bit starting angle copied as the high byte of the two 16-bit angle words `E767` and `E769` (low byte zero)

Verified original `0x1767` indexes the 14-pointer table using `E699`, and `0x6095` onwards uses `IX+0x69` to select a car's five-byte position.

**Do not confuse these starting grids with complete circuit geometry.** Collision masks, AI routes, pit locations, track rendering and checkpoints remain outstanding.

Extractor: `tools/arcade_start_grid_extraction.py`. Original numeric coordinate data stays private.

## 3. Original 15-round championship programme

A separate fixed-ROM table at `0x1ABF` contains the **15 course indices in original championship order**:

`13, 12, 1, 3, 7, 8, 4, 2, 5, 11, 0, 6, 9, 10, 1`.

All 14 unique internal circuit indices occur; circuit index 1 occurs twice. Master bank-0 `0x2941` and bank-3 `0x62B4` both select the next circuit using the table and `E69B` round counter; the latter wraps the count at decimal 15 and writes selected course index to `E699`.

**Naming of internal indices to real circuit names remains to be verified**; do not guess.

## 4. Fourteen per-course spatial trigger rectangles

Master bank-0 routine `0x7A5B` uses `E699` to load:

- Per-course two-byte range from table `0x83B6` into `E95B`, compared against the high byte at `E72C`.
- Per-course two-byte range from table `0x1ACE` into `E642`, compared against the high byte at `E736`.

Code `0x7ABE–0x7AE2` accepts lower-inclusive, upper-exclusive bounds and additionally requires:

`((RAM8[E72C] - car[IX+0x66] + 3) & 255) < 6`.

These are original **course-specific spatial event bounds**, not verified track walls or confirmed pit/lap triggers. Their purposes and downstream status transitions remain open.

Extractor: `tools/arcade_course_bounds.py`.

## Verification and remaining work

All three new tools verify original game instructions against matching ROM hashes. ROM-free synthetic tests exercise the dispatch/control-flow patterns, table indexing, race sequence and spatial range calculations. **Static opcode validation is not a substitute for runtime mechanics parity**.

Still required before Gate A closure:

- Debugger-enabled MAME execution of original arcade ROM, both Z80s traced through playable race states.
- Actual 34 candidate continuation sites classified by event; live bank selection and timing confirmed.
- Complete acceleration, steering, terrain collision, car impacts, boosts, fuel, damage, repairs, AI decisions, upgrades, pit strategy and lap/score state machines.
- Original per-circuit live tilemap/QRAM, track boundaries, checkpoint and pit-zone extraction.
- Audio CPU command map, output timing, menus, save and high-score semantics.
- Full component acceptance dataset, including original-vs-independent state trace parity.

**Existing Godot input arithmetic adapters are unchanged.** No new gameplay build, provisional physics or artwork was introduced.
