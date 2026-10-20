#!/usr/bin/env python3
"""Map Indy Heat arcade's original Intel 80186 audio ROM and external DAC data.

Source is a locally supplied 1991 arcade ROM zip. No proprietary ROM/sound
assets are checked into the repository. This recovers the machine's sound ROM
layout and reset vector, NOT the complete synthesiser/sound game logic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

CHIPS = {
    "e-302-33021-01.u3": ("64caa14e05dd9ec43ce13f5c738df1f39f5fa75c", 0x20000),
    "e-302-33024-01.u6": ("52f66e1ccde0ef3fb7959a207cc967237e37833e", 0x20000),
    "e-302-33022-01.u4": ("0174f5372117d15bf0ecd48b72c9cca4cf8bb75f", 0x20000),
    "e-302-33023-01.u5": ("8f6b3cba2bc729f2e0623578b13720ead91333e4", 0x20000),
    "e-302-33025-01.u8": ("0ea814db7f647f39d11dcde793a17831fca3bddd", 0x20000),
    "e-302-33026-01.u9": ("2ff0f45f17b8a182afdaa5603e7a1af70e6336b7", 0x20000),
    "eeprom-indyheat.bin": ("bd1f116c2650576da73a7f80e9677a9f3fefb390", 0x100),
}
# Note: EEPROM SHA1 cross-check against original MAME manifest is intentional.
AUDIO_INTERLEAVES = {
    "e-302-33021-01.u3": 0x20001,  # odd byte
    "e-302-33024-01.u6": 0x20000,  # even byte
    "e-302-33022-01.u4": 0x60001,
    "e-302-33023-01.u5": 0x60000,
}


def read_audio_chips(archive: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(archive) as z:
        members = {Path(m.filename).name.lower(): m for m in z.infolist()}
        chips = {}
        for name, (expected_sha, expected_size) in CHIPS.items():
            if name not in members:
                raise ValueError(f"Arcade ROM member missing: {name}")
            data = z.read(members[name])
            if len(data) != expected_size or hashlib.sha1(data).hexdigest() != expected_sha:
                raise ValueError(f"Original arcade ROM integrity mismatch: {name}")
            chips[name] = data
        return chips


def restore_audio_image(chips: dict[str, bytes]) -> bytes:
    image = bytearray(0x100000)
    for name, offset in AUDIO_INTERLEAVES.items():
        data = chips[name]
        image[offset:offset + 2 * len(data):2] = data
        if name.endswith((".u4", ".u5")):
            mirror = offset + 0x60000
            image[mirror:mirror + 2 * len(data):2] = data
    return bytes(image)


def restore_dac_region(chips: dict[str, bytes]) -> bytes:
    return chips["e-302-33025-01.u8"] + chips["e-302-33026-01.u9"]


def analyse(archive: Path, output_dir: Path, export_binary: bool = False) -> dict:
    chips = read_audio_chips(archive)
    sound = restore_audio_image(chips)
    dac = restore_dac_region(chips)
    # Original 80186 reset vector FFFF0 is a FAR JMP, CS:IP FF D8:0000.
    vector = sound[0xffff0:0xffff5]
    if vector[0] != 0xea:
        raise ValueError("Original 80186 reset vector does not begin with far JMP")
    offset, segment = int.from_bytes(vector[1:3], "little"), int.from_bytes(vector[3:5], "little")
    entry = ((segment << 4) + offset) & 0xfffff
    result = {
        "machine": "Indy Heat 1991 arcade rev1 Intel 80186 sound",
        "sound_cpu_region": {
            "bytes": len(sound), "sha256": hashlib.sha256(sound).hexdigest(),
            "reset_far_jump": {"segment": f"{segment:04X}", "offset": f"{offset:04X}",
                               "physical_entry": f"{entry:05X}"},
            "interleave": "u3/u6 at 20000 odd/even, u4/u5 at 60000 odd/even",
            "reload": "u4/u5 mirrored to C0000-FFFFF",
        },
        "external_clocked_dac": {
            "bytes": len(dac), "sha256": hashlib.sha256(dac).hexdigest(),
            "region": "u8 offset 00000; u9 offset 20000"
        },
        "eeprom": {
            "bytes": len(chips["eeprom-indyheat.bin"]),
            "sha256": hashlib.sha256(chips["eeprom-indyheat.bin"]).hexdigest(),
        },
        "scope": "Hardware layout and 80186 entry verified; sound functions and music NOT decompiled",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "audio_rom_inventory.json").write_text(json.dumps(result, indent=2) + "\n")
    if export_binary:
        (output_dir / "audio80186_private.bin").write_bytes(sound)
        (output_dir / "dac_private.bin").write_bytes(dac)
        (output_dir / "eeprom_private.bin").write_bytes(chips["eeprom-indyheat.bin"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arcade_rom_zip", type=Path, help="Private, user-supplied indyheat.zip")
    parser.add_argument("--out", type=Path, default=Path("local/audio-recovery"))
    parser.add_argument("--export-private-binaries", action="store_true")
    args = parser.parse_args()
    print(json.dumps(analyse(args.arcade_rom_zip, args.out,
                             args.export_private_binaries), indent=2))


if __name__ == "__main__":
    main()
