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
