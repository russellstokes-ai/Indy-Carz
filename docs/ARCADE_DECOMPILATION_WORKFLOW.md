# Indy Carz — Original arcade ROM decompilation/reimplementation workflow

**Status 2026-10-19:** hardware, memory layout and original input mapping confirmed from MAME; **original proprietary ROMs not provided**; no extracted physics constants or routines claimed. This is *not* a finished decompilation or a verified Godot gameplay port.

## Principle

Recover **observable rules and numerical behaviour** from the original 1991 arcade executable; implement independently in Godot/GDScript. Do not ship or commit original assembly, binary, sprites, fonts, tracks as image data, audio or commercial identities. The ROM is an analysis input only. MAME is the hardware emulator, not the original game's gameplay source code. Decompilation does not automatically output compilable Godot code.

## Confirmed machine layout

Reference driver: https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland.cpp

Reference banking/input implementation:
https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_m.cpp

- Master CPU: Z80, 6 MHz, MAME region "master", 0x90000 bytes.
- Slave CPU: Z80, 6 MHz, MAME region "slave", 0x160000 bytes.
- Audio: Intel 80186 (not part of initial gameplay recovery).
- Video: original horizontal 320 x 240 arcade presentation.
- Input: three 8-bit dial steering channels, three 8-bit pedal channels, three turbo buttons (P1/P2/P3 button1), separate player-1 button2. Inputs are read through the MAME Ataxx-era analog/input I/O implementation.
- Master ROM fixed window 0000–1fff, selectable bank 2000–9fff. Master memory region is *rotated* in 0x8000 chunks starting at offset 0x10000 during initialization.
- Slave ROM fixed window 0000–1fff, selectable bank 2000–9fff, with a different bank selector. Slave region is also rotated.
- Master accesses 0x40000-byte 16-bit interleaved X-ROM data via hardware read ports.
- ROM set short name: **indyheat**, revision 1. Never substitute NES, Amiga or ST program data.

Critical: ROM 152/153 use MAME ROM_CONTINUE for their second halves; master ROM 64 uses ROM_RELOAD with overlap. Do not simply concatenate ROM files. Each bank has a distinct address mapping.

## Stage 1 — Reconstruct program data

Provide a locally held 1991 arcade rev 1 ROM set named indyheat.zip. The recovery script checks the **14 program/X-ROM files by length, CRC32 and SHA1** before producing analysis-only local images:

\`\`\`bash
python tools/arcade_rom_recovery.py /path/to/indyheat.zip --out local/rom-recovery
python -m unittest discover -s tests -v
\`\`\`

Outputs:
- master.mame_raw.bin / master.mame_runtime.bin
- slave.mame_raw.bin / slave.mame_runtime.bin
- xrom.mame_raw.bin / xrom.mame_runtime.bin
- memory_map.json with bank mapping and output hashes

All outputs remain local; the repo ignores local/ and roms/. These reconstruct MAME CPU memory regions; they do NOT identify mechanics by themselves.

## Stage 2 — Trace original executed code

Run MAME (debugger-enabled build) with the original locally provided ROM in MAME's ROM path:

\`\`\`text
mame indyheat -debug
\`\`\`

Useful debugger commands (see https://docs.mamedev.org/debugger/execution.html and https://docs.mamedev.org/debugger/memory.html):

\`\`\`text
trace master.tr,master
trace slave.tr,slave
trace off,master
trace off,slave
dasm master_visible.asm,0,10000,1,master
dasm slave_visible.asm,0,10000,1,slave
\`\`\`

**Do not run unbounded all-session traces:** use short, repeatable windows, because Z80 tracing is extremely verbose. MAME exposes currently mapped CPU memory, not every possible bank at once. Trace both CPUs and the shared-memory interactions before deciding which chip owns physics and AI. Record the active bank/control register for every code address.

MAME debugging and ROM reconstruction can be used to identify code/data cross-references, table candidates and mutable state. No address is called a physics routine without controlled input→state observations.

## Stage 3 — Extract numerical mechanics for review

The first verified mechanic sheet must include the corresponding **CPU/bank/address**, trace or RAM evidence, exact observations, derived algorithm or parameter, and confidence status:

| Mechanic | Evidence to collect | Status |
|---|---|---|
| Steering | wheel samples; heading increments; lateral drift vs speed | UNVERIFIED |
| Acceleration/drag | pedal changes; velocity/position each update | UNVERIFIED |
| Tyres and handling | same course/driving with each upgrade level | UNVERIFIED |
| Turbo | activated/nonactivated velocity and timer samples | UNVERIFIED |
| Braking/release | deceleration after pedal release | UNVERIFIED |
| Collisions | identical contact situations, speed and headings | UNVERIFIED |
| Damage/fire | damage state changes and repair conditions | UNVERIFIED |
| Fuel | fuel delta per tick and pit refill | UNVERIFIED |
| Pit crew | pit entry/exit, service timers, upgrades | UNVERIFIED |
| Opponents | path following, speed thresholds, pit behaviour | UNVERIFIED |
| Race rules | lap gates, positions, championships and economy | UNVERIFIED |
| Tracks | collision mask / path data and lane geometry | UNVERIFIED |

The original track geometry must be reconstructed without reusing original graphic assets.

## Stage 4 — Original Godot rewrite + validation

Translate verified algorithms into *new* Godot 4 scripts using deterministic fixed-step updates. No original ROM, machine-code binary, or proprietary source will be linked or compiled into the released application.

**Approved departure:** pace approximately 5% slower than the arcade reference. Do this in a coherent simulation-speed or tuned-motion adaptation with matched AI, turbo, cornering and collision response. It must not become a separate redesign of gameplay. Portrait view uses gentle speed-aware panning of the near-original track geometry, never squeezing or rotating circuits.

Record reproducible input scenarios, arcade trace data (kept local), and Godot outputs in a delta/acceptance report. Do not claim exact parity without passing measured numerical checks.

## Blockers

1. Original **arcade** ROM (rev 1) is currently absent from the provided files/repository.
2. No controlled MAME instruction/RAM traces have been captured.
3. Exact physics formulae, AI rules, upgrade effects and circuit encoding are unknown until trace/disassembly.
4. Do not spend time building speculative physics as a substitute for extracting them.
