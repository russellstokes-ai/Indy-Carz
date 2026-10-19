# Indy Carz — Arcade binary inspection, 19 October 2026

## Input verification — completed

Source file: user-provided `indyheat.zip` (kept outside GitHub).

- Archive SHA-256: `942abd5d3ab79d1f0ca9c08f5087618a68689bc7199979da5c03f3fc6ed14096`.
- 27 ROM files (including EEPROM); all file CRC32 and SHA-1 values match the MAME `indyheat` ROM declarations.
- Correct set: **Danny Sullivan's Indy Heat (1991) arcade**, not an Amiga/NES conversion.
- Verified 14 master/slave/X-ROM program and data chips for extraction.

## Binary reconstruction — completed locally

MAME's ROM load/reload/continue operations and `rotate_memory` were applied:

| Runtime memory region | Size | SHA-256 of reconstructed local image |
|---|---:|---|
| Master Z80 | `0x90000` | `521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7` |
| Slave Z80 | `0x160000` | `e9afaa243befc45c4d91a110ae210bd6a051e5beef61ae4d045f4d6fa6b426cd` |
| X-ROM (16-bit interleaved) | `0x40000` | `1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb` |

Static reset-path inspection from these images:

- Master Z80 resets at `0000`, sets stack and interrupts, selects master ROM bank through I/O port `F4`, then jumps to `83D5` (bank 0).
- Slave Z80 resets at `0000`, sets stack/interrupts, then jumps to `00A9`.
- These are **actual executable bootstrap locations**, but they are NOT identified handling, AI or race-system routines.

## Graphics and track addressing — confirmed

Using MAME's `gfx_8x8x6_planar` layout:

- Six 0x20000-byte graphics planes form **16,384 8×8, 6-bit-per-pixel background tiles**.
- The original Ataxx-era tilemap is RAM-backed, **256 × 128 tiles** (nominal 2048 × 1024 world pixels), with per-tile low/high codes from 65536 bytes of QRAM.
- A matching local grayscale source graphics atlas was decoded and checked visually. It does not represent complete race tracks or include the dynamic foreground and original palette.
- Exact per-race backgrounds require **runtime QRAM snapshots**. See `tools/mame_capture_trackmaps.lua` and `tools/arcade_track_recovery.py`.
- QRAM snapshots will not alone recover lap logic, wall masks, AI paths, pit zones or car physics; those require binary analysis and controlled runtime tests.

## Next milestone — not yet completed

1. Run the original arcade ROM in debugger-enabled MAME; the current analysis container does **not** have MAME installed.
2. Capture QRAM while each of the original 14 different circuits is displayed; identify duplicate/transition frames and reconstruct background placements privately.
3. Trace both Z80 CPUs through controlled steering, throttle, boost, collision, fuel and pit-stop events.
4. Match banked CPU addresses, RAM state changes and X-ROM data to candidate mechanics and track rule structures.
5. Independently implement precisely observed game logic in Godot; validate event traces against arcade original before marking mechanic complete.

**Honest status:** ROM verification, CPU memory reconstruction and background tile decoding are completed. **No original physics algorithm, AI code or circuit geometry is yet verified as ported.** Static decoding is not the same as running and disassembling every bank.

## Data handling

All original ROM binaries, runtime-reconstructed CPU images, tile atlases, source graphics and live QRAM snapshots remain private/local. The public repository contains tools and documentation only. Renaming a game and changing artwork does not automatically resolve all intellectual-property issues for a near-exact commercial game; address that separately before release.

## Hardware references

- MAME driver: https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland.cpp
- MAME machine and bank mapping: https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_m.cpp
- MAME graphics / QRAM tilemap: https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_v.cpp
- MAME six-plane graphic layout: https://github.com/mamedev/mame/blob/master/src/emu/video/generic.cpp
- MAME Lua memory-share reference: https://docs.mamedev.org/luascript/ref-mem.html
