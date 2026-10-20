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
| Collision separation quantisation | Fixed-ROM B3C2..B3DB shifts and rounds both 16-bit signed pair separations to byte outputs B and C using floor((signed16(delta)+4)/8), wrapping modulo 256. Exhaustive 65,536 word cases, 131,072 original output bytes, zero mismatches | ENTIRE BOUNDED STAGE VERIFIED; CONTACT DECISION AND RESPONSE OPEN |
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


## 20 October — complete bank-5 contact mask addressing and angle quantisation

- **Original ROM bank switching confirmed:** the collision loop selects master bank **5** at fixed `AD64` using port F4 and restores bank **0** at `B3A6`. The correct contact-table source is bank5 region offset `0x38000`, **not** the ordinary master bank0 code/data at the same visible CPU addresses.
- **Exact contact lookup structure extracted:** 18 × 24 signed-projection bins × 16 relative-heading categories × 3 bytes = **6,912 indexed records / 20,736 bytes**, CPU addresses `2000–70FF`. First byte's sign determines whether original `B4D1..B4D3` exits; subsequent two bytes are consumed by the original response branch. Raw table classifies **4,635 negative-sign accepted entries / 2,277 early returns** (not actual game collision frequencies).
- **All 6,912 entries tested** against bounded actual Z80 instructions and the original X-ROM with **zero address, payload or acceptance mismatches**. Public code: `tools/arcade_collision_bank5_lookup.py`; the extracted original table stays private.
- **Original collision event bookkeeping:** `B4D4–B4ED` tracks old/new contact-table pointer (`E92A/E928`), first-byte status `E919` and acceptance counter `E927`. First two accepted contacts read subsequent payload bytes to `E91A/E91B`; third or later follows a different handler path. Physics semantics of those two bytes remain OPEN.
- **Original collision-response direction conversion recovered:** `A600–A639`, fixed-ROM 16×16 angle table stored at `A000–A1FF` in 2-byte stride; signed/quadrant scaling is entirely integer. **65,536 signed B/C input pairs tested** against bounded original Z80 execution, **zero mismatches**. Public code `tools/arcade_collision_angle_opcode_parity.py`.
- [Full bank5 contact/angle technical record](ARCADE_COLLISION_BANK5_LOOKUP_2026-10-20.md).
- **Still OPEN:** real collision impulse/velocity/damage after `B510`, terrain and pit/fuel/turbo logic, original track geometry, end-to-end AI/race state and debugger-enabled MAME runtime trace parity. Original-engine extraction Gate A still blocks Godot gameplay.


### Collision-contact continuation (latest)

The bank-5 6,912-entry contact table is now followed into the original
fixed-ROM code `B510–B545`. It invokes the recovered integer angle
converter at `A600` **twice** and compares the resulting byte angles.

- The first angle call's **carry flag** is consumed immediately by a
  16-bit `SBC HL,DE` involving car indexed field `-0x62`.
- After three 16-bit left shifts the final shift's carry is consumed by
  another `SBC HL,DE` involving field `-0x58`. This is not identical
  to two ordinary coordinate subtractions.
- The high bytes of both wrapped 16-bit differences (shifted left three
  bits) become the second pair of signed inputs to `A600`.
- The wrapped byte angular difference is compared against **0x40** and
  **0xC0**, selecting original PC `B546` for values in [64,192) and
  `B5AC` otherwise.
- Independent reconstruction of both return-angle **and carry** across
  **65,536** A600 input cases passed, as did **30,000** paired
  `B510–B545` gate cases against bounded original Z80 execution, all
  with **zero mismatches**.
- New verifier: `tools/arcade_collision_response_gate.py`.
  Notes: [collision mask and response angles](ARCADE_COLLISION_BANK5_LOOKUP_2026-10-20.md).

**Still unverified:** semantics of indexed words -0x62 and -0x58,
actual impulse, damage and steering changes in the two downstream
branches; hardware-emulated full-session contact parity. The full
commercial Godot game has **not** started; original-engine Gate A is OPEN.


## Exact original paired collision geometry response (20 October 2026, further)

Original master Z80 fixed-ROM response routines now independently reproduced and
opcode-checked, beyond previous broad-phase, contact table and direction tests:

- **B985–BA1F and BA20–BABA**: IX and IY car-specific 10-word
  geometry translation: add correction BC to offsets 00..08 and DE to 0A..12,
  in steps of two bytes; set car status +7C bit6. Original upper-byte
  guard redirects to routine 1689 when either signed 16-bit correction
  high byte lies in 05..FA. **20,000 original instruction cases, zero
  mismatches**, including both normal and redirected branches.
- **B546–B5AB**: first/second car contact correction, signed arithmetic
  half-shifts, original carry from the preceding B541 CP C0, a borrow
  transferred between coordinate calculations, and **carry carried from
  first-car B985 return into second-car first subtraction**. The original
  status +7C bit1 can suppress correction to an individual participant.
  Original counter E926 increments. **16,000 original-machine-code scenarios,
  zero mismatches**, conditional on this specifically identified entry path.
- **B5AC–B5C8**: byte E91B bit7 selects original IX/IY responder order;
  clear bit = pass pointers as-is; set bit = pass pointers swapped and
  mask payload with 7F, then restore pointers. **768 original opcode
  dispatch comparisons, zero mismatches**.
- **BABB–BB6B**: restores ten saved previous-coordinate words to the ten
  current-coordinate words; copies angular-state word +1C to +3C;
  conditionally reduces word +40 by its signed arithmetic one-eighth;
  sets status +7C bits0,1,6. **18,000 original opcode comparisons,
  zero mismatches**.
- Routine 1689 visibly saves diagnostics and selects original master bank 0
  before transferring to 68E0, which contains register-reporting text.
  Treat this as an exceptional diagnostic control transfer, not
  ordinary collision physics, until emulator observations establish
  its full outcome.

**Evidence:** [paired collision response and fallback](ARCADE_COLLISION_RESPONSE_2026-10-20.md);
public ROM-gated verifiers in
`tools/arcade_collision_geometry_push.py`,
`tools/arcade_collision_b546_response.py`,
`tools/arcade_collision_payload_dispatch.py`,
`tools/arcade_collision_state_restore.py` with independent ROM-free tests.
Original ROM and derived reports remain private.

**Still OPEN:** complete B5C9–B67D impulse and B67E classification,
full damage/collision event causality, actual track walls, AI, fuel/turbo,
pit, upgrade and original end-to-end executed gameplay traces. No Godot
gameplay development approved.


## New exact original collision correction stages — 20 October 2026

- **Fixed Z80 B5C9–B63B (115 bytes)** now recovered as the exact contact correction-vector synthesis. Original E91B low-7-bit input, first-car angular state, relative-heading nibble E922, signed 8-bit trig, original signed saturated X-ROM multiplier and arithmetic right shifts produce 16-bit BC/DE vectors. Exhaustive original-versus-independent test **128 × 256 × 16 = 524,288 cases, 1,048,576 words, zero mismatches**.
- **Fixed Z80 B63C–B67D (66 bytes)** now recovered as original two-car correction assignment, conditioned on each record's +7C bit1. Both-bit1-set diverts to B4EE (unresolved); one eligible car receives doubled vectors; both eligible cars receive asymmetrically reversed corrections affected by carry from first car's last coordinate translation and borrow into the second axis. **40,000 bounded original-code cases, zero mismatches** when composed with previously verified original B985/BA20 translators.
- This connects the previously recovered 6,912-entry bank-5 contact lookup and approach-angle classifier to the original geometry translation paths. It does **not** recover the remaining B67E onwards velocity/damage/heading branches or special scheduler transfer at 1689.
- Sources: [contact vector and assignment evidence](ARCADE_COLLISION_VECTOR_APPLICATION_2026-10-20.md), public validators tools/arcade_collision_b5c9_vector.py and tools/arcade_collision_b63c_assignment.py, plus ROM-free tests.
- **Next:** classify original B67E–B8E4 event and motion handling, and verify runtime contact changes in debugger-enabled MAME. Gate A remains OPEN; no new Godot gameplay.

## 20 October — exact original B67E–B6EC collision velocity projection (new)

- The original fixed master Z80 stage B67E–B6EC (111 opcode bytes) checks E919 bit 5 to select first/second car ordering. It projects each car's slot +0x41 signed input through slot +0x3F heading into signed-byte sine/cosine outputs at E91F/E920 and E923/E924, then computes signed-overflow-saturated relative D/E components through original helper 0B35.
- Signed input rounding is original SRA A / ADC A,0, equivalent to ceil(signed8(input)/2); the trigonometric X-ROM multiplication is the verified original signed 8×8 ×2 slot 0 with positive saturation. It is **not** floating-point vector normalisation or general vehicle dynamics.
- **50,000** original opcode vs independent integer-model two-car scenarios, **zero six-byte output mismatches**; 25,000 of each original car-pointer order. Original trig 512/512 samples and X-ROM high output 65,536/65,536 checked independently.
- Public, ROM-gated verifier: tools/arcade_collision_velocity_projection.py; synthetic regression: tests/test_arcade_collision_velocity_projection.py; full limitations/evidence: docs/ARCADE_COLLISION_VELOCITY_PROJECTION_2026-10-20.md.
- **Still OPEN:** B6ED and later actual contact consequences, B4EE alternative case, live MAME trace correlation, vehicle dynamics, terrain, circuits, pit/fuel/turbo/upgrades, full opponent AI and commercial release Gate A. No new Godot gameplay or concept build.

## 20 October — exact B4EE alternative collision fallback dispatcher (new)

- Fixed master Z80 **B4EE–B505**, a complete 24-byte branch, has been recovered and original-instruction tested. For each car record independently: when **slot+7C bit0 is clear**, invoke separately verified state-restoration routine BABB. If set, leave that car untouched. The original second-car call uses temporary IX/IY pointer exchange, not a new car-state structure.
- Exact four bit0 combinations restore 2/1/1/0 slots. **50,000** bounded original-opcode vs independent selection-model cases, **0 mismatches**, including original BABB state-modification model; 12,500 cases for each entry combination.
- Public verifier: tools/arcade_collision_b4ee_fallback_dispatch.py; six ROM-free regression tests. See section 6 of docs/ARCADE_COLLISION_RESPONSE_2026-10-20.md.
- The previously open **B4EE branch selection is now verified**. Physical damage, effects after B6ED, runtime car-state traces, terrain/AI/pit/fuel/turbo/championship and Gate A remain OPEN. No new gameplay implementation.


## 20 October — original contact classification and two-car event fast path

**Original source:** user-owned, SHA-256-verified master Z80/X-ROM. All proprietary binary input and contact tables remain private. Full original-engine Gate A remains OPEN; no Godot gameplay/ROM/art released.

- **B6ED–B727**: recovered the original 59-byte contact-projection/three-way control-flow stage, including original 24-category indexed lookup, the E925 0x33 mask, trigonometry at A200/A500, original signed product high bytes, extra SCF/ADC carry, signed overflow saturation helper 0B3E and destinations **B728/B778/B86C**. Independently matched **100,000 original Z80 opcode executions, zero mismatches**, plus all 512 trig bytes and 65,536 X-ROM high-product bytes. Branch coverage: B728=48,520, B778=1,802, B86C=49,678.
- **0A30–0A41**: original 18-byte conditional collision-triggered car-control byte assignment. Original IX+0x31 bit0 gates original IX+0x57 = ((IX+0x77)>>1)&0x7E. Across **65,536** original opcode input combinations, zero mismatches; A preserved. Remember physical slot offset = IX-relative offset +0x80.
- **B728–B777**: recovered full original 80-byte paired event state update for **0971's verified early-return subdomain only**. Status at IX/IY+0x5C, writes +0x5C/+0x63/+0x33/+0x77, and original 0A30/0971 calls handled exactly. **100,000** original-code paths (25,000 per 0/IX/IY/both activation pattern), zero output or car-state mismatches. **Surprising original IX behaviour:** second-car event branch calls 0A30 against first-car IX before switching IX to IY for 0971; preserve this, do not symmetrise it. If any invoked 0971 does not early-return, verifier aborts as UNVERIFIED.
- Public regression tools: arcade_collision_projection_classification.py (8 ROM-free tests), arcade_collision_contact_input_gate.py (6 ROM-free tests), arcade_collision_contact_two_car_fastpath.py (8 ROM-free tests).
- Exact evidence, source SHA-256 and limitations: **docs/ARCADE_COLLISION_CLASSIFICATION_INPUT_2026-10-20.md**.
- **Next**: original 0971 remaining branches, B778–B86B and B86C, original circuit collision and road/terrain, full motion and AI, fuel/pits/turbo/upgrades, sound, championship and controlled real MAME runtime traces. Do not substitute guessed physics.

**Memory-layout audit warning:** original IX and IY pointers sit 0x80 bytes into the physical state slots. Existing public Godot ArcadeCarRecord uses an IX-relative byte API and a logical pointer address; reconcile exact record extent and adjacent-slot boundaries under a separate test-backed audit **before** changing canonical gameplay classes.


## 20 October — original service helper 0971 return gates

- **Original fixed master Z80 0971–0984**, full 20-byte bounded entry, recovered and instruction-tested. If physical slot+0xB1 bit0 is set, return immediately with no write. Otherwise original call A is stored at slot+0xCE; if unsigned slot+0x7D>=3 return, else if slot+0xA3 is nonzero return; otherwise execution enters **0985**, which is still OPEN.
- **131,072** exhaustive original opcode vs independent branch/state comparisons: 65,536 returns at 0975, 64,768 at 097F, 765 at 0984, three inputs explicitly rejected as unverified continuation 0985. **Zero mismatches**. These are combinatorial coverage counts, **not observed gameplay branch frequencies**.
- The previously recovered **B728–B777** original two-car event model now composes all three original 0971 early-return exits instead of just BIT0/RET NZ. Reran **100,000 varied paired original Z80 cases with zero mismatches** while keeping the counterintuitive original 0A30-first-car IX helper sequence. Ten ROM-free B728 tests and seven ROM-free 0971 tests.
- Public verifier: tools/arcade_collision_service_0971_entry.py; evidence: docs/ARCADE_COLLISION_CLASSIFICATION_INPUT_2026-10-20.md.
- **Still OPEN:** the longer original 0971 continuation at 0985, B778/B86C and other collision effects, car dynamics, terrain/road/pits, AI, turbo, fuel, upgrades, complete race and championship systems, plus MAME live execution/circuit QRAM maps. Godot gameplay gate remains CLOSED.


## 20 October — original 0985 banked transfer and B86C recovery dispatch

**Fresh original arcade ROM work verified locally and pushed to this draft PR:**

- **Full 158-byte original fixed-master 0985–0A22**: recovered complete bank-controlled 24-byte LDI data-copy path reached after all 0971 early-return gates fail. Original 12-entry pointer table at 289F via verified helper 176A, five F4 bank writes, exact two sets of twelve 3-row/4-column destination bus writes, full DE/BC increment/decrement carry effects and exact final E608 restoration. **50,000 original-opcode vs independently computed full-state/bus-output cases, zero mismatches**; all twelve source selectors covered, 791 destination E-wrap cases. **Eight ROM-free regressions pass.** The destination physical video/memory mapping and gameplay display effect are NOT verified; do not assert a damage display or physics consequence.
- **Full 24-byte original fixed-master B86C–B883**: original status bit1 at each 256-byte car slot +7C controls calls to B884 (first, second, both, none), with original IX pointer swap/restore. **All 65,536 full 8-bit car-status pairs, zero original-opcode mismatches**, 16,384 in each original branch category. **Seven ROM-free tests pass.** B884 is intentionally an opaque target: this is not its full effect or game-visible response.
- Public ROM-gated verifiers: tools/arcade_service_0985_bank_copy.py and tools/arcade_collision_b86c_dispatch.py. Scope and SHA-256 source evidence: docs/ARCADE_COLLISION_0985_MEMORY_TRANSFER_B86C_2026-10-20.md.
- **Remaining first-order blockers:** B884–B8E3 nested behaviour and BC8C, B778–B86B, complete vehicle handling and physics, live MAME bank/QRAM observation, terrain, tracks, all AI/fuel/pit/turbo/upgrade/race systems. Gate A still OPEN. No original ROM or private asset bytes were committed; existing Godot gameplay and camera baseline untouched.


## 20 October — B884 original callback entry and post-callback return gate

- **Original fixed-master B884–B8AB**: exact entry and return-gate instructions for the original B86C two-car dispatcher target. Verified source car pointer offset -0x80, **LDIR of exactly 20 state bytes** from physical car offsets 0–19 to shared scratch E72B–E73E, original E941=0xFF marker, **CALL BC8C**, then bank control E608=(post-callback E608&0xF0)|0x05 and F4 output.
- Original INC A; RET Z at B8AB returns only when **post-callback E941 == 0xFF**. Other post-callback values continue into B8AC. The BC8C routine itself is deliberately *not* emulated or assumed, and controlled test inputs for its return state must not be mistaken for observed live-game output.
- **30,000 bounded opcode executions against independently modelled original entry/callback-boundary/return-gate behaviour, zero mismatches**; 15,000 controlled cases per return/continue path. **Seven ROM-free tests**. Tool: `tools/arcade_collision_b884_callback_gate.py`; evidence: `docs/ARCADE_COLLISION_0985_MEMORY_TRANSFER_B86C_2026-10-20.md`.
- **OPEN:** original BC8C branch and changes, B8AC–B8E3, second collision continuation B778–B86B, live MAME runtime evidence, full original handling/damage/AI/pits/fuel/turbo/upgrades/tracks. No original ROM/assets or speculative gameplay added to public GitHub. Commercial Gate A remains OPEN.


## 20 October — whole-original-ROM audit and B8AC original-copy follow-on

- **All original program ROM banks statically surveyed**: authentic user-owned 27-member ROM archive; original master/slave/XROM region hashes verified. 60 distinct Z80 CPU code/data memory views (16 master banks, 41 unique slave physical bank views, three fixed windows), plus full 80186 sound-ROM static listing and reset entry. 61 **linear sweep** assembly listings produced in a PRIVATE 9.4MiB archive. 4,385 candidate bank-qualified direct-call targets are **untrusted static leads, NOT confirmed live game functions or completeness percentages**. Six additional private authenticity/decoder/archive tests passed.
- **Original fixed master B8AC–B8E3** following B884/BC8C: exact **66-byte original LDIR** copies E72B..E76C scratch to physical car slot+00..+41, two original 8-bit wrapped coordinate difference guards (difference 06..F9 is a nonlocal CALL to diagnostic/scheduler 1689), then original BIT 7 car slot+B1 and conditional SET 1 at +7C. **50,000** bounded original Z80 opcode/state tests vs independent model **zero mismatches**. The two exceptional exits are deliberately NOT treated as normal collision returns. The BC8C body itself remains unverified.
- Detailed public evidence only: docs/WHOLE_ARCADE_ROM_STATIC_AND_B8AC_AUDIT_2026-10-20.md. Private user deliverables include original instruction listings and locally rerunnable analysis tools, never checked into this repo.
- **Gate A remains OPEN**: no dynamic MAME race trace, no all-game decompiler or compilable high-level source, no full geometry/terrain/AI/economy/audio/game progression, no playable commercial APK. No changes to Godot mechanics or canonical circuits/camera.

