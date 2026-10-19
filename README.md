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

## Development rule

**Never label approximated physics as arcade-faithful.** Any mechanic must have a recorded reference observation or be marked `UNVERIFIED`. Avoid replacing game rules with third-party template physics. Prioritise recovery and faithful porting of verified arcade routines into a native Godot mechanics library; no ROM binaries or extracted proprietary code are committed. Assess reuse rights separately before any commercial release.

See [the ROM decompile/recompile workstream](docs/ARCADE_BINARY_PORT_PLAN.md) and the [private ROM preparation utility](tools/prepare_indyheat_rom.py).

## Project structure

- `project.godot` — Godot 4 project
- `scenes/` — screen and game scenes
- `scripts/camera/` — portrait pan tracking
- `scripts/data/` — circuit resources and race information
- `scripts/mechanics/` — independently implemented, arcade-verified mechanics
- `docs/` — acceptance register and verification notes

## Current status

Repository initialized; a ROM layout verifier and bank-image preparation script are in a draft PR. No arcade game program binaries were provided or decompiled; no original game mechanics or APK are yet built.

## Legal / assets

Original ROMs, extracted code, artwork, music and game branding must not be committed to this public repository. Rebuilding mechanics with new visual assets helps establish an original product, but legal clearance of an unusually close commercial reproduction remains a separate release checkpoint.
