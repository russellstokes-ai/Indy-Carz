# Original Indy Heat arcade — two-car collision response recovery

**Recorded 20 October 2026.** Source: privately supplied, independently SHA-256-matched original 1991 arcade master Z80 ROM. **Engine extraction Gate A remains OPEN.** This document describes bounded original machine-code routines, not the full collision system, playable Godot gameplay, or a commercial build.

## 1. Original per-car geometry translation (fixed Z80 B985–BABA)

The original code contains two near-identical routines:

| Routine | Car pointer | Original CPU range |
|---|---|---|
| First car correction | IX | B985–BA1F |
| Second car correction | IY | BA20–BABA |

Both accept signed 16-bit correction words in **BC** and **DE**, inspect the *upper byte* of each word before applying it, then perform:

```text
for each of five 16-bit state words at slot +0x00,+0x02,+0x04,+0x06,+0x08:
    word = (word + BC) mod 65536
for each of five 16-bit state words at slot +0x0A,+0x0C,+0x0E,+0x10,+0x12:
    word = (word + DE) mod 65536
slot[0x7C] |= 0x40     # Original BIT 6 status flag
```

**Critical guard:** each signed word's upper byte must be `0x00–0x04` or `0xFB–0xFF`. If either high byte is `0x05–0xFA`, the original program conditionally `CALL`s fixed master routine `1689` **before writing any geometry**. Routine `1689` disables interrupts, saves diagnostic state, selects master ROM bank 0, then jumps to `68E0`. The latter contains diagnostic/register-reporting text including `BANK=` and `PC`. This appears to be a diagnostic path rather than ordinary collision physics; live MAME execution is still required to establish its complete outcome.

The independent 10-word mathematical model was compared to a strict, bounded interpreter of both genuine original Z80 instruction sequences on **20,000 tests with zero mismatches**, covering both IX/IY update paths, signed wraparound and high-byte guard exits.

Tool: `tools/arcade_collision_geometry_push.py`. The original routine SHA-256 digests are pinned in the source; ROM-free synthetic code tests in `tests/test_arcade_collision_geometry_push.py`.

## 2. Exact paired normal-contact correction (fixed B546–B5AB)

The original approach-angle gate at `B510–B545` branches to `B546` only when its final `CP C0` leaves the **Z80 carry flag set**. For this entry path the pair response is:

1. Increment byte counter `E926`, wrapping to 0 when necessary.
2. If first car's `slot[0x7C]` bit 1 is **clear**, derive two signed, 16-bit correction words from the car's previous and current word pairs: previous offsets `+0x1E/+0x28`, current offsets `+0x00/+0x0A`.
3. The first `SBC HL,DE` consumes the carry flag from `CP C0`. Its `SRA H; RR L` implements a **signed arithmetic right shift by one** and leaves the original 16-bit difference's lowest bit in carry.
4. The next axis' `SBC HL,DE` consumes that **carry from the first shift**, then applies its own signed shift. The original `CALL B985` applies both correction words to first car geometry.
5. At return from `B985`, its last `ADD HL,DE` leaves a **carry** that survives `SET 6,(IX-4)` and `RET`.
6. The second car's starting subtraction can **consume that carry**, so the two corrections are not independent. If first car was excluded via bit 1, its unchanged incoming carry flows into second car instead.
7. If second car's status bit 1 is set, `RET NZ` exits without modifying it. Otherwise calculate two corrections and tail-`JP BA20` to translate second-car geometry.

This dependence on original CPU flags is why a generic symmetrical separation routine, floating-point vector push or independent collision correction would not reproduce the original game.

A separate independent arithmetic/state model was compared with bounded original Z80 execution of `B546–B5AB`, invoking the separately verified original `B985/BA20` routines, for **16,000 original-code input cases with zero mismatches**. This is the documented accepted-contact normal entry; the other original branch at `B5AC` is handled separately.

Tool: `tools/arcade_collision_b546_response.py`; synthetic boundary, car-disable, overflow-carry, counter-wrap tests: `tests/test_arcade_collision_b546_response.py`.

## 3. Original contact-table payload selects response car (B5AC–B5C8)

A separate branch uses original RAM byte **E91B**:

- If bit 7 is **clear**, pass the existing IX/IY pointers to `B5C9`, with accumulator A unchanged.
- If bit 7 is **set**, mask A with `0x7F`, temporarily swap IX and IY through the Z80 stack, call `B5C9`, then swap the pointers back.

Thus `E91B` supplies a signed-side selector plus a seven-bit argument. Its precise force/impact/angle meaning is **not yet verified**. The wrapper itself was checked for **all 256 input bytes × three pointer pairs = 768 original Z80 control-flow cases, zero mismatches**.

Tool: `tools/arcade_collision_payload_dispatch.py`; tests: `tests/test_arcade_collision_payload_dispatch.py`.

## 4. Original contact fallback restores saved state (BABB–BB6B)

The fixed-ROM routine `BABB` executes:

1. Copy **ten 16-bit words** from saved car-state block offsets `+0x1E,+0x20,...,+0x30` back into current coordinate words `+0x00,+0x02,...,+0x12`.
2. Copy angular/status-like **16-bit word** at `+0x1C` into `+0x3C`.
3. Read the 16-bit word at `+0x40`. If `((high_byte + 128) & 255) >= 160`, replace it with `word - (signed16(word) >> 3)`, preserving 16-bit wrapping. Otherwise leave it unchanged. Its exact semantic role remains unverified, although it behaves like damping of a non-negative state word.
4. Set `slot[0x7C] |= 0x43`, i.e. original status bits **0, 1 and 6**.

The independent model and a bounded interpreter of the actual original machine instructions matched across **18,000 varied original-ROM input cases without error**. Tool: `tools/arcade_collision_state_restore.py`; tests: `tests/test_arcade_collision_state_restore.py`.

Prior bank-5 recovery shows that the original contact controller can call `BABB` when it has already recorded multiple accepted table contacts. This is evidence for contact recovery, not an assertion of a particular visible crash or damage animation.

## 5. What's still missing

**Outstanding original engine work**, needed before the production Godot gate opens:

- Decode the complete `B5C9–B67D` impulse construction and its downstream `B67E` classification, with all X-ROM lookup and carry effects.
- Interpret the meaning of additional contact-table bytes, event flags, per-car state at +0x40 and all collision side effects.
- Recover complete track walls/terrain collision and surface slowing rules, fuel, turbo, damage, pits, upgrades and full AI strategy.
- Establish the executed, frame-by-frame game sequence under debugger-enabled MAME and verify original-vs-reimplementation full state traces.
- Independently implement the recovered complete mechanics in the **one commercial Godot release build** only after the approved engine extraction gate is met.

**No new Godot gameplay code, concept, placeholder physics or test APK was produced in this recovery pass.**

## 6. Original B4EE alternative collision-state fallback dispatcher — now verified

The fixed master Z80 **B4EE–B505** is a 24-byte complete alternative branch, with original-code SHA-256 `519e1ee888fbe0d931a98822814cb3ead4541f51ba31e2f385595a097f58f832`. It is reached from the previously verified B63C assignment when **both car +7C bit 1 flags are set** (other call sites have not been dynamically characterized).

The original dispatcher:

1. Tests **first car slot +7C bit 0**; if clear, calls original **BABB** to restore that car's previous saved state.
2. Tests **second car slot +7C bit 0**; if set, returns without touching the second car.
3. Otherwise temporarily selects the second car as IX, invokes **BABB**, restores the first pointer and returns.

Thus the exact four entry combinations for slot +7C bit 0 yield **2, 1, 1, 0** state restorations. They are not interchangeable with a generic no-op or physics bounce. BABB itself has already been verified with original opcodes to restore ten 16-bit position words, one angular-state word, optionally alter one other state word, and set status bits 0, 1 and 6.

The new independent dispatch model and bounded original Z80 instruction interpreter matched across **50,000 private original-code executions**, with 12,500 cases per bit combination and zero mismatches. The original BABB output model is reused rather than duplicated. Public ROM-gated tool: `tools/arcade_collision_b4ee_fallback_dispatch.py`; ROM-free tests: `tests/test_arcade_collision_b4ee_fallback_dispatch.py` (six checks).

**Scope limit:** branch selection and exact restored slot data are verified; game-visible damage, full impulse response, broader reachability and timing still require controlled emulator tracing. Original ROM inputs are private. Gate A remains OPEN.
