# Indy Carz — Independent original collision translation audit

**Audit date:** 20 October 2026  
**Original evidence:** user-provided 1991 arcade `indyheat.zip`, original MAME-rotated master ROM, SHA-256 `521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7`.  
**Gate A:** OPEN. No gameplay source/ROM or assets have been published.

## Canonical original Z80 routines

The shared original collision code has two mirrored state-translation routines:

| Routine | CPU address range | Length | Original instruction SHA-256 |
|---|---|---:|---|
| First-car IX translation | `B985–BA1F` | 155 | `400755ca6f3478bda5e4e765c420032c4fd59d94da55b0d5ebe52836eb008fb8` |
| Second-car IY translation | `BA20–BABA` | 155 | `d6aed40a17b98f3d5d3fdd14c76f4137f13b927b3fa0d68c1e44893de8c205cf` |

Both 155-byte instruction sequences have been confirmed **byte-for-byte** from the supplied original master binary. Each routine translates ten 16-bit little-endian values in the affected car's 256-byte state record:

- Five words at offsets `+00,+02,+04,+06,+08` receive signed/wrapping 16-bit displacement **BC**.
- Five words at `+0A,+0C,+0E,+10,+12` receive displacement **DE**.
- All additions wrap modulo 65536; they do **not** invoke generic floating-point physics.
- The car's status byte at `+7C` has bit 6 set at the end.
- The original state-layout and corner-generation evidence identify these ten words as one centre-plus-four-corners geometry block on each axis. This is a coherent **position/footprint translation**, not proof of a generic velocity impulse.

## Important scheduler boundary

Before updating coordinates, each routine checks the *unsigned* high bytes of BC and DE. If either lies within inclusive range `05..FA`, it conditionally calls fixed CPU address `1689`.

That target saves original execution context and switches master banking/scheduling. The bounded translation verifier must **stop at this transfer** and mark its later behaviour unresolved. Never silently model this branch as an immediate return followed by the normal translation.

The normal-return path is valid only if both displacement high bytes are in `00..04` or `FB..FF`.

## Independent private original-opcode audit

A separate locally executed audit verified the canonical translation equations against **bounded interpretation of the actual original machine instructions**:

- **20,000 distinct random 256-byte car-state and in-range displacement scenarios**
- **Both original Z80 routines executed for each scenario: 40,000 executions**
- **Ten 16-bit output words compared per execution: 400,000 coordinate comparisons**
- **Zero mismatches**
- **65,536 possible high-byte pairs classified** for the scheduler threshold; 65,436 would initiate one of the conditional nonlocal transfers and 100 are normal-return high-byte combinations

The independent audit report is retained privately at `indyheat_analysis_private/ongoing/original_contact_geometry_translation_parity.json`. No original ROM bytes, table payloads, assembled machine code or derived graphics are committed here.

Canonical public tools already exist:

- `tools/arcade_collision_geometry_push.py` — checks the mirrored original translation and the scheduler transfer
- `tools/arcade_collision_b546_response.py` — separately verifies a branch of the two-car response which calls those routines
- `tools/arcade_collision_state_restore.py` — verifies a distinct original fallback restoration path
- `docs/ARCADE_COLLISION_BANK5_LOOKUP_2026-10-20.md` — contact table and approach-angle recovery

**No duplicate production or extraction implementation is retained.** Redundant overlapping experimental checkers were removed in favour of these canonical tools.

## Outstanding work

The `1689` scheduler transfer, full contact-response branches, effect flags and potential damage consequences, geometry-wall contacts, terrain, AI, pit/fuel/turbo and runtime MAME comparison are not covered by this audit.

This report is **independent verification of two narrow original subroutines**, not proof that the entire arcade collision engine or commercial game has been recovered.
