"""ROM-free independent MAME Ataxx/Indy Heat bank/view mapping tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_master_bank_map import (BANK_BASES, MASTER_SIZE, bank_base,
    mapped_rom_offset, event_source_window, banked_write_target)


def original_unrotated_image():
    return bytearray(((i * 29 + (i >> 7) * 11 + (i >> 15) * 67) ^ (i >> 3)) & 255
                     for i in range(MASTER_SIZE))


def independent_mame_rotate(region):
    out = bytearray(region)
    for base in range(0x10000, MASTER_SIZE, 0x8000):
        block = region[base:base + 0x8000]
        out[base:base + 0x8000] = block[0x2000:] + block[:0x2000]
    return out


class OriginalMasterBankMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = original_unrotated_image()
        cls.rotated = independent_mame_rotate(cls.raw)

    def test_all_sixteen_original_banks_and_high_control_bits(self):
        self.assertEqual(len(BANK_BASES), 16)
        for control in range(256):
            bank = control & 15
            base = 0x2000 if bank == 0 else 0x10000 + bank * 0x8000
            self.assertEqual(bank_base(control), base)
            for addr in (0x2000, 0x3F00, 0x3FFF, 0x4000, 0x40FF, 0x9FFF):
                logical_offset = addr - 0x2000
                physical = (base + logical_offset if bank == 0 else
                            base + ((logical_offset + 0x2000) % 0x8000))
                self.assertEqual(self.rotated[mapped_rom_offset(addr, control)],
                                 self.raw[physical])

    def test_full_event_window_all_banks_matches_independent_raw_mapping(self):
        for control in range(256):
            bank = control & 15
            base = 0x2000 if bank == 0 else 0x10000 + bank * 0x8000
            expected = bytes(self.raw[base + addr - 0x2000] if bank == 0 else
                             self.raw[base + ((addr - 0x2000 + 0x2000) % 0x8000)]
                             for addr in range(0x3F00, 0x4100))
            self.assertEqual(event_source_window(self.rotated, control), expected)
            self.assertEqual(len(expected), 512)

    def test_all_four_event_groups_use_correct_active_bank_bytes(self):
        from arcade_event_2ad6_staging import independent, IXS, SOURCE_OFFSETS
        for control in range(256):
            source = event_source_window(self.rotated, control)
            for value in (0, 11, 12, 35, 36, 59, 60, 255):
                ix = IXS[control % 5]
                ram = bytearray(0x2000)
                ram[ix + 0x3A - 0xE000] = value
                result = independent(ram, ix, source)
                group = 0 if value < 12 else 1 if value < 36 else 2 if value < 60 else 3
                addr = SOURCE_OFFSETS[group] + value
                self.assertEqual(result["next_pc"], 0x2B77)
                self.assertEqual(result["ram"][0x900 + 2 * group], source[addr - 0x3F00])
                self.assertEqual(result["ram"][0x901 + 2 * group], source[addr + 25 - 0x3F00])

    def test_qram_and_battery_views_all_four_qram_planes(self):
        for low in range(16):
            for high in (0x00, 0x40, 0x80, 0xC0):
                for addr in (0xA000, 0xB234, 0xDFFF):
                    offset = addr - 0xA000
                    self.assertEqual(banked_write_target(addr, high | 0x20 | low),
                                     ("qram", ((high & 0xC0) << 8) | offset))
                    self.assertEqual(banked_write_target(addr, high | 0x10 | low),
                                     ("battery_ram", offset))
                    self.assertEqual(banked_write_target(addr, high | low),
                                     ("rom_write_ignored", None))
                    self.assertEqual(banked_write_target(addr, high | 0x30 | low),
                                     ("rom_write_ignored", None))

    def test_fail_closed_without_full_region_or_observed_f4(self):
        for bad in (-1, 256, None, True, 1.5, "3"):
            with self.assertRaises(ValueError):
                bank_base(bad)
            with self.assertRaises(ValueError):
                event_source_window(self.rotated, bad)
        for size in (0, MASTER_SIZE - 1, MASTER_SIZE + 1):
            with self.assertRaises(ValueError):
                event_source_window(bytes(size), 0)
        for addr in (0, 0x1FFF, 0xA000, 0x10000, True):
            with self.assertRaises(ValueError):
                mapped_rom_offset(addr, 0)
        for addr in (0x9FFF, 0xE000, 0xFFFF, -1):
            with self.assertRaises(ValueError):
                banked_write_target(addr, 0)


if __name__ == "__main__":
    unittest.main()
