"""ROM-free callback routing regressions; private original opcode parity."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_callback_2eaf_prefix import independent as first_callback, IXS
from arcade_callback_3006_dispatch import independent as dispatch, HANDLERS


class CallbackDispatchTests(unittest.TestCase):
    def test_first_callback_real_exit_and_exact_mutations_all_slots(self):
        for ix in IXS:
            ram = bytearray(8192)
            for off in (0x7E, 0x1E, 0x10, 0x56):
                ram[ix + off - 0xE000] = 0xFF
            before = bytes(ram)
            result = first_callback(ram, ix)
            out = result["ram"]
            self.assertEqual((result["next_pc"], result["branch"], result["complete"]),
                             (0x85B4, "call_85b4", False))
            self.assertEqual([out[ix + off - 0xE000] for off in (0x7E, 0x1E, 0x10, 0x56)],
                             [0xFD, 0xFE, 0, 0xFF])
            self.assertEqual(bytes(ram), before)

    def test_disabled_first_callback_preserves_ram_and_returns(self):
        for ix in IXS:
            ram = bytearray([0xA5] * 8192)
            ram[ix + 0x33 - 0xE000] |= 2
            self.assertEqual(first_callback(ram, ix)["ram"], bytes(ram))
            self.assertTrue(first_callback(ram, ix)["return_to_caller"])
            self.assertEqual(first_callback(ram, ix)["next_pc"], 0x2EB3)

    def test_each_status_bit_selects_the_actual_original_call(self):
        for ix in IXS:
            for site, off, bit, target in HANDLERS:
                ram = bytearray(8192)
                ram[ix + off - 0xE000] |= (1 << bit)
                self.assertEqual((dispatch(ram, ix)["call_site_pc"],
                                  dispatch(ram, ix)["next_pc"]), (site, target))

    def test_all_512_flag_masks_preserve_original_first_call_priority(self):
        for ix in IXS:
            for mask in range(512):
                ram = bytearray(8192)
                for index, (_, off, bit, _) in enumerate(HANDLERS):
                    if (mask >> index) & 1:
                        ram[ix + off - 0xE000] |= (1 << bit)
                for aggregate in (0, 0x10, 0x20, 0x30):
                    ram[ix + 0x34 - 0xE000] = aggregate
                    result = dispatch(ram, ix)
                    expected = next(((site, target) for index, (site, _, _, target)
                                     in enumerate(HANDLERS) if (mask >> index) & 1),
                                    (0x304A, 0x113B) if aggregate else (0x304D, 0x689D))
                    self.assertEqual((result["call_site_pc"], result["next_pc"]), expected)

    def test_bad_ram_or_unknown_slot_rejected(self):
        for fn in (first_callback, dispatch):
            with self.assertRaises(ValueError):
                fn(bytes(8191), IXS[0])
            with self.assertRaises(ValueError):
                fn(bytes(8192), 0xE680)


if __name__ == "__main__":
    unittest.main()
