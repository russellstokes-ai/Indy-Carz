"""ROM-free tests for original B86C two-car status dispatch."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_b86c_dispatch import START,STOP,TARGET,model,opcode,verify


def rec(status=0):
    b=bytearray(256)
    b[0x7C]=status
    return bytes(b)


class OriginalB86CDispatchTests(unittest.TestCase):
    def test_verified_stage_addresses(self):
        self.assertEqual((START,STOP,TARGET),(0xB86C,0xB884,0xB884))

    def test_both_eligible_queue_both_original_call_targets(self):
        self.assertEqual(model(rec(0),rec(0)),(0,1))

    def test_first_skipped_restores_only_second(self):
        self.assertEqual(model(rec(2),rec(0)),(1,))

    def test_second_skipped_restores_only_first(self):
        self.assertEqual(model(rec(0),rec(2)),(0,))

    def test_both_status_bits_skip_all_calls(self):
        self.assertEqual(model(rec(2),rec(2)),())

    def test_unrelated_status_bits_do_not_change_dispatch(self):
        self.assertEqual(model(rec(0xFD),rec(0x81)),(0,1))

    def test_invalid_record_length_or_master_fails_closed(self):
        with self.assertRaises(ValueError):
            model(bytes(255),rec())
        with self.assertRaises(ValueError):
            opcode(bytes(0x90000),rec(),rec())
        with self.assertRaisesRegex(ValueError,'checksum-verified'):
            verify(bytes(0x90000))


if __name__=='__main__':unittest.main()
