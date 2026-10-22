"""ROM-free tests for original B884 pre-callback state and B8AB return gate."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_b884_callback_gate import START,STOP,CALLBACK,model,opcode,verify


def slot():
    return bytes(range(256))


def scratch():
    return bytes([211]*96)


class OriginalB884CallbackTests(unittest.TestCase):
    def test_bounded_stage(self):
        self.assertEqual((START,STOP,CALLBACK),(0xB884,0xB8AC,0xBC8C))

    def test_original_20_byte_copy_to_scratch_only(self):
        r=model(slot(),scratch(),255,0x62)
        self.assertEqual(r['scratch'][:20],slot()[:20])
        self.assertEqual(r['scratch'][20:],scratch()[20:])
        self.assertEqual(r['copy_pairs'],[(i,0xE72B+i) for i in range(20)])
        self.assertEqual(r['bc8c_invocations'],1)

    def test_callback_still_ff_uses_original_ret_z(self):
        r=model(slot(),scratch(),255,0xCA)
        self.assertEqual((r['accumulator'],r['next']),(0,'return_B8AB'))

    def test_non_ff_callback_continues_at_b8ac(self):
        for status in (0,1,254):
            r=model(slot(),scratch(),status,0x71)
            self.assertEqual((r['accumulator'],r['next']),
                             ((status+1)&255,'continue_B8AC'))

    def test_original_bank_high_nibble_and_five(self):
        for before in (0x00,0x15,0xA9,0xF7):
            r=model(slot(),scratch(),255,before)
            expected=(before&0xF0)|5
            self.assertEqual(r['e608'],expected)
            self.assertEqual(r['out_f4'],(expected,))

    def test_invalid_callback_and_record_dimensions(self):
        for bad in (-1,256):
            with self.assertRaises(ValueError):
                model(slot(),scratch(),bad,0)
            with self.assertRaises(ValueError):
                model(slot(),scratch(),255,bad)
        with self.assertRaises(ValueError):
            model(bytes(255),scratch(),255,0)
        with self.assertRaises(ValueError):
            model(slot(),bytes(95),255,0)

    def test_original_opcode_or_bad_master_fails_closed(self):
        with self.assertRaises(ValueError):
            opcode(bytes(0x90000),slot(),scratch(),255,0)
        with self.assertRaisesRegex(ValueError,'Checksum-verified'):
            verify(bytes(0x90000),0)


if __name__=='__main__':unittest.main()
