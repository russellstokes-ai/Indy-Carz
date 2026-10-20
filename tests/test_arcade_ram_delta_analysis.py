"""ROM-free tests for private per-frame original game state captures."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_ram_delta_analysis import analyse_bytes, RAM_BASE, RECORD_BYTES


def sample_capture(values):
    header = b"ICR1" + RAM_BASE.to_bytes(4, "little") + RECORD_BYTES.to_bytes(4, "little")
    payload = b"".join(number.to_bytes(4, "little") + ram for number, ram in values)
    return header + payload


class MemoryTraceAnalysisTests(unittest.TestCase):
    def test_detect_car_offset_changes_without_dumping_values(self):
        first = bytearray(RECORD_BYTES)
        second = bytearray(first)
        third = bytearray(second)
        second[0x080 + 0x57] = 65  # racer 1 accelerator candidate
        third[0x580 + 0x79] = 3  # sixth initialized record
        result = analyse_bytes(sample_capture([
            (1, bytes(first)), (2, bytes(second)), (3, bytes(third))]))
        self.assertEqual(result["frames"], 3)
        self.assertEqual(result["car_related_records"]["E080"]["total_byte_transitions"], 1)
        self.assertEqual(result["car_related_records"]["E580"]["total_byte_transitions"], 1)
        self.assertEqual(result["car_related_records"]["E180"]["total_byte_transitions"], 0)
        self.assertEqual(result["frame_numbers"], {"first": 1, "last": 3})
        self.assertNotIn("65", str(result))  # no private original byte values in report

    def test_reject_truncated_capture(self):
        with self.assertRaisesRegex(ValueError, "Truncated"):
            analyse_bytes(sample_capture([(1, bytes(RECORD_BYTES))]) + b"\x00")

    def test_reject_repeated_frame_numbers(self):
        zeros = bytes(RECORD_BYTES)
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            analyse_bytes(sample_capture([(10, zeros), (10, zeros)]))

    def test_reject_wrong_header(self):
        with self.assertRaises(ValueError):
            analyse_bytes(b"broken")


if __name__ == "__main__":
    unittest.main()
