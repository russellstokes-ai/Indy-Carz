# Indy-Carz — original arcade ROM decompile / native recompile workstream

**Status:** Verified architecture + MAME memory mapping. **No original ROM bytes have been provided, disassembled or ported yet.** This document is an engineering plan, not a claim of recovered source.

## Decision

Recover actual arcade rules from the **1991 Leland Indy Heat rev 1** binaries first; rebuild the *recovered gameplay algorithms* as native C/C++ for Godot 4. Replace branding, visuals, audio and mobile UI/camera, not the arcade mechanics or track geometry. No substitute car physics or home-version-derived rules.

## Facts verified in MAME

- 2 × Zilog Z80 CPUs run master game-control and slave/video-side execution; Intel 80186 handles audio.
- MAME game selector: \`indyheat\` (rev 1), \`ataxx_state\`, \`init_indyheat\`, \`wsf\` machine configuration.
- Master memory image 0x90000 bytes; secondary ("slave") image 0x160000 bytes; banked ROM windows (0x2000–0x9fff), shared hardware memory and video/I/O registers.
- Critical: \`init_indyheat()\` calls \`rotate_memory("master")\` and \`rotate_memory("slave")\`. MAME source \`leland_m.cpp\` implements **for each 0x8000-byte bank beginning at region offset 0x10000** a rotation \`bank = bank[0x2000:0x8000] + bank[0:0x2000]\`. This transformation MUST be applied **after** reconstructing ROM regions, before disassembly or simulation.
- Input read hooks and analog output hooks are in the driver. This helps locate actual steering/accelerator control consumption.
- The original machine uses extra interleaved 16-bit \`xrom\` data; these may contain track or other tables. Determine contents with runtime traces, not guesswork.

MAME authoritative sources:
- https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland.cpp
- https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_m.cpp
- https://docs.mamedev.org/debugger/index.html

## Repeatable process

1. **Private reference setup.** Obtain a legitimately accessible Indy Heat rev 1 ROM set; keep it **outside public Git**. Run \`python tools/prepare_indyheat_rom.py --rom-set /path/to/indyheat.zip --out reference_private/prepared\` (path may also be an unpacked folder). Check all chip SHA-1s against MAME. Fail on missing/mismatched dumps.
2. **Reassemble regions.** Apply the exact \`ROM_LOAD\`, \`ROM_RELOAD\`, \`ROM_CONTINUE\`, and \`ROM_LOAD16_BYTE\` ordering documented in the MAME driver. Apply both master/slave 0x8000 bank rotations. Produce per-bank private images.
3. **Dynamic trace FIRST.** Run \`mame indyheat -debug\`. Break/watch input I/O (master port 0x00–0x02, 0x08–0x0b), race state updates, car-position RAM, collision, fuel/turbo variables. Record Z80 PC + active bank at each event, mapped memory state and controlled input sequence. Instrument both master and slave; don't wrongly assign game logic exclusively to either without evidence.
4. **Static recovery.** Load assembled fixed ROM + **each bank as a distinct address-space overlay** into Ghidra's Z80 language, or use \`z80dasm\` for round-trip assembly. Annotate cross-bank calls, input/output addresses, RAM structs, table references, path data, self-modification if any. Disassembly is **not equivalent** to recovered original high-level source.
5. **Recompile test.** Confirm a small selected Z80 routine can be disassembled and reassembled to produce the same bytes under the same layout; verify opcode semantics against emulation. This validates extraction, **not** that the whole game already runs natively.
6. **Native conversion.** Translate recovered Z80 gameplay routines into a deterministic C/C++ core, retaining integer/fixed-point maths, byte overflow, tick order and original update rate exactly. Compile shared library for Godot via a native extension (GDExtension or thin C API wrapper). The original Z80 assembler itself cannot compile directly into Android ARM code.
7. **Golden trace parity.** Feed identical recorded steering/throttle/turbo events into the original reference and native core. Compare per-tick XY/heading, velocity, fuel, turbo, damage, AI and laps; only consider port complete when differences are documented/resolved.
8. **Modern display, original world.** Godot renders premium original art and uses slow 2D camera panning over an unchanged circuit coordinate system. Recover original track/race data; no shape-changing or rotation for portrait fit.
9. **Production hardening.** Regression replay sets for all original circuits, pit entries, collisions, 5-car AI races, upgrades and championships; stable Android export, device safe areas and touch latency.
10. **Source/rights gate.** Do not add unlicensed game ROMs, recovered code, ripped sprites/audio or other protected material to the public repo. New branding alone does not remove possible rights implications of incorporating recovered original implementation; review reuse rights before release.

## Precise caution: what can / cannot be automated

**Can automate:** ROM validation and map construction, 0x8000 bank rotation, bank-image export, debugger trace parsing, instruction disassembly, candidate code/data partitions, some asset/table identification, scripted replay comparisons.

**Cannot assume automatic:** machine code -> human-quality original C source; fully correct data/code separation; cross-CPU interactions; readable physics function names; 1-click Z80-to-Android recompilation; legal clearance for copying proprietary binary code.

## ROM-to-native milestone gate

Before investing in all graphics/tracks:
- Full hash-verified master/slave images plus xrom assembled with correct transforms.
- A clearly identified per-frame car position/heading update path with bank, PC, input and RAM evidence.
- One isolated recovered **mechanical** routine translated to C++ and compared in a golden trace to arcade behaviour.
- An architecture decision: preserve an original algorithm with a permitted port, or implement behaviourally equivalent code if direct reuse is not cleared. Either way, no hand-designed replacement physics.

## Public repo policy

The ROM-preparation utility and these notes are public and contain only the MAME-observed mapping and new code. All raw/reassembled machine binaries, ROM-set ZIPs, trace dumps, symbols derived from binaries and screenshot/source asset material stay in an ignored private directory and are **never published here**.
