# Original Z80 2AD6–2B76 banked-event staging

**22 October 2026. Engine extraction gate remains OPEN.**

Original bank0 Z80 code at `2AD6–2B76` selects one of four staging groups
from the car's `IX+3A` byte, reads two bytes from the original mapped
`3F00–40FF` memory view, and prepares four 16-bit words in master RAM
`E900–E907`. The selected word is one byte at the computed source address
and a second byte 25 addresses later. Earlier groups default to `0013`;
later groups default to `0001`.

**Bank dependency (hardware mapping now verified):** All source addresses
`3F00–40FF` lie in the master Z80 `2000–9FFF` banked ROM window.
MAME's port-F4 low nibble selects one of 16 MAME-rotated ROM banks;
the original opcode tests alone do not establish the **live F4 latch**
at every call. The caller must provide the authentic mapped source bytes
or a full rotated master image plus an actually observed F4 value.
See [master F4 mapping](ARCADE_MASTER_F4_BANK_MAPPING_2026-10-22.md).

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

The `2B77–2BCC` F4 CPU bus sequence and MAME bank/view mapping are now
separately documented. Next: verify the live F4 latch and QRAM effects,
event consequences and the rest of the original race engine with MAME traces.