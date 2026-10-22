# Original Z80 2AD6–2B76 banked-event staging

**22 October 2026. Engine extraction gate remains OPEN.**

Original bank0 Z80 code at `2AD6–2B76` selects one of four staging groups
from the car's `IX+3A` byte, reads two bytes from the original mapped
`3F00–40FF` memory view, and prepares four 16-bit words in master RAM
`E900–E907`. The selected word is one byte at the computed source address
and a second byte 25 addresses later. Earlier groups default to `0013`;
later groups default to `0001`.

**Bank dependency:** Source addresses at `4000+` are in a banked ROM
window. Original opcode parity verifies the selection arithmetic, but does
not establish which bank the live arcade hardware exposes for every frame.
The caller must provide the actual active mapped source bytes.

| Input `IX+3A` | Group | Selected E900 word | Source address |
|---|---:|---|---|
| 0–11 | 0 | E900/E901 | `3F50 + value` |
| 12–35 | 1 | E902/E903 | `3F38 + value` |
| 36–59 | 2 | E904/E905 | `3F20 + value` |
| 60–255 | 3 | E906/E907 | `3F08 + value` |

Original `LDI` instructions and their carry/HL/DE/BC behaviour were
interpreted directly. The initial original `PUSH HL` preserves `0108` on
the Z80 stack for later hardware continuation.

**Verification:** 100,000 independent original-opcode comparisons,
zero mismatches across all four groups, with and without caller-provided
table data. Public ROM-free unit tests cover all 256 input values for
each of the five physical car slots, source address bounds, missing-data
stops and exact E900 staging writes.

**Boundary:** With a complete caller-provided 512-byte source window,
execution stops at `2B77`, immediately before original F4 bank selection
and QRAM writes. Without it, execution stops at the actual first `LDI`
(`2AED`, `2B14`, `2B3E` or `2B63`). No ROM bytes or proprietary source
table values are embedded in the public implementation.

The verified `2AD1` gate is now connected to this stage in the Godot
per-car driving path. It does **not** return to `709B` until the original
banked hardware continuation is recovered. Original circuit geometry,
camera and prior physics were left unchanged.

Next: verify `2B77–2BCC` F4 writes, original hardware bank mapping,
event effects and the rest of the original race engine with MAME traces.