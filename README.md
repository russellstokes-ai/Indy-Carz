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

See [docs/ARCADE_FIDELITY_SPEC.md](docs/ARCADE_FIDELITY_SPEC.md) for the baseline and [docs/REFERENCE_CAPTURE_CHECKLIST.md](docs/REFERENCE_CAPTURE_CHECKLIST.md) for the evidence and extraction process.

## Project structure

- `project.godot` — Godot 4 project
- `scenes/` — screen and game scenes
- `scripts/camera/` — portrait pan tracking
- `scripts/data/` — circuit resources and race information
- `scripts/mechanics/` — independently implemented, arcade-verified mechanics
- `docs/` — acceptance register and verification notes

## Current status

**Arcade ROM and original subroutine recovery underway.** The actual 1991 arcade ROM was provided and checksum-verified locally; its master/slave Z80 and X-ROM memory regions were reconstructed privately. Recoverable original input mechanisms now exist in Godot 4.4: steering dial+response curve, steering accumulators, pedal fixed-point response, and two X-ROM drive-byte stages. These were validated against original Z80 instructions or the X-ROM tables and have ROM-free regression tests. A noninvasive portrait camera is present, with Godot engine-level headless tests.

**Not playable yet.** The downstream car-motion/traction, collisions, AI, pit/fuel/upgrade systems and per-race circuit geometry remain to be recovered and implemented. Debugger-enabled MAME traces and QRAM track snapshots have not been collected. Do not claim arcade gameplay parity on the basis of isolated verified arithmetic stages. See [mechanics evidence](docs/ARCADE_MECHANICS_RECOVERY_2026-10-19.md), [actual ROM inspection](docs/ROM_INSPECTION_2026-10-19.md) and [recovery workflow](docs/ARCADE_DECOMPILATION_WORKFLOW.md).

## Legal / assets

Original ROMs, extracted code, artwork, music and game branding must not be committed to this public repository. Rebuilding mechanics with new visual assets helps establish an original product, but legal clearance of an unusually close commercial reproduction remains a separate release checkpoint.
