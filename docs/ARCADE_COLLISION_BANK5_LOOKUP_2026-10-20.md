# Indy Carz — Original bank-5 collision contact mask and angle engine

**Recovery date:** 20 October 2026  
**Source:** independently checksum-verified 1991 arcade `indyheat` master Z80 ROM and X-ROM, supplied privately by the user.  
**Gate:** Engine extraction still OPEN. **No Godot gameplay, concept or build work.**

## 1. Critical bank-switching discovery

The collision-pair enumeration and separation code recovered previously executes from **fixed master ROM** at `B057–B4A2`, rather than from a normal selectable Z80 bank.

At fixed PC `AD64–AD6C`, the game preserves the upper nibble of the master bank control byte `E608`, ORs the low nibble with `05`, stores it and writes the result to I/O port `F4`. This selects **master ROM bank 5** for the entire contact lookup. At fixed `B3A6–B3B0`, the game restores the low nibble to 0 via the same port.

**This bank switch is crucial.** Merely disassembling the fixed collision code with bank 0's contents would read a mixture of unrelated data and instructions at its calculated addresses, producing completely invalid contact results.

The original contact table lives in **master bank 5 region offset `0x38000`**; visible CPU addresses `0x2000–0x70FF`. Source SHA-256 of the locally reconstructed 20,736-byte table:

`6f220e853ecb22bd0f5c5697400c651c4ac06e9335e40eb832cfdb611c9febec`

Do not include the table itself or any extracted original ROM data in the public repository.

## 2. Exact lookup geometry and original Z80 arithmetic

After the previously recovered fixed-PC `B45A–B4A2` relative/rotated contact-projection tests have passed, their accumulator values are **two unsigned cell coordinates**:

- `axis0`: integer `0–17` (18 bins).
- `axis1`: integer `0–23` (24 bins).

The original Z80 code `B4A3–B4D3` computes:

```text
orientation = (((IY_heading - IX_heading) & 0xFF) & 0xF0) >> 4
cell = (axis0 * 24 + axis1) * 16 + orientation
record_offset = cell * 3
lookup_cpu_address = 0x2000 + record_offset
```

The first multiplication `axis0*24` is supplied by the original signed X-ROM multiply `axis0*12*2`. Z80 `ADD A,L` carry increments the high byte, avoiding a subtle wrap error when `axis0*24+axis1 >= 256`. Four subsequent `ADD HL,HL` instructions multiply by 16; four `RRCA` instructions move the relative heading's high nibble to the low nibble, followed by `HL = 3*HL` and base `0x2000`.

Each **3-byte table entry** has:

1. Byte 0: signed contact-acceptance and response-status value. The original `LD A,(HL); OR A; RET P` rejects the entry if bit 7 is clear; if bit 7 is set it continues into response logic.
2. Byte 1: additional response data loaded into shared RAM `E91A` at `B507–B509` on the appropriate accepted-contact branch.
3. Byte 2: additional response data loaded into shared RAM `E91B` at `B50C–B50F` on that branch.

These remaining payload bytes must **not** be renamed as impulse magnitude, direction, speed or damage until their downstream use is decoded and verified.

**Exhaustive verification:** Independent index arithmetic versus bounded execution of original Z80 `B4A3–B4D3` and original X-ROM over all **18×24×16 = 6,912 table entries**, with **zero address, payload or sign-test mismatches**.

| Raw bank-5 table classification | Entries |
|---|---:|
| Sign-bit set (continues to accepted-contact handler) | 4,635 |
| Sign-bit clear (early return) | 2,277 |
| Total | 6,912 |

These are **raw table-entry classifications**, not observed collision probabilities during an arcade race. The upstream geometric checks reject many prospective pairs before the table is accessed.

Public tool: `tools/arcade_collision_bank5_lookup.py`. It can optionally export the original 20,736-byte table into a **private local directory** for further analysis, but never into public GitHub or an Android game package.

## 3. Original accepted-contact bookkeeping

The fixed-ROM continuation `B4D4–B4ED` writes:

- Previous contact table pointer `E928` → `E92A`
- New contact table pointer → `E928`
- Current sign/status byte → `E919`
- Increments accepted-contact counter `E927`

The counter is cleared at `AD71` at the beginning of the broader collision-pair processing pass. If incremented `E927 < 3`, it enters `B506` and loads the two additional table bytes into `E91A` and `E91B`. On the third or later accepted contact, the routine takes a different conditional processing route involving `BABB`.

This is a **confirmed event-count branch**, not proof of a maximum number of collisions or effects displayed in a frame. It matters for exact replay because third-and-later accepted contacts do not follow the same path as the first two.

## 4. Original collision direction quantiser `A600–A639`

One of the accepted-contact response routines at `B510` invokes `A600`, a fixed-ROM function that converts two signed byte components (`B` and `C`) into an 8-bit direction.

The actual algorithm uses:

1. Sign/quadrant tests for both components.
2. Bitwise complement for negative inputs.
3. Repeated unsigned right shifts of one component together with signed right shifts of the other until magnitudes fit four bits.
4. Lookup through the original **256-entry, 2-byte-stride table at `A000–A1FF`**.
5. Integer complementary/quadrant transforms including `CPL`, `ADD 0x81` and `NEG`.

Table SHA-256: `60959ac9359a5c5aa9da0b39e9fc18c4be48e08e2e7a9d588c6f019c7db12f93`.

Bounded original Z80 instruction execution and an independent high-level reconstruction agreed on all **256×256 = 65,536** possible input pairs, both in the table index and the resulting angle byte, with zero mismatches.

This is the exact original integer angle converter. It is **not** interchangeable without validation with floating-point `atan2`.

Public tool: `tools/arcade_collision_angle_opcode_parity.py`.



## 5. Exact collision-response directional branch (B510–B545)

Further original Z80 analysis establishes the **approach-angle classifier**
called after the original accepted-contact data has been read. It invokes
the original `A600` angle conversion **twice**, comparing the current
relative separation direction with another direction calculated from
two indexed 16-bit fields at original offsets `IX/IY-$62` and
`IX/IY-$58`.

**Critical precision detail:** the original `A600` routine returns
not only an 8-bit angle in register `A` but also an **observable carry
flag**. The immediately following `SBC HL,DE` at `B51F` consumes that
carry. The last of three `ADD HL,HL` operations then supplies another
carry flag to the second 16-bit `SBC HL,DE` at `B531`. A rewrite that
simply subtracts both car field pairs with ordinary subtraction will be
wrong at specific negative/quadrant boundaries.

A separately reconstructed equivalent of the original gate is:

```text
angle1, carry0 = A600(B, C)   # B/C from prior signed contact projection
difference1 = (IY.word[-0x62] - IX.word[-0x62] - carry0) & 0xFFFF
B = ((difference1 << 3) & 0xFFFF) >> 8
carry1 = (difference1 >> 13) & 1

difference2 = (IY.word[-0x58] - IX.word[-0x58] - carry1) & 0xFFFF
C = ((difference2 << 3) & 0xFFFF) >> 8

angle2, _ = A600(B, C)
delta = (angle2 - angle1) & 0xFF

if delta < 0x40 or delta >= 0xC0: jump B5AC
else: proceed at B546
```

All **65,536** possible signed-component inputs were independently checked
against the original `A600` opcodes for both **angle and carry**. Then
**30,000 controlled comparisons** between independent arithmetic and bounded
execution of the original `B510–B545` instructions passed without a
mismatch, including unsigned wrap, 16-bit carry propagation and the angle
boundary branches.

Tool: `tools/arcade_collision_response_gate.py`; the model and
`A600` flags are in `tools/arcade_collision_angle_opcode_parity.py`.
The original array bytes remain excluded from GitHub.

**Unverified interpretations:** these indexed words may represent motion
components, but their precise storage meaning and update cadence need
proof. Both branch outcomes lead to further contact-response code and
are deliberately labelled by their original CPU addresses, not by
unsupported assumptions about damage or impact types.

## 6. Remaining collision recovery


Original Z80 code after the table lookup, particularly `B510–B5AC` and the handlers near `B5C9, B985, BA20`, uses relative velocity components, current/previous position-like state, status flags and additional X-ROM lookups. Some branches call `BABB` and others modify individual car records.

The major remaining extraction tasks are:

- Identify the precise meaning and generation of all two-byte table response payloads.
- Trace and independently reproduce the original force/heading/velocity changes following accepted contact, including all branches and special cases.
- Identify the original per-car damage/status transitions arising from contact, and separate effect/sound consequences from gameplay physics.
- Recover barriers, terrain, fuel, turbo, pit stops, upgrades and AI elsewhere in the complete game.
- Execute controlled original game scenarios under debugger-enabled MAME. The current container lacks MAME, so numerical routine parity is **not** full executed-game parity.

**Do not start Godot gameplay** until the previously approved Gate A has been satisfied. Only the original-extraction tools, reports and regression tests belong in this pass.
