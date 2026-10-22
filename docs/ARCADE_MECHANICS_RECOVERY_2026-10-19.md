# Indy Carz — Recovering original 1991 arcade mechanics

**Evidence record, 19 October 2026.** Primary input: user-supplied original
`indyheat.zip`, whose 27 member checksums were verified against MAME's ROM
manifest. Machine references: MAME `leland.cpp`, `leland_m.cpp`,
`leland_v.cpp`. Local decoded binaries and complete listings are deliberately
excluded from this public repository.

## Recovered directly from original Z80 code

| CPU address, bank | Observed original operation | Confidence |
|---|---|---|
| Master fixed `0C4A` | Loop across physical controls for three players, corresponding to car records `E080/E180/E280` | Verified statically |
| Master fixed `0D6A` | Decode 5-bit dial phase delta through 32-entry response table at `0DCD`; check encoder's direction bit; output signed sample into indexed car record | Verified statically |
| Master fixed `0D89` | Process active-low input transitions and write per-car input state | Verified statically; exact button semantics require dynamic trace |
| Master bank 0 `341E` | Read indexed steering sample (IX+122), build X-ROM slot-0 word address using low byte `7F`, read X-ROM upper byte and double it before applying accumulator/carry branches | Verified statically, downstream vehicle behaviour incomplete |
| Master bank 3 `7519` | Read indexed steering state (IX+121), update indexed field (IX+123) with overflow-dependent branches | Verified statically; game-state interpretation not yet complete |
| Master fixed `145F/1490/14C1` | Jump through inline 16-bit addresses into master banks 2/3/4 with automatic bank restore | Verified statically |
| Master bank 0 `83D5` | Initialises indexed records in 0x100-byte steps, with five active racer records and an additional `E580` initialization slot | Verified statically |

### Input bytes, faithfully recovered

- Five racer state record bases, `IX`: `E080,E180,E280,E380,E480`.
- Three physical wheel inputs: master I/O `00,01,02`.
- Three turbo-button inputs: master I/O `0D,0E,0F` (button identity established by MAME input mapping; full effect has not yet been traced).
- The hardware's 8-bit direction/5-bit phase wheel encoding is documented by
  MAME's `dial_compute_value` in `leland_m.cpp`.
- The game's `0D6A` code produces signed wheel-response values from a
  **32-entry** table, ranging `-62..+62` for valid original input samples.
- The game stores current steering sample at car-record offset `+122` (`0x7A`),
  and conditionally stores its primary copy at offset `+121` (`0x79`).
  Another routine updates car-record offset `+123` (`0x7B`). Calling that
  final vehicle heading without recovering its uses would be premature.

The independently written Godot `scripts/mechanics/ArcadeWheelInput.gd`
implements precisely the MAME encoder + original ROM response lookup. It does
**not** fabricate car acceleration, traction, steering yaw, opponent AI or turbo.

### X-ROM steering data confirmed

At master bank-0 address `341E`, the code uses:

```text
X-ROM slot 0 word address = ((signed response & 0xFF) << 8) | 0x7F
Read X-ROM word's upper byte, then double it as 8-bit arithmetic
```

All **41 distinct signed steering sample values** reachable from the ROM's
32-entry lookup were checked against the actual reconstructed X-ROM. The X-ROM
upper byte matched `n-1` for positive `n`, or `n` otherwise, interpreted
modulo 256; the doubled signed outputs range from `-124` to `+122`.
This is an observation for these samples and this X-ROM address; it is **not**
the full movement/heading formula. Original accumulator, threshold, collision,
upgrades and tyre calculations still require analysis.

Run the optional verifier privately with:

```bash
python tools/arcade_logic_probe.py local/rom-recovery/master.mame_runtime.bin
python tools/arcade_steering_xrom.py \
  local/rom-recovery/master.mame_runtime.bin \
  local/rom-recovery/xrom.mame_runtime.bin
```

### Bank switching clarified

The `CALL` instruction at fixed `112C`, for example, is followed by an
inline target word and transfers through trampoline `145F` to master
**bank 2, address 2012**, which jumps to a real routine at `35A7`.

A naive linear disassembly wrongly treats inline destination bytes as code,
or reads the wrong bank as the target. Reconstructing the original bank
mapping is essential for all further mechanic recovery. Across the fixed
trampoline table beginning at `111D`, **25 distinct wrappers** were located
for bank 2 (5), bank 3 (17) and bank 4 (3). These are static findings, not
proof that every entry runs during racing.

## Further verified numeric stages — pedal and drive-byte arithmetic

- Master bank-0 **$67B5–$67D5** (pedal): original 8-bit analogue pedal,
  car-record offsets IX+$58 and IX+$59, X-ROM slot-1 multiplication,
  threshold and saturation into car-record offset IX+$57.
  Original X-ROM multiplication is exactly
  `(left * right + 128) >> 8` over **all 65,536 8-bit input pairs**.
  A bounded original Z80 interpreter checked **41,536 pedal cases** with zero
  mismatches against the independently reconstructed formula.
  Port: `scripts/mechanics/ArcadePedalInput.gd`.

- Master bank-0 **$7039–$7043**: original X-ROM multiplies its input
  byte by `0x60` (96), rounding at half of a 256th, and assigns register B.
  The preceding car-state counter at $7036 is not included in this stage.
  Port: `ArcadeDriveStages.exceptional_input_branch`.

- Master bank-0 **$709C–$70AB**: original X-ROM multiplies B by
  `0xA6` (166), adds car-record field IX+$54, and calls the
  `$0A9C` saturation helper on 8-bit carry; exact outcome is
  `min(255, ((B * 166 + 128) >> 8) + car_field_54)`.
  **65,536 value/field combinations**, plus **256 preceding branch
  inputs**, have been validated against original ROM/X-ROM data.
  The bounded opcode verifier is
  `tools/arcade_drive_opcode_parity.py` and port is
  `scripts/mechanics/ArcadeDriveStages.gd`.

These are verified original arithmetic **subroutines**, not complete vehicle
acceleration, traction or fuel logic. The next step is tracing and converting
the remaining context around $7027–$7315, including car-indexed status,
shared speed variables, collision conditions and dynamic upgrade factors.

## Godot engine and mobile camera

The development branch now contains a Godot 4.4 `project.godot` and
testable GDScript input/steering/pedal/drive-byte components. GitHub Actions
runs `tests/godot/test_mechanics.gd` on a real headless Godot installation.
There is also a presentation-only camera
`scripts/camera/ArcadePortraitCamera.gd` to provide smooth speed-aware
panning without changing track geometry, orientation or pace.

These are **building blocks**, not a playable race. The test suite deliberately
prohibits invented or approximated car physics.

## Scope still open

1. **Original runtime traces** under debugger-enabled MAME for input→RAM state
   changes, AI loops, speed, collision, fuel, turbo and pit events.
2. Recover and verify car movement and collision routine, upgrade impacts
   and AI strategy across all active ROM banks.
3. Recover per-race QRAM tilemaps and wall, lane, checkpoint and pit-zone
   geometry without retaining/releasing original track artwork.
4. Implement *verified* physics in the Godot project and compare deterministic
   traces against the original arcade reference.
5. Build upgraded original artwork, the approved smooth portrait camera pan,
   Android controls, menus and APK once core mechanic parity is demonstrated.

**No arbitrary 5% slowdown, generic replacement physics, track rotation or
track redesign is authorised.**

## Validation

- Pure Python synthetic regression suite runs in GitHub Actions without ROMs.
- Godot adapter is written but a Godot runtime has **not** been executed here.
- Numeric extraction has been exercised locally on verified original arcade
  ROM data; it does **not** demonstrate a completed game.


## Further original arithmetic recovered — 20 October 2026

**Master Z80 bank 0, PC 0x71D9–0x71F9 inclusive.**
A separate, bounded original-instruction execution check recovered this exact
signed, 16-bit *intermediate* calculation:

1. The master Z80 reads a byte from car record offset **IX-0x0B** and multiplies
   it by register **B** through X-ROM slot 1 (8-bit rounded fixed-point table).
2. It doubles the 8-bit lookup output with wraparound and shifts the result
   left by four bits.
3. The high/sign bit of RAM location **E76C** controls conditional 16-bit
   two's-complement negation. The result is left in **DE** when control
   passes to PC **0x71FA**.

Independently reconstructed expression (unsigned 16-bit result):

`base = (((B * car[IX-0x0B] + 128) >> 8) * 2 & 255) << 4`

`DE = (-base if (RAM[E76C] & 0x80) else base) & 0xFFFF`

**131,072 cases were tested against bounded execution of the original ROM
instructions** (all 256 values of B × all 256 values of IX-0x0B × both
sign-branch outcomes), with **zero mismatches**. See
`tools/arcade_displacement_opcode_parity.py`; invoke it using
`python tools/arcade_displacement_opcode_parity.py local/rom-recovery/master.mame_runtime.bin local/rom-recovery/xrom.mame_runtime.bin`.
ROM-free synthetic tests are in
`tests/test_arcade_displacement_opcode_parity.py`.

**Do not label this a recovered velocity, traction or collision formula yet.**
It is one numerical stage within the larger racing update path. The semantic
roles of RAM[E76C], IX-0x0B and the downstream DE usage must be demonstrated
through full instruction/state tracing. No new Godot gameplay implementation
was made for this step, per the engine-extraction-first release gate.

**Next target:** Determine how this DE intermediate combines with the
remaining car state in the following PC 0x71FA–0x7315 branches, then
recover the complete per-frame racer update and cross-bank collision
processing. Debugger-enabled MAME reference traces remain an open prerequisite
for final arcade parity.


## Original trigonometric coordinate integration — 20 October 2026 (verified)

### Original 256-entry angle tables

The original arcade master ROM contains an 8-bit cosine table at **CPU 0xA200–0xA2FF**
and an 8-bit sine table at **CPU 0xA500–0xA5FF** (when ROM mapping is enabled).
Every original value matches the independently generated formula over all 256 angles:

```
angle_radians = angle_byte * 2 * pi / 256
cos_byte = clamp(round(128 * cos(angle_radians)), -128, 127)
sin_byte = clamp(round(128 * sin(angle_radians)), -128, 127)
```

The stored results are signed two's-complement bytes. These tables are derived
from the original ROM and should not be copied as original assets to the release.

### Original two-axis position update (master bank 0, PC 0x7530–0x7571)

This routine reads the **high byte** of 16-bit state at `E769` from
`E76A`, and the high byte of 16-bit motion state at `E76B` from
`E76C`. It uses the sine/cosine values and the original X-ROM slot-0
signed saturated multiplication:

```
signed_product = clamp(signed8(trig) * signed8(motion) * 2, -32768, 32767)
step = floor((signed_product * 4 + 128) / 256)
RAM16[E735] = (RAM16[E735] + step(sin[RAM8[E76A]], RAM8[E76C])) & 65535
RAM16[E72B] = (RAM16[E72B] + step(cos[RAM8[E76A]], RAM8[E76C])) & 65535
```

These are *position-like 16-bit accumulators*: the startup code loads initial
values into them from an indexed course/car state table (master 0x60AA/0x60B3),
and later reads them for movement and geometry. Final dynamic proof of
coordinate scale, reference frame and fixed update cadence is still required.

The independent formula matched **65,536 bounded original-Z80 opcode
executions**, 256 heading samples × 256 motion samples, zero mismatches.
The verifier is `tools/arcade_coordinate_opcode_parity.py`; it uses only
private master/X-ROM data and commits no proprietary ROM bytes.

### Original 8-value oriented rectangle geometry (master bank 0, PC 0x7572–0x75F1)

The next consecutive routine reads the high byte at **E768** (of 16-bit
angular state E767), which is **distinct** from the angle used above at E76A.
Using its own sine/cosine, it generates eight 16-bit coordinate values from
centre candidates `x=RAM16[E735]` and `y=RAM16[E72B]`:

```
s = sin8[RAM8[E768]]
c = cos8[RAM8[E768]]
RAM16[E73D] = x + 3*s - 2*c
RAM16[E737] = x - 3*s + 2*c
RAM16[E73B] = x + 3*s + 2*c
RAM16[E739] = x - 3*s - 2*c
RAM16[E733] = y + 3*c + 2*s
RAM16[E72D] = y - 3*c - 2*s
RAM16[E731] = y + 3*c - 2*s
RAM16[E72F] = y - 3*c + 2*s
```

All operations wrap to 16-bit. The resulting four symmetrical pairs have the
mathematical form of a rotated **3-by-2 half-extent rectangle** (in internal
units). The actual use of the geometry in track/car collision testing is NOT
yet recovered, so this must not be labelled the final collision algorithm.

**Original opcode parity:** 65,536 heading/centre test cases, verifying eight
16-bit output coordinates per case = **524,288 coordinate comparisons**, zero
mismatches. Tool: `tools/arcade_geometry_opcode_parity.py`. The expected
formula is independent of the bounded Z80 instruction executor, and only
private local ROM data is read.

The following routines at 0x75F2–0x7634 copy the computed geometry to a
secondary buffer at E747..E75B. Other routines at 0x61CE–0x6235 and
0x62FC–0x635C save and restore this block. Their execution sequence and
collision/terrain consumers need full dynamic verification.

**Important:** These are genuinely recovered portions of the original
low-level engine. They do not establish the complete vehicle acceleration,
tyre/slip, collision response, race rules or AI logic. Game construction remains
blocked by the approved full-engine extraction gate.


## Original six-slot state machine — 20 October 2026 (verified code structure)

The original arcade keeps six separate **0x100-byte RAM slots**, based at
`E000,E100,E200,E300,E400,E500`. Each slot has a **96-byte dynamic
working-state block** in its lowest 0x60 bytes, followed by additional
status/control fields. The IX bases `E080..E580` refer to these same slots.

Two original Z80 routines use the stack pointer for efficient exact 48-word
transfer, with interrupts temporarily disabled and the original SP restored:

- **Master bank 0, PC 0x61CE–0x6299**: load 48 little-endian 16-bit words from
  a slot's first 0x60 bytes and assign them sequentially to shared scratch
  RAM `E72B..E789` (48 × 2 bytes).
- **PC 0x629A–0x6365**: write those 48 words back into the same original slot,
  using reversed `LD HL,(nn); PUSH HL` ordering and stack pointer initially
  set to `slot+0x60`. The copy is position-preserving.
- **PC 0x5EA1–0x5F12**: explicit six-slot initialisation pass:
  load slot, set IX to `slot+0x80`, call `0x601E`, save slot.
- **PC 0x2D87–0x2E0B**: six callback dispatches using each slot's 16-bit
  pointer at **slot+0x94**, then saving the working state.
- **PC 0x2E0E–0x2E92**: six further callback dispatches using
  **slot+0x96**, then saving again.
- **PC 0x18C0** contains the Z80 indirect jump `JP (HL)`, providing the
  generic callback trampoline used by both passes.

All **48 forward transfers, 48 reversed transfers, six initialization
sequences and 12 callback sequences** were checked against the original
master Z80 executable, including their exact stack/pointer and bank addresses.

A private verification report can be regenerated with
`python tools/arcade_state_serializer.py local/rom-recovery/master.mame_runtime.bin`.

This explains **where the game stores per-car physics state** and provides
an exact starting map for dynamic tracing. It does **not** establish the
purpose of the sixth auxiliary slot, the frame rate of these callback
passes, or the destinations selected at runtime. No claim is made that
callback `0x18C0` itself implements collision or physics: it is an indirect
jump to a pointer supplied by each slot.

Future reverse engineering must read the stored callback pointers after
initialisation and trace their targets, while using the 48-word scratch
layout to identify which car values change during steering, motion,
collisions, damage and pit service.
