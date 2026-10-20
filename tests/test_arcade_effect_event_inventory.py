"""Synthetic-only original event/effect/sound memory layout tests."""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import arcade_effect_event_inventory as effects

FLAGS = [
    (0x32,5,0x6C1C), (0x32,3,0x6DFA), (0x32,4,0x6E06),
    (0x31,5,0x6EA6), (0x7E,2,0x6A18), (0x31,4,0x6A3A),
    (0x32,6,0x6B61), (0x32,7,0x6BA2), (0x33,3,0x6A51),
]


def synthetic_rom() -> bytes:
    m = bytearray(0x90000)
    def put(pc: int, raw: str) -> None:
        b = bytes.fromhex(raw)
        m[pc:pc+len(b)] = b
    for i, (offset, bit, target) in enumerate(FLAGS):
        pc = 0x3006 + 7*i
        m[pc:pc+7] = bytes((0xDD, 0xCB, offset, 0x46 + bit*8,
                              0xC4, target & 255, target >> 8))
    put(0x3045, "DD 7E 34 E6 30 C4 3B 11")
    put(0x304D, "CD 9D 68")
    put(0x8659, "21 00 E8 0E 10")
    put(0x8689, "F6 FF C9")
    put(0x8694, "21 00 E8 7E FE 02 30 11")
    put(0x86AD, "20 28")
    put(0x86E7, "CD C0 18")
    put(0x8700, "FD 36 00 00")
    put(0x6E03, "C3 0F 6E")
    put(0x6E0F, "F5")
    put(0x6BA2, "26 E8 DD 6E 30 E5 FD E1")
    put(0x0BBC, "D3 F4 CD 00 20")
    put(0x0BC2, "32 08 E6 D3 F4")
    b3_offset = 0x28000
    for addr, raw in ((0x2000, "F5 D5 E5 78"),
                      (0x20B7, "79 D3 05"),
                      (0x20BF, "E6 7F B3 D3 06")):
        b = bytes.fromhex(raw)
        begin = b3_offset + addr - 0x2000
        m[begin:begin+len(b)] = b
    for sites in effects.EFFECT_PATHS.values():
        for pc in sites:
            put(pc, "CD 59 86")
    for calls in effects.SOUND_PATHS.values():
        for pc, dest in calls:
            put(pc, "CD " + dest[2:] + " " + dest[:2])
    return bytes(m)


def invent_with_synthetic(m: bytes) -> dict:
    with patch.object(effects, "MASTER_SHA", hashlib.sha256(m).hexdigest()), \
         patch.object(effects, "ALLOCATOR_SHA", hashlib.sha256(m[0x8659:0x8694]).hexdigest()), \
         patch.object(effects, "UPDATE_SHA", hashlib.sha256(m[0x8694:0x86F5]).hexdigest()), \
         patch.object(effects, "SOUND_GATE_SHA", hashlib.sha256(m[0x0B98:0x0BC9]).hexdigest()):
        return effects.inventory(m)


class OriginalEffectInventoryTests(unittest.TestCase):
    def test_all_nine_and_exact_allocator_sites(self):
        report = invent_with_synthetic(synthetic_rom())
        self.assertEqual(len(report["events"]), 9)
        self.assertEqual(report["allocating_handlers"], 8)
        self.assertEqual(report["existing_record_handlers"], 1)
        self.assertEqual(report["distinct_allocator_call_sites"], 8)
        self.assertEqual(report["pool"]["number_of_records"], 16)
        self.assertEqual(report["pool"]["effect_record_size"], 16)
        self.assertEqual(report["pool"]["animation_callback_address"], "+02/+03 for status>=3")
        self.assertEqual(report["events"][7]["handler_pc"], "6BA2")
        self.assertEqual(report["events"][7]["original_allocator_calls"], [])

    def test_three_direct_audio_gateway_paths(self):
        report = invent_with_synthetic(synthetic_rom())
        relevant = [x for x in report["events"] if x["direct_audio_command_calls"]]
        self.assertEqual([x["handler_pc"] for x in relevant],
                         ["6C1C", "6EA6", "6A51"])
        self.assertEqual(report["audio"]["bank3_80186_ports"],
                         ["05 command_hi", "06 command_lo"])

    def test_fail_closed_on_sound_handshake_corruption(self):
        m = bytearray(synthetic_rom())
        m[0x28000 + 0x20B8 - 0x2000] = 0
        with self.assertRaisesRegex(ValueError, "bank3 20B7"):
            invent_with_synthetic(bytes(m))

    def test_original_rom_integrity_enforced(self):
        with self.assertRaisesRegex(ValueError, "Verified original"):
            effects.inventory(synthetic_rom())


if __name__ == "__main__":
    unittest.main()
