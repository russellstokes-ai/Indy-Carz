"""Synthetic structural tests: proprietary Indy Heat ROM never enters GitHub."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_callback_recovery import (
    BANK3, check, mapped, inspect, inspect_initializers,
    inspect_passes, inspect_continuations,
)


def synthetic_master():
    mem = bytearray(0x90000)
    mem[0x18C0] = 0xE9
    mem[0x2D65:0x2D70] = bytes.fromhex("3a 7d e6 b7 28 1c fe 02 ca 0e 2e")
    mem[0x611D:0x6126] = bytes.fromhex("21 af 2e dd 74 15 dd 75 14")
    mem[0x6126:0x612F] = bytes.fromhex("21 1e 2f dd 74 17 dd 75 16")
    for first, offset in ((0x2D87, 0x94), (0x2E0E, 0x96)):
        for slot in range(6):
            base = 0xE000+slot*0x100
            ix = base+0x80
            ptr = base+offset
            pc = first+slot*22
            mem[pc:pc+22] = bytes([
                0x21, base&255, base>>8,
                0xCD,0xCE,0x61,
                0xDD,0x21,ix&255,ix>>8,
                0x2A,ptr&255,ptr>>8,
                0xCD,0xC0,0x18,
                0x21,(base+0x60)&255,(base+0x60)>>8,
                0xCD,0x9A,0x62,
            ])
    def put_bank3(pc, data):
        pos = BANK3 + pc-0x2000
        mem[pos:pos+len(data)] = data
    put_bank3(0x77BE, bytes.fromhex("e1 dd 74 15 dd 75 14 c9"))
    for pc in (0x756B, 0x7594):
        put_bank3(pc, bytes.fromhex("dd 36 15 74 dd 36 14 c9"))
    # Distinct artificial locations; explicitly candidates only.
    for pc in range(0x2300, 0x2300+34*4, 4):
        put_bank3(pc, bytes.fromhex("cd be 77"))
    return bytes(mem)


class CallbackRecoveryTests(unittest.TestCase):
    def test_independent_default_callbacks(self):
        mem = mapped(synthetic_master(), 0x02000)
        info = inspect_initializers(mem)
        self.assertEqual(info["first_default_callback"], "2EAF")
        self.assertEqual(info["second_default_callback"], "2F1E")

    def test_original_six_slot_callbacks(self):
        memory = mapped(synthetic_master(), 0x02000)
        rows = inspect_passes(memory)
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["pointer_ram"], "E094")
        self.assertEqual(rows[5]["pointer_ram"], "E594")
        self.assertEqual(rows[6]["pointer_ram"], "E096")
        self.assertEqual(rows[11]["pointer_ram"], "E596")

    def test_34_yield_sites_and_two_overrides(self):
        bank3 = mapped(synthetic_master(), BANK3)
        report = inspect_continuations(bank3)
        self.assertEqual(report["site_count"], 34)
        self.assertEqual(report["signature_matched_yield_sites"][0]["saved_continuation_pc"], "2303")
        self.assertEqual(len(report["explicit_callback_redirects"]), 2)
        self.assertTrue(all(x["forced_callback_target"] == "74C9" for x in report["explicit_callback_redirects"]))

    def test_fail_on_corrupted_continuation_trampoline(self):
        mem = bytearray(mapped(synthetic_master(), BANK3))
        mem[0x77BE] = 0
        with self.assertRaisesRegex(ValueError, "77BE"):
            inspect_continuations(bytes(mem))

    def test_wrong_rom_rejected(self):
        with self.assertRaisesRegex(ValueError, "Original verified"):
            inspect(synthetic_master())


if __name__ == "__main__":
    unittest.main()
