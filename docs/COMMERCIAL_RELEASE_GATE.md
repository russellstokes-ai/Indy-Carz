# Indy Carz — Full commercial release baseline

**Approved 20 October 2026.** This is a commercial production project, not a conceptual demonstration, simplified homage, physics approximation, playable prototype, vertical slice or early test APK.

## Non-negotiable sequencing

**Gate A — Recover the original arcade engine, before starting Godot gameplay implementation.**

- Use the uploaded, verified 1991 *Danny Sullivan's Indy Heat* arcade ROM as the reference source; explicitly exclude home conversions.
- Reconstruct the banked Z80 execution context and gameplay data correctly.
- Identify actual original program routines, tables, constants and event order for steering, throttle, coasting/braking, collisions, damage, turbo, fuel, pit entry/services, AI, overtaking, upgrades, economy, race positions, lap counting, result screens and championship rules.
- Recover track geometry and game-related collision/lap/pit data, distinguishing background graphics from gameplay geometry.
- Validate each recovered system against controlled MAME runs and traces. Every system gets a proven source mapping and repeatable expected outputs; do not label heuristics as authentic.
- Deliver an **engine extraction dossier**: memory/bank address map, game update/event sequence, numerical rule tables, circuit definitions, tested scenarios, and an explicit unresolved-items register.
- Block Godot racing-code implementation until each gameplay-critical subsystem has been captured sufficiently to reproduce it and its acceptance tests are defined. Do not build a guessed placeholder engine.

**Gate B — Implement the production game in Godot 4.**

- Single definitive production architecture; no separate throwaway proof-of-concept or demo build.
- Independently implement the recovered arcade behaviour in new maintainable Godot code.
- Preserve original arcade mechanics and their relative timing/pace, original 14 track layouts and 15-race progression; minor track edits require approval and must not compensate for phone aspect ratio.
- Portrait-first Android uses gentle bounded camera panning over unchanged geometry; support narrower and foldable displays with controls outside the racing action.
- Replace the original graphics, identities, teams, audio and branding with original commercial-quality art and sound. Do not incorporate proprietary ROMs or original code/assets in distributables or the public repository.

**Gate C — Full commercial release acceptance, not a demo.**

- Entire circuit set and race programme; complete computer opposition; full pit/refuel/repair/upgrade economy, AI and collision behaviour; original game scoring progression.
- Final consistent HD pixel-art cars and racing environments, animations, menus, HUD, VFX, sound, music and branding.
- Complete touch controls, screen rotation/aspect support, foldable layout, device pause/resume, accessibility basics and robust save/recovery.
- Performance target: stable 60 fps on defined supported Android devices, deterministic fixed-step racing logic and no material hitches during panning or effects.
- Automated regression tests and human device QA against the original mechanics, long-running championship sessions, power-state changes, crash recovery, memory use and clean install/update paths.
- Android signing, package IDs, Play policy compliance, privacy/data review, licensing/IP risk review and release assets.
- Nothing labelled **commercial release ready** until feature parity, performance, artwork, QA and release checks are complete. Any incomplete subsystem remains explicitly OPEN.

## Current real status

- Uploaded arcade ROM verified. Master/slave/X-ROM regions reconstructed. Static graphics tile format and QRAM tilemap addressing understood.
- Extraction tools and synthetic tests are in draft PR #2.
- No verified original steering/physics/AI/pit/circuit gameplay algorithms are yet recovered or ported.
- Debugger-enabled arcade execution and event tracing remains necessary; pure static disassembly alone cannot establish gameplay parity.
- Therefore **Gate A is OPEN**. Godot gameplay and visual-production development must not begin yet.

## Operating rules

- Prioritise irreversible foundation correctness over mock-ups, estimates, and premature visuals.
- Never change approved original-game mechanics, circuit geometry or user-approved camera baseline without an explicit decision.
- No unapproved speed reduction (earlier reference to 5% slowdown was incorrect).
- Maintain one verified status/acceptance register. Distinguish executed/tested recovery from tools that are merely written.
- Track commercial rights separately: new brand/art reduces some risks but does not automatically eliminate all IP concerns for a very close recreation.
