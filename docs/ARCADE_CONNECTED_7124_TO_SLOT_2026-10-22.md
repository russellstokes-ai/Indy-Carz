# Indy Carz — Connected original driving prefix and test-runner audit

**22 October 2026.** Source baseline: PR #2, `ed7fab2477c37dac50592eccb5d658025873a39a`.
Original ROM, original game assets and owner-only MAME memory captures remain outside this public repository.

## Newly connected verified stages

The Godot port now provides `ArcadeVerifiedVehiclePhysicsPrefix.run_verified_original_slot_from_7124`, connecting existing, individually original-Z80-verified computations without adding estimated car physics:

1. Original `61CE` 48-word load of the selected physical 256-byte car slot into shared `E72B` scratch, retaining the remaining 160 bytes in the physical record.
2. Original `7124–714D` signed heading projection into `E933`, including its actual outgoing Z80 carry.
3. Original `714E–71C7` carry-sensitive `B/C` table selection, from an externally supplied authenticated 257-byte window. The caller supplies real incoming `B/C`, not a fabricated default.
4. Normal route: existing independently recovered `71C8–752F` drive, angular and steering stages. Bounded nonlocal `1689` exits fail closed.
5. **Original bypass route:** `714E -> 7315` skips all `71C8–7314` acceleration/angular calculations, but executes the verified `7315–752F` steering suffix. It must not be mistaken for a completed early return from the car update.
6. Both legitimate routes continue through `7530–7571` integer position integration, then `7572–75F0` eight-point collision geometry, returning at `75F1`.
7. The original `629A` reverse 48-word scratch storeback runs **only** after that genuine `75F1` return. The caller's original master RAM remains unmodified.

The standalone `advance_from_original_7315` helper is independently exercised against the previously connected `71C8->7315->7530` suffix for both `7315` branch families and all five racing-slot pointers. Per-slot integration tests also exercise carry=1 normal selection versus carry=0 original bypass and verify the resulting 96-byte save-back.

All 257-byte/256-byte tables and test state in public Godot tests are **synthetic**; they prove composition and branch preservation, not whole-game parity against real arcade execution. The underlying isolated math stages had prior owner-ROM opcode verification; this new orchestration still needs a separately collected full in-game MAME frame/state trace.

## Test infrastructure defect repaired

The old `ArcadeVerifiedMotionChain.gd` preload alias `Control` collided with Godot's native `Control` class. A direct local Godot 4.4.1 run proved that it caused script compilation errors, while the old smoke-test invocation could still exit with code zero.

The headless suite also ran inside `SceneTree._initialize`, before `root` entered the live tree. It consequently emitted hundreds of viewport errors in camera tests despite printing a success marker. The runner now starts deferred after the scene tree is ready and verifies that condition.

`tools/check_godot_test_output.py` and its ROM-free unit tests now reject a nonzero exit status, any `ERROR`/`SCRIPT ERROR`/`WARNING` lines, or a missing/zero/duplicate explicit success marker. The GitHub Godot workflow captures stderr and validates this transcript rather than trusting process exit alone.

## Explicitly still open

- Proven original *runtime* sources and changes for `B/C`, E96B/E96D table windows, ROM drive factors and time/frame cadence across complete car callbacks.
- Full original `601E` and subsequent CPU event/physics scheduling, terrain/road responses and all-car collision outcomes beyond these bounded routines.
- AI route decisions, pit services, fuel, turbo, upgrades, original sound, full race UI/economy and original 14 dynamic QRAM trackmaps.
- Original-running-arcade, end-to-end input-to-per-car-output parity over race frames and complete Android product/game QA.

**Commercial Gate A remains OPEN.** This is a tested arithmetic/geometry integration advance, not a playable game, finished original-engine decompile or permission to substitute approximate rules.
