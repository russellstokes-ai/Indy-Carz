"""ROM-free tests for bounded original 85B4/1783 linked-record callback."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_callback_85b4_linked import linked_85b4, connected_2eaf_to_2ed0, IXS


def put16(ram, addr, value):
    ram[addr - 0xE000] = value & 255
    ram[addr + 1 - 0xE000] = value >> 8


def setup(ix, current=1, threshold=3, pointer=0xE900, data=0x4A):
    ram = bytearray(0x2000)
    put16(ram, ix + 0x7C, 0xE700)
    ram[ix + 0x04 - 0xE000] = threshold
    ram[ix + 0x7E - 0xE000] = 0xA4
    ram[0x700 + 0x1D] = current
    put16(ram, 0xE700 + 0x1E, pointer - 1)
    if 0xE000 <= pointer <= 0xFFFF:
        ram[pointer - 0xE000] = data
    return ram


class Linked85B4Tests(unittest.TestCase):
    def test_all_five_slots_and_true_early_return(self):
        for ix in IXS:
            ram = setup(ix, current=4, threshold=4)
            before = bytes(ram)
            got = linked_85b4(ram, ix)
            self.assertEqual((got['next_pc'], got['branch'], got['iy']),
                             (0x2EC7, 'ret_nc', 0xE700))
            self.assertEqual(got['ram'], before)
            self.assertTrue(got['returned_to_2ec7'])

    def test_linked_pointer_increment_and_record_update(self):
        for ix in IXS:
            ram = setup(ix, pointer=0xE900, data=0x78)
            before = bytes(ram)
            got = linked_85b4(ram, ix)
            self.assertEqual((got['next_pc'], got['branch'], got['hl']),
                             (0x2EC7, 'ret_full', 0xE900))
            out = got['ram']
            self.assertEqual(out[ix + 0x7E - 0xE000],
                             before[ix + 0x7E - 0xE000] ^ 0x10)
            self.assertEqual(out[0x71E:0x720], bytes([0x00, 0xE9]))
            self.assertEqual(out[0x71D], 0x78)
            self.assertEqual(bytes(ram), before)

    def test_outside_ram_read_stops_after_real_prior_mutations(self):
        ix = IXS[0]
        ram = setup(ix, pointer=0x2040)
        got = linked_85b4(ram, ix)
        self.assertEqual((got['next_pc'], got['branch'], got['hl']),
                         (0x85D3, 'requires_cpu_read', 0x2040))
        self.assertEqual(got['ram'][ix + 0x7E - 0xE000],
                         ram[ix + 0x7E - 0xE000] ^ 0x10)
        self.assertEqual(got['ram'][0x71E:0x720], bytes([0x40, 0x20]))
        self.assertEqual(got['ram'][0x71D], ram[0x71D])

    def test_unknown_iy_record_stops_before_any_memory_change(self):
        ram = setup(IXS[0])
        put16(ram, IXS[0] + 0x7C, 0x10)
        got = linked_85b4(ram, IXS[0])
        self.assertEqual((got['next_pc'], got['branch']), (0x85B7, 'requires_iy_record'))
        self.assertEqual(got['ram'], bytes(ram))

    def test_unknown_iy_pointer_stops_after_exact_xor(self):
        ram = setup(IXS[0])
        put16(ram, IXS[0] + 0x7C, 0xFFE1)
        ram[0x1FFE] = 0
        ram[IXS[0] + 4 - 0xE000] = 1
        got = linked_85b4(ram, IXS[0])
        self.assertEqual((got['next_pc'], got['branch']), (0x85C6, 'requires_iy_pointer'))
        self.assertEqual(got['ram'][IXS[0] + 0x7E - 0xE000],
                         ram[IXS[0] + 0x7E - 0xE000] ^ 0x10)

    def test_connected_callback_original_bit_zero_gate(self):
        for ix in IXS:
            for flag in (0, 1):
                ram = setup(ix)
                ram[ix + 0x31 - 0xE000] = flag
                got = connected_2eaf_to_2ed0(ram, ix)
                self.assertEqual(got['next_pc'], 0x2ED0 if flag else 0x22B8)
                self.assertEqual(got['original_85b4']['next_pc'], 0x2EC7)
                self.assertFalse(got['complete'])
            ram[ix + 0x33 - 0xE000] |= 2
            got = connected_2eaf_to_2ed0(ram, ix)
            self.assertEqual(got['next_pc'], 0x2EB3)
            self.assertTrue(got['complete'])

    def test_bad_memory_pointer_input_rejected(self):
        with self.assertRaises(ValueError):
            linked_85b4(bytes(8191), IXS[0])
        with self.assertRaises(ValueError):
            linked_85b4(bytes(8192), 0xE680)


if __name__ == '__main__':
    unittest.main()
