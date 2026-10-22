# Indy-Carz

A Godot 4 mobile-first overhead arcade racer inspired by the **1991 Indy Heat arcade experience**, with an original visual identity.

## Locked product direction

- **Platform:** Android portrait-first; adaptable landscape and tablet presentation.
- **Gameplay reference:** the original *arcade* release, **not** NES, Amiga or other ports.
- **Track design:** reconstruct the arcade circuit layouts, corner shapes, width proportions and pit-lane placement with only specifically justified, approved minor adjustments. **Do not rotate, squeeze, procedurally redesign or replace circuits merely to fit the phone.**
- **Mobile camera:** gentle, speed-aware **panning** of the unmodified track. Keep the player inside a comfortable view zone; minimize motion sickness and jitter. Provide off-screen car direction hints.
- **Mechanics:** preserve original steering, accelerator and turbo behaviour, collisions, car damage, fuel usage, repairs, servicing, upgrades, opponents, lap scoring and championship systems. These are *verification targets*, not guessed constants.
- **Visuals and brand:** entirely original car/track/scenery art, audio, text, names, logos, teams and sponsor identities. More polished graphics without changing gameplay.
- **Performance:** deterministic fixed-step simulation independent of display frame rate, 60 fps rendering target, support narrow and foldable Android displays.

## Commercial-release gate (approved)

**Do not begin Godot gameplay or make a concept/demo/prototype build until the original arcade game engine has been recovered and its mechanics verified.** The sole target is a complete, production-grade commercial Android game. See [commercial release gate](docs/COMMERCIAL_RELEASE_GATE.md) for compulsory extraction, implementation and QA acceptance criteria.

## Development rule

**Never label approximated physics as arcade-faithful.** Any mechanic must have a recorded reference observation or be marked `UNVERIFIED`. Avoid replacing game rules with third-party template physics. A clean-room implementation is preferred to committing original ROM binaries or proprietary source/assets.

See the [entire-game extraction register](docs/ENGINE_EXTRACTION_REGISTER_2026-10-20.md), the [recovered callback/track/championship evidence](docs/ARCADE_ENGINE_EXTRACTION_CALLBACKS_TRACKS_2026-10-20.md), the [original collision prefilter and separation maths](docs/ARCADE_COLLISION_PREFILTER_2026-10-20.md), the [original mechanics evidence](docs/ARCADE_MECHANICS_RECOVERY_2026-10-19.md), and the [decompilation workflow](docs/ARCADE_DECOMPILATION_WORKFLOW.md).

## Project structure

- `project.godot` — Godot 4 project
- `scenes/` — screen and game scenes
- `scripts/camera/` — portrait pan tracking
- `scripts/data/` — circuit resources and race information
- `scripts/mechanics/` — independently implemented, arcade-verified mechanics
- `docs/` — acceptance register and verification notes

## Current status

**Arcade ROM and original subroutine recovery underway.** The provided original 1991 ROM was checksum-verified locally; master/slave Z80 and X-ROM regions were reconstructed privately. Independently original-opcode-verified steering, drive, movement geometry, collision and race-control stages have been connected incrementally in Godot 4.4. Selected original-running-MAME traces have verified bounded stages, but the entire original race frame/physics engine has not been recovered. A noninvasive portrait camera is present, with Godot headless regressions.

**Latest connected driving milestone:** authentically recovered original `709C–7123` speed update and linked it to six-slot scratch transfer, `7124` heading/carry, `714E` B/C selection, the normal `71C8` route or original `7315` bypass, `7530` position/footprint and conditional 48-word storeback at `75F1`. Original table contents and all upstream controls remain authenticated caller inputs, never guessed. The private original master program was reconstructed from the owner's saved listings and verified by its exact original SHA-256. Independent arithmetic vs original Z80 executed **100,000 cases with zero mismatches** for the new speed stage. See [709C speed recovery](docs/ARCADE_DRIVING_709C_SPEED_2026-10-22.md) and [7124 connection/CI audit](docs/ARCADE_CONNECTED_7124_TO_SLOT_2026-10-22.md).

**Further original entry recovery:** `7017` connects the genuine `75F2` eleven-word geometry checkpoint to the independently recovered `701A–7048` per-car control gate. Both the normal `7036` and slow `7049` branches now feed the verified `709C→75F1` pipeline when the original code reaches it. The `7049` branch stops safely instead where the original calls external `7E5E` or `2AD1`. The original gate and additional slow branch each independently matched **100,000 original-Z80 cases with zero discrepancies**. See [7017 driving control recovery](docs/ARCADE_DRIVING_7017_GATE_2026-10-22.md) and [7049/7D65 recovery](docs/ARCADE_DRIVING_7049_7D65_RECOVERY_2026-10-22.md).

**Original special positioning:** both outcomes of `7D4C` are now independently recovered. Bit 1 set copies original car Y/X directly; bit 1 clear enters the fully recovered `7D65–7E35` fixed-point smoothing of centres, heading and speed. Both return to original `7024→7572→75F1` geometry-only continuation without normal `709C/7530` motion; each original special-stage verifier matched **100,000 original-Z80 cases with zero discrepancies**. See [7D4C direct-position recovery](docs/ARCADE_DRIVING_7D4C_DIRECT_2026-10-22.md) and [7049/7D65 recovery](docs/ARCADE_DRIVING_7049_7D65_RECOVERY_2026-10-22.md).

**Further original slow-branch continuation:** the conditional `708E CALL 7E5E` now has four authentically recovered early returns. Those may continue to `7091→709C` after the original `IX-03` gate, while the unknown event-dispatch branch stops exactly at `7EA3`. An additional **100,000 original-Z80 comparisons, zero mismatches** cover the bounded gate. See [7E5E early-return verification](docs/ARCADE_DRIVING_7E5E_EARLY_RETURNS_2026-10-22.md).
**Original event gate at 2AD1:** its authentic five-byte bit-0 early return is recovered and linked to `709B POP BC→709C`; bit-0-clear cars stop before original `2AD6` bank switching/event processing. **100,000 additional Z80 comparisons** matched zero discrepancies. See [2AD1 early-return proof](docs/ARCADE_DRIVING_2AD1_EARLY_RETURN_2026-10-22.md).

**Not playable yet.** Complete original per-frame scheduling, all driving/terrain/contact behaviour, full AI, pits/fuel/turbo/upgrades, original full QRAM trackmaps and commercial presentation still require recovery and validation. The existing original-RAM maths and synthetic integration tests are **not** whole-game parity. See [mechanics evidence](docs/ARCADE_MECHANICS_RECOVERY_2026-10-19.md), [original ROM inspection](docs/ROM_INSPECTION_2026-10-19.md) and [recovery workflow](docs/ARCADE_DECOMPILATION_WORKFLOW.md).

## Current extraction gate\n\n**Gate A remains OPEN.** Banked master/slave CPU static control-flow surveys, original X-ROM mathematics, original per-car initialisation, part of AI pedal mapping and Intel 80186 audio mapping have been recovered. Default callback entries (2EAF/2F1E), a bank-3 coroutine continuation helper, all fourteen original starting grids (70 positions), the fifteen-race circuit sequence, and fourteen per-course spatial event bounds are now recovered. Complete vehicle dynamics, collision, turbo, fuel, AI decision-making, original runtime trackmaps and the event semantics of the spatial zones remain unresolved. No concept game, provisional physics or additional Godot gameplay changes are authorised until engine recovery is sufficiently verified.\n\n## Legal / assets

Original ROMs, extracted code, artwork, music and game branding must not be committed to this public repository. Rebuilding mechanics with new visual assets helps establish an original product, but legal clearance of an unusually close commercial reproduction remains a separate release checkpoint.
