"""ROM-free tests of exact original 2AD6–2B76 eight-byte event staging."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_event_2ad6_staging import independent, IXS, SOURCE_OFFSETS, MISSING_SOURCE_PC


class Original2AD6StagingTests(unittest.TestCase):
    def seed(self, ix, value):
        ram = bytearray(0x2000)
        ram[ix + 0x3A - 0xE000] = value
        ram[0x900:0x908] = bytes([0xA5] * 8)
        return ram

    def test_every_byte_value_selects_correct_group_and_source(self):
        source = bytes((i * 37 + 17) & 255 for i in range(512))
        for ix in IXS:
            for value in range(256):
                ram = self.seed(ix, value)
                before = bytes(ram)
                result = independent(ram, ix, source)
                group = 0 if value < 12 else 1 if value < 36 else 2 if value < 60 else 3
                addr = SOURCE_OFFSETS[group] + value
                self.assertEqual((result["group"], result["source_addr"], result["next_pc"]),
                                 (group, addr, 0x2B77))
                self.assertEqual(result["stack_word"], 0x0108)
                self.assertEqual(bytes(ram), before)
                for word in range(4):
                    if word < group:
                        expected = [0x13, 0]
                    elif word == group:
                        expected = [source[addr - 0x3F00],
                                    source[addr + 25 - 0x3F00]]
                    else:
                        expected = [1, 0]
                    self.assertEqual(list(result["ram"][0x900 + word * 2:0x902 + word * 2]),
                                     expected)

    def test_missing_table_stops_before_first_ldi_without_writing(self):
        for value in (0, 11, 12, 35, 36, 59, 60, 255):
            ram = self.seed(IXS[0], value)
            result = independent(ram, IXS[0])
            self.assertEqual(result["next_pc"], MISSING_SOURCE_PC[result["group"]])
            self.assertFalse(result["complete"])
            self.assertEqual(result["ram"], bytes(ram))

    def test_source_address_never_escapes_supplied_window(self):
        for value in range(256):
            result = independent(self.seed(IXS[0], value), IXS[0], bytes(512))
            self.assertGreaterEqual(result["source_addr"], 0x3F00)
            self.assertLess(result["source_addr"] + 25, 0x4100)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            independent(bytes(0x2000), 0xE680, bytes(512))
        with self.assertRaises(ValueError):
            independent(bytes(0x2000), IXS[0], bytes(511))


if __name__ == "__main__":
    unittest.main()
