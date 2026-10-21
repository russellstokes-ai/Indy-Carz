# Original arcade bank-4 22BA metric: complete bounded X-ROM mathematics

**Date:** 21 October 2026  
**Source:** privately authenticated, user-supplied 1991 Indy Heat original arcade rev-1 master Z80 and X-ROM.  
**Scope:** genuine bounded full-routine numerical recovery, **not** completed game AI/collision/physics. Original copyrighted program bytes and X-ROM lookup contents stay outside the public repository.

## Why this matters

The previously recovered first bank-4 far-call path at **20A8–213E** executes **CALL 22BA** at CPU address **213F**. This newly verified **75-byte original routine** at **bank 4, CPU 22BA–2304** performs a two-stage fixed-point lookup and returns one unsigned 16-bit value in HL.

The routine was previously an unknown numerical dependency in the original car-selection code. Its entire bounded arithmetic is now independently reproduced with exact integer operations, without invented floating-point physics.

## Verified original inputs and output

- Original **D = car IX+02**, **E = car IX+04**; two separate original 8-bit fields combined into a temporary word DE.
- **B = original E638**, verified as **2 or 4** from the separately recovered second bank-4 initializer's 14-course control table.
- Original global bytes **E639**, **E623**, and original car byte **IX+3A**.
- Original X-ROM **slot 1 low output** read through memory-mapped address FFFE twice; this lookup's formula was independently checked for all 65,536 unsigned 8×8 input pairs.

Independent exact maths:

    round8(a,b) = (a*b + 128) >> 8
    DE = (car_IX_plus_02 << 8) | car_IX_plus_04
    Q  = (((E639 - E638 + 1) & 255) << 8)

    if Q < DE:
        return DE

    fraction = min(255, (Q - DE) // E638)   # verified E638 2 or 4
    first    = round8((car_IX_plus_3A * 2) & 255, fraction)
    second   = round8(first, E623)
    HL       = (DE + (second * 4)) & 65535
    return HL

**Original Z80 details preserved:**

- SUB B; INC A wraps at 8 bits before the high-word subtraction. OR A explicitly clears carry before SBC HL,DE.
- The early return uses JR NC / EX DE,HL / RET to return the initially combined DE byte word without X-ROM multiplications.
- CP B / JR C and RRA / RR L right shifts implement a capped divide by 2 or 4, with incoming carry consumed exactly.
- SLA H doubles the car source byte **modulo 256**, so byte inputs 128 and 0 both produce a zero multiplicative factor.
- Original X-ROM slot1 **low** is the verified rounded unsigned result; the original slot1 **high** output is a separate lookup and remains uncharacterized.
- ADD A,A / RL H / ADD A,A / RL H constructs an exact 16-bit 4×second, and ADD HL,DE wraps at 16 bits.

## Actual original-machine verification

Original bank4 instruction bytes 22BA–2304 have pinned SHA-256: 3a2d4fc9529375ad9b0c0b847228e936b88edb5655c78ed47d542b380127a6ec.

The privately reconstructed original Z80 opcodes and real original X-ROM slot1 low results were executed with a strict, bounded opcode interpreter and compared with independently written integer maths:

| Verification | Result |
|---|---:|
| Original instruction-model comparisons | **100,000** |
| Mismatches (branch, output, fraction, intermediates or HL) | **0** |
| Original inputs taking the early DE return | **38,608** |
| Original inputs computing the full result | **61,392** |
| Computed fraction saturated at 255 | **58,113** |
| Computed fraction requiring shifted division | **3,279** |
| Original X-ROM slot1 low table operand pairs verified | **65,536/65,536** |

The case counts are controlled input cases, **not real race frequencies**. No original X-ROM table bytes or original program ROM were committed.

Public original-ROM-gated verifier: tools/arcade_bank4_metric_22ba.py. ROM-free tests: tests/test_arcade_bank4_metric_22ba.py.

## Remaining downstream work

Although original 22BA's **numerical HL result is exact**, the rest of its bank-4 caller after 213F and how the result ultimately affects original AI steering, player handling, collisions, strategy or race-state transitions still need recovery and controlled runtime validation.

The original fourteen circuit QRAM surfaces, all complete game physics/AI systems and sound processing also remain open. This result should not be called a proven damage, fuel, pit or car-speed equation solely because it occurs in car-selection code.

No new Godot game, speculative physics, replacement circuit geometry, copyrighted graphic/music asset or Android APK was created. The canonical unrotated tracks and gentle bounded portrait camera remain protected.

**Original engine commercial extraction Gate A remains OPEN.**
