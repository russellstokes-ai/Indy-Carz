# Original Indy Heat — exact six-slot collision prefilter

**Evidence recorded:** 20 October 2026  
**Source:** privately supplied, SHA-256-verified 1991 *Indy Heat* arcade master Z80 image.  
**Status:** Pair enumeration, coarse tests and the first two shared contact-entry rejection conditions recovered. **Complete collision resolution still OPEN.** No Godot gameplay changes.

## 1. Fifteen explicitly unrolled car-state pair checks

The original master program contains **15 contiguous, 56-byte sequences** in its fixed-address ROM window `B057–B39E`. These enumerate all unordered pairs of **six 256-byte records**, in lexicographic order:

`(0,1), (0,2), (0,3), (0,4), (0,5), (1,2), (1,3), (1,4), (1,5), (2,3), (2,4), (2,5), (3,4), (3,5), (4,5)`.

Every one of the 15 sequences was matched **byte-for-byte** against its respective original instruction template, including:

- the two slot addresses and bit-field eligibility check;
- the original 16-bit coordinate-subtraction instructions;
- the original upper-byte coarse-range tests;
- the selected `IX` and `IY` slot record pointers; and
- the original shared handler call at **`B3B1`**.

The six slots are at `E000, E100, E200, E300, E400, E500` and the selected `IX/IY` car-record bases are `slot + 0x80`. All six appear in pair processing. **Whether the sixth slot is an additional active racer, auxiliary simulated object or a context-specific vehicle must be determined from actual runtime state**, not inferred just from the number of pairs.

### ROM alias avoids double-counting routines

In this ROM version, the fixed `A000–DFFF` CPU-addressed bytes are **identical to the ROM material visible in master bank 1 at `2000–5FFF`**. They are the same program data mapped through two windows, not independent code requiring two decompilations. This was compared across the complete 16,384-byte interval.

Some prior static listings show both `bank1:30xx` and fixed `B0xx` as separate-looking code. The pairwise calls execute to the **fixed-ROM PC `B3B1`**, and the fixed `B0xx` range is the preferred canonical address for the pair loop.

## 2. Original pair prefilter equations

The original CPU copies 16-bit values at offsets **`slot+00`** and **`slot+0A`** from each candidate. It first requires the high bit of at least one slot's `slot+7C` status byte.

Let `A` and `B` be the two original slot records. The independent model reproduces the original instructions as follows:

```text
if ((A[0x7C] | B[0x7C]) & 0x80) == 0:
    skip_pair

delta0 = (word16(B, 0x00) - word16(A, 0x00)) & 0xFFFF
if (((delta0 >> 8) + 3) & 0xFF) >= 6:
    skip_pair

delta1 = (word16(B, 0x0A) - word16(A, 0x0A) - 1) & 0xFFFF
if (((delta1 >> 8) + 3) & 0xFF) >= 6:
    skip_pair

IX = address_of(A) + 0x80
IY = address_of(B) + 0x80
DE = delta0
HL = delta1
CALL 0xB3B1
```

**The subtraction of 1 on the second axis is intentional and important.** The first successful Z80 `CP 06` sets the carry flag; intervening instructions do not reset carry before the second `SBC HL,BC`. We verified this by executing the original instruction bytes, rather than simplifying both comparisons into a generic box-distance check.

The first gate is an observed **bit-7 test**, not a confirmed semantic claim that bit 7 universally means car enabled. The initial coarse test also does not itself prove a physical collision: it only decides whether to call the deeper original routine.

## 3. Shared original collision-entry rejection conditions

The initial 17 bytes of **`B3B1–B3C1`** implement two further early-return checks:

1. Return immediately if **both** participants' `slot+7C` low bit is set.
2. Return immediately if **either** participant's `slot+B3` bit 1 is set.

Only when neither condition blocks does control advance into the deeper pairwise calculations beginning at **`B3C2`**. Those calculations and the subsequent collision forces, direction changes, damage and sound/events are **NOT YET VERIFIED**.

## 4. Original opcode parity result

The new independent mathematical model was compared against an original-instruction interpreter that runs each of the 15 authentic 56-byte pair routines until its skip or shared-call boundary:

| Test | Actual original instructions compared | Mismatches |
|---|---:|---:|
| Pairwise coarse checks, all 15 slot pairs | **31,500** | **0** |
| Shared `B3B1` early-return flag combinations | **256** | **0** |

The 31,500 cases cover first/second axis edges, negative and positive differences, wraparound, status bit variants and deterministic random inputs. They include **11,850 routes to the shared `B3B1` candidate call**. This number is a test-coverage count, not an actual race collision frequency.

Public tools:

- `tools/arcade_car_pair_broadphase.py` — authentic opcode templates, exact bounded instruction interpretation, independent model and original private-ROM-gated verification
- `tests/test_arcade_car_pair_broadphase.py` — ROM-free synthetic structural and boundary regressions

To independently verify using the private original ROM memory image:

```bash
python tools/arcade_car_pair_broadphase.py \
    local/rom-recovery/master.mame_runtime.bin \
    --out local/recovery/original_pair_broadphase.json
```

The resulting original-derived report and executable ROM input remain private.

## 5. Next recovery target and gate

Follow **`B3C2` onward** through the original rotated-coordinate checks, narrow contact testing, separation/velocity updates and paired event flags. Map the outgoing response calls (including routines around `B45A`, `B67E`, `B8E4`, `B985` and `BA20`), rather than assuming they are equivalent to any contemporary 2D physics library.

This stage does not resolve car-versus-wall response, terrain, turbo, pit stops, AI, championship scoring or the remaining original race system. The original gameplay implementation remains blocked by **Gate A: complete arcade-engine extraction and validation**.

**Runtime limitation:** debugger-enabled MAME is still unavailable in the current session. Bounded original opcode execution is stronger than a flat disassembly for these isolated branches, but does not establish full per-frame gameplay parity.


## 6. Original collision relative-distance scaling — recovered

Immediately after the two shared-entry flag checks, the original master
CPU routine **`B3C2–B3DB`** transforms the supplied 16-bit relative
coordinates in `DE` and `HL` to signed/rounded **8-bit** values in `B`
and `C`. The complete bounded instruction sequence is:

- Three arithmetic high-byte shifts and carry-based low-byte rotations per axis
- An original `ADC A,0` rounding step
- Output register B for the first axis, C for the second

Its bit-exact independent mathematical equivalent is:

```text
def axis_word_to_byte(word16):
    signed = word16 - 65536 if word16 >= 32768 else word16
    return ((signed + 4) >> 3) & 255

B = axis_word_to_byte(DE)
C = axis_word_to_byte(HL)
```

The original signed/right-shift and rounding behaviour is important for
negative coordinate separations; naive division with truncation to zero
would differ for many contacts. The independent model was validated against
the original Z80 instruction bytes over **all 65,536 input words**, checking
**131,072 output bytes** (both axes), with **zero mismatches**.

Tool: `tools/arcade_collision_delta_scale.py`. ROM-free regression:
`tests/test_arcade_collision_delta_scale.py`.

**Remaining from B3DC onward:** rotated contact geometry and direction
tests (including the B45A function), contact classification, velocity
changes, damage/event flag writes and two-car impulse/separation handling.
This recovered scaling stage alone does NOT demonstrate complete collision
resolution or car dynamics.
