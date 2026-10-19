"""Tests for generic graphics and QRAM math, without original ROMs or Pillow."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_track_recovery import COLS, ROWS, decode_qram_map, tile_pixels

class TrackRecoveryTests(unittest.TestCase):
    def test_qram_rows_cross_64_row_bank_boundary(self):
        qram = bytearray(0x10000)
        for row in (0, 63, 64, 127):
            low_index = ((row & 0x3f) << 8) | ((row & 0x40) << 9) | 17
            qram[low_index] = row
            qram[low_index | 0x4000] = 5
        tiles = decode_qram_map(qram)
        self.assertEqual((len(tiles), len(tiles[0])), (ROWS, COLS))
        for row in (0, 63, 64, 127):
            self.assertEqual(tiles[row][17], row + (5 << 8))

    def test_reject_invalid_qram_size(self):
        with self.assertRaisesRegex(ValueError, "65536"):
            decode_qram_map(b"bad")

    def test_planar_graphics_pixel_weight(self):
        planes = [bytes(0x20000) for _ in range(6)]
        planes[0] = b"\x01" + planes[0][1:]
        self.assertEqual(tile_pixels(planes, 0)[:9], bytes([32] + [0] * 8))
        planes[5] = b"\x80" + planes[5][1:]
        self.assertEqual(tile_pixels(planes, 0)[7], 1)

    def test_reject_out_of_range_tile(self):
        planes = [bytes(0x20000) for _ in range(6)]
        with self.assertRaises(ValueError):
            tile_pixels(planes, 16384)

if __name__ == "__main__":
    unittest.main()
