"""ROM-free original arcade post-round hardware port handshake tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_io_handshake_2120 import (
    START, STOP, HELPER, HELPER_STOP, RETRIES, POLL_BUDGET,
    independent, check_original, original_opcode,
)


class OriginalPortHandshakeTests(unittest.TestCase):
    def test_verified_original_stage_addresses(self):
        self.assertEqual((START, STOP, HELPER, HELPER_STOP),
                         (0x2120, 0x21A3, 0x2105, 0x2115))
        self.assertEqual((RETRIES, POLL_BUDGET), (10, 50000))

    def test_immediate_original_reset_exchange(self):
        result = independent(((0, 0),), 44, True, 0x13)
        self.assertEqual(result["ports"],
                         [(6, 255), (5, 255), (12, 254), (12, 255),
                          (6, 0), (5, 0)])
        self.assertEqual(result["reads04"], 2)
        self.assertEqual((result["attempts"], result["outcome"]), (1, "success"))

    def test_original_control_ram_initialisation(self):
        result = independent(((0, 0),), 0, True, 0x07)
        self.assertEqual(result["status_e62b"], 0x87)
        for key in ("e7a4", "e7a5", "e7a6"):
            self.assertEqual(result[key], 0x80)
        self.assertEqual(result["e7a7"], 1)
        self.assertEqual(result["e7a8"], 10)
        self.assertEqual(result["e7a9"], 0)
        self.assertEqual(result["e7aa"], 255)

    def test_original_iff_state_and_returned_accumulator(self):
        for ireg in (0, 1, 129, 255):
            enabled = independent(((0, 0),), ireg, True, 0)
            disabled = independent(((0, 0),), ireg, False, 0)
            self.assertEqual((enabled["returned_a"], enabled["returned_iff"]),
                             (ireg, True))
            self.assertEqual((disabled["returned_a"], disabled["returned_iff"]),
                             (1, False))

    def test_original_port4_poll_delay(self):
        result = independent(((2, 3),), 0, False, 0)
        self.assertEqual(result["reads04"], 7)
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["outcome"], "success")

    def test_first_phase_50000_poll_timeout_then_retry(self):
        result = independent(((50000, 0), (0, 0)), 0, False, 0)
        self.assertEqual(result["reads04"], 50002)
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["e7a9"], 1)
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(len(result["ports"]), 10)

    def test_second_phase_timeout_then_retry(self):
        result = independent(((0, 50000), (0, 0)), 0, False, 0)
        self.assertEqual(result["reads04"], 50003)
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["e7a9"], 1)
        self.assertEqual(len(result["ports"]), 12)

    def test_all_ten_retries_exhaust(self):
        result = independent(((50000, 0),)*10, 0, False, 0)
        self.assertEqual(result["attempts"], 10)
        self.assertEqual(result["reads04"], 500000)
        self.assertEqual(result["outcome"], "retry_exhausted")
        self.assertEqual(result["e7a9"], 1)
        self.assertEqual(len(result["ports"]), 40)
        self.assertEqual(result["e7a8"], 10)

    def test_last_attempt_success_preserves_earlier_error_marker(self):
        result = independent(((50000, 0),)*9 + ((0, 0),), 73, True, 0)
        self.assertEqual(result["reads04"], 450002)
        self.assertEqual(result["attempts"], 10)
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["e7a9"], 1)

    def test_failed_retry_requires_explicit_next_input(self):
        with self.assertRaises(ValueError):
            independent(((50000, 0),), 0, False, 0)
        with self.assertRaises(ValueError):
            independent((), 0, False, 0)
        with self.assertRaises(ValueError):
            independent(((50001, 0),), 0, False, 0)
        with self.assertRaises(ValueError):
            independent(((0, 0),)*11, 0, False, 0)

    def test_invalid_cpu_registers_or_forged_rom_rejected(self):
        with self.assertRaises(ValueError):
            independent(((0, 0),), 256, True, 0)
        with self.assertRaises(ValueError):
            independent(((0, 0),), 0, True, -1)
        with self.assertRaises(ValueError):
            independent(((0, 0),), 0, 1, 0)
        with self.assertRaisesRegex(ValueError, "(?i)checksum-verified"):
            check_original(bytes(0x90000))
        with self.assertRaises(ValueError):
            original_opcode(bytes(0x90000), ((0, 0),), 0, False, 0)


if __name__ == "__main__":
    unittest.main()
