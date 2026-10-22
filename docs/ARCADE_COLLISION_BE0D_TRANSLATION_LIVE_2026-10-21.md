# Collision geometry translation: BE0D-BE67

**Original arcade recovery, 21 October 2026.** The original game data
and private MAME memory captures remain outside the public repository.

This 91-byte bounded original Z80 stage uses two 16-bit target/reference
pairs. It writes the first target to E731 and applies the wrapped
target-minus-old difference to E72D, E72F, E733 and E72B if nonzero.
It then writes the second target to E73B and applies that wrapped
difference to E737, E739, E73D and E735 if nonzero. Execution continues
at original collision retry PC BCA5.

Original code SHA-256:
34dc15f002f171e4ded0ab435abfbbb1f9e13ea590da366802c8fa142c9a2da9.

## Original-code verification

An independent integer/byte-state model matched **100,000** executions
of the authentic Z80 instructions, zero mismatches. Inputs were evenly
distributed across both-delta-zero, first-axis-only, second-axis-only,
and both-axis-nonzero cases (25,000 in each group). Output comparison
included every 8,192-byte shared-RAM state image and both branches.

Verifier: tools/arcade_collision_be0d_translation.py.
Tests: tests/test_arcade_collision_be0d_translation.py.

## Live arcade verification

The running original game was observed without any state injection.
Read-only debugger samples at entry BE0D and exit BE65 captured **22**
complete calls, original frames 2421 through 28892, across all five
original racing cars.

| Case | Actual calls | Mismatches |
|---|---:|---:|
| X-only change | 9 | 0 |
| Y-only change | 12 | 0 |
| Both axes change | 1 | 0 |
| Neither axis changes | 0 | 0 |

Car IX counts: E080=3, E180=5, E280=5, E380=2, E480=7.

Original private trace SHA-256:
d0c64cc1b1ae99640268ceb413c87f48496a6722beb02cb882248aef1a37a59c.

Reproduce via tools/mame_capture_collision_be0d.lua (private original
ROM required) and check with tools/arcade_live_collision_be0d_translation.py.
The public audit emits counts and checksum only, not private state bytes.

## Godot and limits

scripts/mechanics/ArcadeCollisionTranslation.gd implements only this
verified state transformation on a copied original E000-FFFF memory
image. Godot tests verify wrapping, conditional axis updates and
unrelated-memory preservation. It does not introduce guessed physics.

**Still missing:** the upstream contact impulse, tyres/surface
interactions, wider collision states, acceleration, AI, pits,
fuel/turbo/upgrades, original circuit collision surfaces and complete
original-game playback parity. Engine extraction Gate A stays OPEN.
Approved circuits/camera remain unchanged.
