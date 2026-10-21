# Original motion sign gate 7225-7244 — opcode and live racing parity

**21 October 2026, privately authenticated 1991 Indy Heat rev-1 master Z80.**
The original machine-code input, private MAME captures, copyrighted ROM,
track images and decoded assets are never committed to this public repo.

## Verified bounded driving calculation

The original fixed CPU stage at 7225–7244 reads a 16-bit word from E76B,
subtracts the incoming original Z80 DE word after clearing carry, tests
the SIGN BIT of the 16-bit wrapped subtraction, optionally replaces it
with zero, and stores the result to E76B before EX DE,HL.

The rule is exact:

    candidate = (old_motion_word - incoming_DE) & 65535
    same_sign = bool(old_motion_word & 32768) == bool(candidate & 32768)
    E76B      = candidate if same_sign else 0
    final_DE  = E76B
    final_HL  = incoming_DE

The original Z80 uses BIT 7,H, JP Z and then JP M or JP P depending
on the original sign. This is NOT host-language saturated signed
subtraction or an arbitrary floating-point acceleration model.

Original stage SHA-256:
50b80e7b8e2dc40be44f80205f465e9b15450092e42ffff3db9714b0d6fe529f.

## Genuine original instruction verification

100,000 original Z80 instruction executions against an independent
16-bit formula, zero mismatches:

| Original branch | Controlled cases |
|---|---:|
| Positive-side value retained | 38,866 |
| Positive-side clamped to zero | 25,319 |
| Negative-side retained | 15,411 |
| Negative-side clamped to zero | 20,404 |

All input/result/DE/HL/branch outcomes matched. Public checker:
tools/arcade_velocity_sign_gate_7225.py; ROM-free tests:
tests/test_arcade_velocity_sign_gate_7225.py.

## Live actual arcade verification

MAME 0.264 was run with the original game in a credited race. An
original master RAM write tap at PC 7241 checked the previous E76B,
actual DE, actual HL and the low-byte write at that CPU instruction.

**3,598 real original CPU writes, zero mismatches.** Natural-race branch
counts were positive clamp=3,271; positive keep=325; negative keep=2.
Negative clamp did not occur naturally in this 9,000-frame trace
but is covered in the 100,000 original-opcode tests.

Live events came from all five original racing slots. Private CSV
SHA-256: 768db115740d2e74a865492db8967400d515802e96b397f469563a01729282c3.

Public reproducible read-only instrumentation:
tools/mame_capture_velocity_7225.lua. Audit:
tools/arcade_live_velocity_gate_7225.py. All private data stay local.

## Godot integration and outstanding boundaries

scripts/mechanics/ArcadeVelocitySignGate.gd reproduces the original
calculation as a pure 16-bit operation and a separately callable
E000–FFFF RAM state transformation. Godot regressions verify all four
branches, register exchange, input immutability and 16-bit wraps.

The preceding DE-production stages (including bank0 71D9–71F9 and
71FF–7224), actual update timing, acceleration, steering, collisions,
tyres, terrain, turbo, fuel, AI and pit logic still need complete
runtime/ROM parity. A verified motion sign gate is NOT a complete
driving dynamics engine.

**Commercial Gate A remains OPEN. No original circuit rotations,
redesigns or changes to the approved smooth bounded portrait camera.**
