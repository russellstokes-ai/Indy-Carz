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
| Human/AI input selection | First three racer slots can be human/AI, two default AI; dispatch at master 0x6793 and AI entry 0x2263 | DISPATCH VERIFIED |\n| Original AI accelerator input | Master bank-0 0x22A2–0x22B1 stores car IX+0x57 = ((IX+0x77) >> 1) & 0x7E; B = (((IX+0x77)>>1) - (IX-0x45)) & 0xFF. 65,536 bounded original-opcode input cases checked, zero mismatches. Rest of AI pending | NUMERIC STAGE VERIFIED |
| Two drive arithmetic stages | Z80 bank-0 PCs 0x7039 and 0x709C, original X-ROM multiplication and saturation | NUMERIC STAGES VERIFIED |
| Intermediate movement stage | Z80 bank-0 PCs 0x71D9–0x71F9: multiply B × (IX−0x0B), scale, conditional signed negation from RAM E76C | NUMERIC STAGE VERIFIED |
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

1. **Runtime capture:** launch the authentic arcade set in debugger-enabled MAME, verify original code-banking, read all five car state records and global race RAM every fixed update. Capture control changes for each driver and original output.
2. **Frame/update-loop:** map the master/slave CPU message handoff, per-frame call chain, original tick cadence, indexed car record fields and global RAM references.
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
