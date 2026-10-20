"""ROM-free checks of original collision-side dispatcher and contact-byte mask."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_payload_dispatch import START, END, independent, original, verify


def generated_synthetic_wrapper() -> bytes:
    # Minimal synthetic assembly of the documented original control-flow
    # pattern; no complete original ROM, contact table or assets included.
    mem=bytearray(0x90000)
    movepointers=bytes([0xDD,0xE5,0xFD,0xE5,0xDD,0xE1,0xFD,0xE1])
    control=bytes([0x3A,0x1B,0xE9,0xB7,0xF2,0xC9,0xB5,0xE6,0x7F])
    callback=bytes([0xCD,0xC9,0xB5])
    program=control+movepointers+callback+movepointers+bytes([0xC9])
    assert len(program)==END-START
    mem[START:END]=program
    return bytes(mem)


class OriginalContactSideTests(unittest.TestCase):
    def test_all_256_contact_bytes_across_three_pointer_pairs(self):
        memory=generated_synthetic_wrapper()
        for data in range(256):
            for first,second in ((0xE080,0xE180),(0xE380,0xE480),(0x1111,0x2222)):
                self.assertEqual(original(memory,data,first,second),
                                 independent(data,first,second))

    def test_high_bit_swap_and_seven_bit_payload(self):
        v=independent(0x80,0xE080,0xE180)
        self.assertEqual(v["arg"],0)
        self.assertEqual((v["handler_first"],v["handler_second"]),(0xE180,0xE080))
        self.assertEqual((v["return_ix"],v["return_iy"]),(0xE080,0xE180))
        w=independent(0x7F,0xE080,0xE180)
        self.assertEqual(w["arg"],127)
        self.assertEqual((w["handler_first"],w["handler_second"]),(0xE080,0xE180))
        self.assertEqual(independent(0xFF,1,2)["arg"],127)

    def test_bad_original_branch_fails_closed(self):
        memory=bytearray(generated_synthetic_wrapper())
        memory[START+5]=0xAA
        with self.assertRaisesRegex(ValueError,"Unexpected original jump"):
            original(bytes(memory),0,1,2)
        with self.assertRaises(ValueError):
            independent(256,1,2)

    def test_verify_gate_protects_original_rom(self):
        with self.assertRaisesRegex(ValueError,"checksum-verified"):
            verify(generated_synthetic_wrapper())


if __name__=="__main__":
    unittest.main()
