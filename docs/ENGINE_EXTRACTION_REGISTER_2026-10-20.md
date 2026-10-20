# Indy Carz — Entire Arcade Game Extraction Register

**Updated:** 20 October 2026  
**Source:** user-supplied 1991 arcade `indyheat.zip`, all 27 ROM members validated against the MAME `indyheat` manifest.  
**Gate:** **A — original engine recovery: OPEN**. No production gameplay implementation, substitutes, prototype or concept build authorised.

## What has actually been extracted or verified

| Component | Actual evidence | Recovery state |
|---|---|---|
| ROM inventory | Exact original arcade set and checksums, 27 entries | VERIFIED |
| Master game CPU | Z80 6 MHz, 0x90000 reconstructed ROM image with correct bank rotation | MEMORY MAP VERIFIED |
| Slave CPU | Z80 6 MHz, 0x160000 reconstructed image, bank selector decoded | MEMORY MAP VERIFIED |
| Special bank switching | 25 genuine fixed-code trampoline call sites with inline bank targets, banks 2/3/4 | STATIC FLOW VERIFIED |
| Cross-bank code inventory | Conservative CFG for both Z80s; master 39,006 bank-qualified candidate instruction contexts; slave 3,064. Includes duplicate fixed-code contexts and unconfirmed branches | STATIC ONLY |
| Steering hardware | 3 analogue dial channels, MAME 5-bit phase/direction encoding | VERIFIED |
| Player steering processing | Original 32-entry signed response lookup at master 0x0DCD; routine 0x0D6A, state offsets +0x79/+0x7A; further steering arithmetic in banks 0 and 3 | PARTIALLY VERIFIED |
| Pedal | Original channel selection I/O 0x0B, input 0x09, X-ROM slot-1 lookup, IX+0x57 output; bounded opcode parity tests | PARTIALLY VERIFIED |
| Original state-record initialisation | Original master bank-0 code 0x83FF..0x8447 initialises SIX 0x100-byte records at E580, E480, E380, E280, E180, E080 with descending slot ordinals 5..0 and bit masks 20,10,08,04,02,01. Five racing cars plus auxiliary state; purpose of sixth is still open | VERIFIED STRUCTURE |
| Original working-state layout | Each of six 0x100-byte records at E000..E5FF contains an independent 0x60-byte (48-word) working state at offset 0; routines 61CE..6299 / 629A..6365 load/save this via shared scratch E72B..E789 using stack pointer transfers | EXACT SERIALIZER VERIFIED |
| Pairwise car collision prefilter | Master fixed B057..B39E: all 15 unordered pairs among six 256-byte slots, identical 56-byte instruction blocks; bit7 status gate and two six-unit upper-byte position tests. Exact carry=-1 into second axis; shared contact call at B3B1 | EXACT 15-PAIR PROGRAM + 31,500 OPCODE CASES VERIFIED; FULL IMPACTS OPEN |
| Pairwise contact-entry filter | Fixed B3B1..B3C1 excludes pair if both slot+7C bit0 are set, or either slot+B3 bit1 is set; subsequent narrow contact code remains unknown | EXACT ORIGINAL EARLY RET GATES, 256 OPCODE CASES VERIFIED |
| Original second-callback event fanout | Master 2F1E dispatches a course-specific spatial result from 7AB4 into three distinct branch paths, then at 3006..3044 invokes nine conditional handlers using indexed car state bits; seven immediately clear their trigger bit. Additional masked event branch at 3045 and tail 689D | INSTRUCTION FLOW VERIFIED; HANDLER PURPOSES UNVERIFIED |
| Original six-slot callback passes | 5EA1..5F12 calls 601E once per slot during initialization; 2D87..2E0B and 2E0E..2E92 each dispatch six per-slot function pointers at +0x94 and +0x96 through 18C0 (JP HL), with state copy before/after. 12 callbacks statically verified | EXACT DISPATCH STRUCTURE VERIFIED; TARGETS/TIMING OPEN |
| Human/AI input selection | First three racer slots can be human/AI, two default AI; dispatch at master 0x6793 and AI entry 0x2263 | DISPATCH VERIFIED |\n| Original AI accelerator input | Master bank-0 0x22A2–0x22B1 stores car IX+0x57 = ((IX+0x77) >> 1) & 0x7E; B = (((IX+0x77)>>1) - (IX-0x45)) & 0xFF. 65,536 bounded original-opcode input cases checked, zero mismatches. Rest of AI pending | NUMERIC STAGE VERIFIED |
| Two drive arithmetic stages | Z80 bank-0 PCs 0x7039 and 0x709C, original X-ROM multiplication and saturation | NUMERIC STAGES VERIFIED |
| Intermediate movement stage | Z80 bank-0 PCs 0x71D9–0x71F9: multiply B × (IX−0x0B), scale, conditional signed negation from RAM E76C | NUMERIC STAGE VERIFIED |
| 256-step angular trigonometric data | Master 0xA200–A2FF cosine and 0xA500–A5FF sine, 512/512 signed bytes exactly equal clamp(round(128 trig(2πa/256)), -128,127) | COMPLETE TABLE MATH VERIFIED |
| Exact two-axis movement projection | Bank-0 PCs 0x7530–0x7571: signed saturating X-ROM multiply of trig(high(E769)) and high(E76B), step = floor((signed product×4+128)/256); accumulates into E735 and E72B. 65,536 bounded original-opcode cases passed | EXACT STAGE VERIFIED; FULL VEHICLE UPDATE OPEN |
| Original eight-value vehicle geometry | Bank-0 PCs 0x7572–0x75F1: produces symmetric 16-bit geometry around E735/E72B with 3×sin/cos and 2×sin/cos offsets; 524,288 original instruction coordinate outputs checked without mismatch | EXACT GEOMETRY STAGE VERIFIED; COLLISION CONSUMERS OPEN |
| X-ROM slot 0 | **Signed 8-bit × signed 8-bit × 2, saturated at +32767**, all 65,536 operand pairs checked with 0 mismatches | ENTIRE OUTPUT VERIFIED |
| X-ROM slot 1 low byte | **(unsigned8(a) × unsigned8(b) + 128) >> 8**, all 65,536 pairs checked with 0 mismatches | ENTIRE OUTPUT VERIFIED |
| X-ROM slot 1 high byte | Separate table of 65,536 bytes; mathematical meaning still unidentified | OPEN |
| Original track tile graphics | 16,384 original 8×8 tiles, six planar bitplanes decoded privately | GRAPHIC ENCODING VERIFIED |
| Background tilemap memory | QRAM 256×128 8×8 tiles, 0x10000 bytes; tile code assembly from MAME hardware driver recovered | ADDRESSING VERIFIED |
| Complete circuit layouts | Original per-race QRAM remains dynamic, not present as plain static ROM tilemaps | OPEN |
| Race collision shapes/lap gates/pit boundaries | Must distinguish gameplay data from visual graphics | OPEN |
| Audio CPU | Intel 80186 ROM layout and sound ROM odd/even placement/mirroring reconstructed | MEMORY MAP VERIFIED |
| Audio entry | Reset vector FFFF0 = far JMP FF D8:0000, physical entry FFD80 | VERIFIED |
| Sound samples | Separate externally clocked DAC ROM bytes u8/u9; 0x40000-byte region | MEMORY MAP VERIFIED |
| Game sound commands and playback rules | Traces, port handling and sound program control flow not recovered | OPEN |
| EEPROM | Original 256-byte EEPROM manifest verified | PRESENT; SEMANTICS OPEN |
| Original full acceleration, drag, grip, braking and steering/yaw | Numeric intermediates identified, surrounding state machine incomplete | OPEN |
| Car collisions, crashes, fire, damage, turbo | Original routines and tuning not yet identified end-to-end | OPEN |
| Fuel, pit stops, repairs, upgrade costs/effects | Needs gameplay execution/state traces | OPEN |
| AI steering, racing strategy, pit choices and difficulty | Dispatch recovered only; algorithm remains unknown | OPEN |
| Lap counting, race order, championship, standings, prize economy | No complete extracted data/logic yet | OPEN |
| HUD, menus, title sequence, scoring UI and high scores | Visual/control-flow recovery incomplete | OPEN |

## New evidence on 20 October

- **Exhaustive original X-ROM table analysis:** the two mathematical outputs shown above matched 131,072 actual original table entries without a mismatch. They can be recreated using formulas, avoiding the need to bundle those original ROM tables into the commercial game.
- **Conservative Z80 instruction and banked-control inventory:** all master and slave bank regions were swept privately, producing candidate assembler listings and machine-readable control-flow maps. The original 25 special fixed-code bank wrappers are handled as calls with *inline destination words* and correct bank selection.
- **Audio inventory:** 80186 reset entry and external DAC mapping established separately from graphics/physics.\n- **Original computer-driver input stage:** exact accelerator-byte assignment and saved difference recovered from master 0x22A2..0x22B1 and exhaustively tested across all 65,536 input pairs.\n- **Six record initialisation:** original master 0x83FF..0x8447 sets up six indexed car-related slots (five race cars and one additional slot), assigning distinct ordinals and bit masks.
- **Private reports:** full bank candidate assembler listings, reachable-code listings, cross-reference summaries and X-ROM verification outputs. These are **not reconstructed source files** and are not part of the public repository.

## Critical limitations

A **flat disassembly or linear sweep is not a full decompilation**. Ataxx-era bank switching, indirect control flow, compressed/static tables, runtime-generated QRAM maps and multiple processors all require controlled dynamic analysis. Code/data separation must be proven; the apparent count of decoded instructions **must never** be used as a percent-complete metric. We have not verified the original full game engine or produced compile-ready original gameplay source.

MAME's open hardware driver is **not the original Leland game's source code**. No engine constants or AI rules should be guessed merely because some related arithmetic bytes are understood.

## Ordered Gate A extraction work (before Godot gameplay)

1. **Runtime capture:** launch the authentic arcade set in debugger-enabled MAME, verify original code-banking, read all five car state records and global race RAM every fixed update. Capture control changes for each driver and original output; pay special attention to E767/E769 angular values, E76B signed motion and E72B/E735 position-like accumulators.
2. **Frame/update-loop:** decode the *runtime values* of the six per-slot function pointers at offsets +0x94/+0x96, follow 12 calls through JP(HL) at master 18C0, map the master/slave CPU handoff and frame cadence; correlate each callback with the 48-word car-specific scratch records.
3. **Vehicle core:** decode speed, acceleration, off-throttle deceleration, lateral behaviour, heading transforms and position integration. Validate full input-to-coordinate traces.
4. **Impact and terrain:** boundaries, walls, car collisions, damage, recovery, spin, fire and off-track slowdown.
5. **Race management:** checkpoints, lap progress, ranking, finishing logic, pits, service timers, fuel and turbo effects.
6. **AI and upgrades:** opponent path/target/traffic logic, difficulty, pit strategy, upgrade economy and effects.
7. **Circuits:** capture each of 14 distinct race tilemaps, collision masks, pit/lap data, and duplicate/repeat race sequence. Original geometry retained, with only user-approved minor changes.
8. **Rest of full game:** title/menu/rules/results/championship/high-score state machines; EEPROM behaviour; complete 80186 sound and sample command map.
9. **Parity dossier:** per-subsystem source bank/CPU address, inputs, state transitions, deterministic test vectors, exact parameters, original-vs-independent outputs, known unknowns.

**Only when complete enough to faithfully reproduce the original gameplay may the Godot commercial build gate open.** No alternate prototype is planned.

## Runnable extraction tools on Draft PR #2

- `tools/arcade_rom_recovery.py`: original Z80/X-ROM reconstruction\n- `tools/arcade_ai_opcode_parity.py`: verified bounded original AI pedal byte mapping (not complete AI)
- `tools/arcade_state_serializer.py`: original six 96-byte working-state records, exact 48-word roundtrip and 12 indirect per-slot callbacks
- `tools/arcade_coordinate_opcode_parity.py`: full 256-step trig mathematical reconstruction, 65,536 original Z80 two-axis position update cases
- `tools/arcade_geometry_opcode_parity.py`: original 16-bit 8-point geometry mapping, 524,288 coordinate comparisons against bounded Z80 execution
- `tools/arcade_banked_cfg.py`: conservative cross-bank Z80 structural graph (runtime mechanics unverified)
- `tools/arcade_logic_probe.py`, `tools/arcade_steering_opcode_parity.py`, `tools/arcade_pedal_opcode_parity.py`, `tools/arcade_drive_opcode_parity.py`, `tools/arcade_displacement_opcode_parity.py`: recorded original arithmetic stages
- `tools/arcade_xrom_math.py`: exhaustive two-table math verification
- `tools/arcade_audio_inventory.py`: sound 80186 and DAC ROM reconstruction
- `tools/arcade_track_recovery.py`, `tools/mame_capture_trackmaps.lua`: original tilemap recovery preparations (MAME capture not yet run)\n- `tools/mame_capture_carstate.lua`: bounded 12,000-frame original master RAM capture of E000-E9FF, including six initialized racer-related state records (**unexecuted; requires local MAME**)\n- `tools/arcade_ram_delta_analysis.py`: computes per-field RAM change frequencies from captured frames, with no original state bytes in its JSON output; synthetic tests available

All original binary data, extracted graphics and candidate disassembly remain **private**, never committed to this public repository. Original game art/code and audio are not authorised for inclusion in the Android package merely by changing its name.

## MAME documentation

- Driver: https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland.cpp
- Z80 master/slave banking: https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_m.cpp
- QRAM and graphics: https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_v.cpp
- Runtime memory tooling: https://docs.mamedev.org/luascript/ref-mem.html
- Debugger: https://docs.mamedev.org/debugger/


## 20 October callback/circuit/championship extraction (subsequent work)

- **Default first and second callback targets are now confirmed:** first at master `2EAF`, second at `2F1E`, installed by routine `601E` into each slot's callback fields `+94/+96`. Twelve six-slot dispatch records verified against original code.
- **Coroutine-style continuation mechanism:** bank-3 helper `77BE` saves its caller's return PC to the first callback pointer and unwinds to the enclosing caller. 34 *candidate* yield-call signatures and two explicit redirects to callback `74C9` found in bank 3. Reachability and runtime selection remain unverified.
- **All 14 starting grids recovered:** `6382` is a 14-pointer table, followed by 14 × five 5-byte position-and-heading records = **70 positions**. Source course index `E699`, car starting-grid selector `IX+69`. Original numeric source records are private.
- **Original championship schedule recovered:** fixed code reads 15-byte sequence at `1ABF` using round counter `E69B`, wrapping after 15 rounds. All 14 original internal course indices appear, with internal course 1 repeated.
- **14 per-course coordinate gates recovered:** bounds tables at `83B6` and `1ACE` are loaded into `E95B` and `E642` and tested at `7ABE..7AE2`, with exact half-open comparisons and a six-unit relative condition. These are NOT confirmed to be pits, lap lines, collision barriers or specific events.
- Technical record: [callback and original circuit-data milestone](ARCADE_ENGINE_EXTRACTION_CALLBACKS_TRACKS_2026-10-20.md).
- Tools: `tools/arcade_callback_recovery.py`, `tools/arcade_start_grid_extraction.py`, `tools/arcade_course_bounds.py`. Synthetic tests require no ROM data.
- **Still blocked:** original full racing engine and live MAME traces; Gate A has NOT passed; no Godot gameplay or commercial game build was started.

## Latest dependency: postevent event-handler fanout

The second-phase callback's nine indexed BIT/CALL-NZ handlers have now been
recovered instruction-by-instruction, including the seven immediate self-clearing
flag handlers and two handlers with different entry logic. The global E67D gate
controls whether original course spatial event routine 7AB4 is reached.
See [original handler dispatch record](ARCADE_ENGINE_EXTRACTION_CALLBACKS_TRACKS_2026-10-20.md)
and `tools/arcade_second_phase_dispatch.py`.

**Next:** trace callback targets through their state changes and hardware
interactions, identify game semantics, then use controlled MAME RAM/CPU
traces to verify which branches execute during actual racing. The MAME
runtime blocker is still open; this static inventory is NOT gameplay parity.


## Further recovery: original effects/events and audio gateway (20 October)

- **Original 16-slot effects allocator** at master bank0 `8659–8693`: fixed `E800–E8FF` pool of 16 × 16-byte records. First available slot chosen; when full, lowest unsigned priority replaced only by a strictly higher request (first match on ties); otherwise reject with `A=FF`. Independent formula versus bounded ORIGINAL Z80 instructions: **17,536 checked allocator cases, zero mismatches**.
- **Original effect scheduler** at `8694–86F4`: status 0/1 cleanup; status 2 fixed-format output; status 3+ per-record callback from `+02/+03` through `18C0`. Source route `8700` clears a record. Tick/priority share the `+01` byte; do not casually replace this with generic particles.
- **Original nine car-event handlers**: eight may allocate effect records (eight distinct `CALL 8659` instruction sites because two handlers share a common path), one updates an existing `E8xx` object. Seven handlers immediately clear their trigger bit. Their gameplay *causes* remain unverified.
- **Audio transport**: master wrapper `0BA6` changes ROM bank and calls bank3 `2000`, which writes sound command high/low bytes through ports `05` and `06`; conditional wrapper `0B98`. Exact audible sample mapping and all gameplay causes are still OPEN.
- **Original event producer links**: 11 instruction-aligned `SET` sites verified across master banks0/1 for the nine event bits. In particular, bank1 `50F7`/`526A` write distinct car flags after geometry calculations; `3736` and `375A` set corresponding IX/IY record flags. Runtime execution, all possible writers and the precise physics meaning remain OPEN.
- Sources: [effect and event flag recovery](ARCADE_EFFECTS_AND_EVENT_FLAGS_2026-10-20.md), `tools/arcade_effect_allocator_opcode_parity.py`, `tools/arcade_effect_event_inventory.py` and `tools/arcade_event_flag_provenance.py`, with ROM-free tests.
- **Next:** Trace these event producers under live MAME execution, correlate with geometry and actual collisions/fuel/pit conditions. Engine-first commercial-release Gate A is still OPEN; no Godot gameplay, prototype or speculative engine.


## Original 15-pair prefilter and ROM alias

New [original collision candidate reconstruction](ARCADE_COLLISION_PREFILTER_2026-10-20.md):
- Every unordered pair of six car-related 0x100-byte slots is explicitly tested by the original fixed ROM B057..B39E. Each of the 15 56-byte blocks is byte-for-byte accounted for, with CALL B3B1 as the shared next stage.
- The first status gate, both original coordinate comparisons and the two early returns inside the contact handler have been isolated and compared directly against bounded original Z80 instruction executions: **31,500 prefilter cases + 256 entry-gate cases, zero mismatches**.
- **Crucial original carry behaviour:** a successful CP 06 on the first axis leaves carry set, so the second SBC HL,BC subtracts an extra 1 from the second 16-bit coordinate difference. This cannot be replaced by symmetrical floating-point distance thresholds.
- **ROM alias confirmed:** fixed master A000..DFFF duplicates master bank-1 2000..5FFF; treat these as the same source code rather than separate modules or instruction counts.
- Lower-level contact geometry, collision responses, damage and interactions with terrain are still OPEN, and do not become verified merely from the candidate filter.
