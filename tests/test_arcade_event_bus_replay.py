"""Synthetic MAME-memory replay tests for original 2B77 bus events."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_event_bus_replay import replay, BATTERY_SIZE, QRAM_SIZE
from arcade_event_2b77_bus import independent, IXS


def seed(ix, base, e608=0x07, e613=0x20, e615=0xA0, staged=None):
    ram = bytearray(0x2000)
    ram[ix+0x12-0xE000] = base & 255
    ram[ix+0x13-0xE000] = (base >> 8) & 255
    ram[0x608] = e608
    ram[0x613] = e613
    ram[0x615] = e615
    ram[0x900:0x908] = staged or bytes(range(0x11, 0x19))
    return ram


class OriginalEventBusReplayTests(unittest.TestCase):
    def test_four_qram_planes_and_reverse_address_order(self):
        for ix in IXS:
            for first_plane in (0x00, 0x40, 0x80, 0xC0):
                for second_plane in (0x00, 0x40, 0x80, 0xC0):
                    ram = seed(ix, 0xAEFC, e613=first_plane | 0x20,
                               e615=second_plane | 0x20)
                    before = bytes(ram)
                    q, b = bytes(QRAM_SIZE), bytes(BATTERY_SIZE)
                    result = replay(ram, ix, b, q)
                    original = independent(ram, ix)
                    self.assertEqual(result["ram"], original["ram"])
                    self.assertEqual(result["memory_writes"], original["memory_writes"])
                    self.assertEqual(result["partial_update_requests"], 8)
                    self.assertEqual(result["battery_ram"], b)
                    self.assertEqual(bytes(ram), before)
                    expected = bytearray(q)
                    for control, addr, value in original["memory_writes"]:
                        expected[((control & 0xC0) << 8) | (addr-0xA000)] = value
                    self.assertEqual(result["qram"], bytes(expected))
                    self.assertEqual(result["qram_dirty_tiles"], tuple(
                        ((bank & 0x80) << 8) | (addr - 0xA000)
                        for bank, addr, _ in original["memory_writes"]))

    def test_mixed_battery_and_qram_with_low_byte_wrap(self):
        for ix in IXS:
            ram = seed(ix, 0xADF6, e608=0x04, e613=0x10, e615=0xA0)
            result = replay(ram, ix, bytes(BATTERY_SIZE), bytes(QRAM_SIZE))
            self.assertEqual(result["partial_update_requests"], 4)
            self.assertEqual(len(result["qram_dirty_tiles"]), 4)
            self.assertEqual(result["mapped_writes"][0][0], "battery_ram")
            self.assertEqual(result["mapped_writes"][4][0], "qram")
            expected_b, expected_q = bytearray(BATTERY_SIZE), bytearray(QRAM_SIZE)
            for control, addr, value in result["memory_writes"]:
                if (control & 0x30) == 0x10:
                    expected_b[addr - 0xA000] = value
                else:
                    expected_q[((control & 0xC0) << 8) | (addr - 0xA000)] = value
            self.assertEqual(result["battery_ram"], bytes(expected_b))
            self.assertEqual(result["qram"], bytes(expected_q))

    def test_rom_writes_are_ignored(self):
        ram = seed(IXS[0], 0x4F34, 0x09, 0xA0, 0x20)
        battery, qram = bytes([51])*BATTERY_SIZE, bytes([170])*QRAM_SIZE
        result = replay(ram, IXS[0], battery, qram)
        self.assertEqual(result["battery_ram"], battery)
        self.assertEqual(result["qram"], qram)
        self.assertEqual(result["partial_update_requests"], 0)
        self.assertTrue(all(x[0] == "rom_write_ignored"
                            for x in result["mapped_writes"]))

    def test_unknown_hardware_address_rejected_atomically(self):
        ram = seed(IXS[0], 0xDEFC, 0, 0x20, 0x60)
        battery, qram = bytearray(BATTERY_SIZE), bytearray(QRAM_SIZE)
        before = (bytes(ram), bytes(battery), bytes(qram))
        with self.assertRaisesRegex(ValueError, "separate hardware model"):
            replay(ram, IXS[0], battery, qram)
        self.assertEqual((bytes(ram), bytes(battery), bytes(qram)), before)

    def test_snapshots_mandatory(self):
        ram = seed(IXS[0], 0xAEFC)
        for size in (BATTERY_SIZE - 1, BATTERY_SIZE + 1):
            with self.assertRaises(ValueError):
                replay(ram, IXS[0], bytes(size), bytes(QRAM_SIZE))
        for size in (QRAM_SIZE - 1, QRAM_SIZE + 1):
            with self.assertRaises(ValueError):
                replay(ram, IXS[0], bytes(BATTERY_SIZE), bytes(size))
        with self.assertRaises(ValueError):
            replay(ram, 0xE680, bytes(BATTERY_SIZE), bytes(QRAM_SIZE))

    def test_disabled_memory_view_does_not_mutate_planes(self):
        ram = seed(IXS[0], 0xAB00, e613=0x30, e615=0x30)
        result = replay(ram, IXS[0], bytes([5])*BATTERY_SIZE,
                        bytes([7])*QRAM_SIZE)
        self.assertEqual(result["partial_update_requests"], 0)
        self.assertTrue(all(x[0] == "rom_write_ignored"
                            for x in result["mapped_writes"]))


if __name__ == "__main__":
    unittest.main()
