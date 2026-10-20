"""ROM-free tests for original 155-byte paired coordinate translations."""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import arcade_contact_geometry_translation as tr


def synthetic_program() -> bytes:
    m=bytearray(0x90000)
    for register,(start_hex,_) in tr.STAGE_HASHES.items():
        start=int(start_hex,16)
        m[start:start+155]=tr.stage_template(tr.PREFIX[register])
    return bytes(m)


class OriginalContactTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master=synthetic_program()

    def test_both_mirrored_routines_have_exact_original_shape(self):
        self.assertEqual(len(tr.stage_template(0xDD)),155)
        self.assertEqual(len(tr.stage_template(0xFD)),155)
        self.assertEqual(tr.stage_template(0xDD)[0:len(tr.PROLOGUE)],tr.PROLOGUE)

    def test_all_ten_coordinate_words_update_identically(self):
        record=bytearray(range(256))
        old=bytes(record)
        bc,de=0x0007,0xFFFE # both high bytes safely bypass $1689
        expected=tr.independent_translation(old,bc,de)
        self.assertIsNotNone(expected)
        for register in ("IX","IY"):
            self.assertEqual(tr.original_bounded_stage(self.master,old,bc,de,register),expected)
        for i in range(10):
            before=int.from_bytes(old[i*2:i*2+2],"little")
            after=int.from_bytes(expected[i*2:i*2+2],"little")
            displacement=bc if i<5 else de
            self.assertEqual(after,(before+displacement)&65535)
        self.assertEqual(expected[0x7C],old[0x7C]|0x40)
        self.assertEqual(expected[0x20:0x7C],old[0x20:0x7C])
        self.assertEqual(expected[0x7D:],old[0x7D:])

    def test_scheduler_transfer_not_misrepresented_as_position_update(self):
        record=bytes(256)
        for bc,de in ((0x0500,0),(0xFA00,0),(0,0x0500),(0,0xFA00)):
            self.assertTrue(tr.has_unresolved_scheduler_transfer(bc,de))
            self.assertIsNone(tr.independent_translation(record,bc,de))
            self.assertIsNone(tr.original_bounded_stage(self.master,record,bc,de,"IX"))
        for bc,de in ((0x04FF,0),(0xFB00,0),(0,0xFB00)):
            self.assertFalse(tr.has_unresolved_scheduler_transfer(bc,de))

    def test_256_by_256_gate_boundary_and_sample_parity(self):
        with patch.object(tr,"MASTER_SHA",hashlib.sha256(self.master).hexdigest()):
            report=tr.verify(self.master, 100)
        self.assertEqual(report["actual_state_translations_verified"],200)
        self.assertEqual(report["external_scheduler_gate_classifications"],65536)
        self.assertEqual(report["mismatches"],0)

    def test_original_rom_signature_and_invalid_input_checks(self):
        with self.assertRaisesRegex(ValueError,"Verified private"):
            tr.verify(self.master,0)
        with self.assertRaises(ValueError):
            tr.stage_template(0x00)
        with self.assertRaises(ValueError):
            tr.independent_translation(bytes(255),0,0)
        with self.assertRaises(ValueError):
            tr.has_unresolved_scheduler_transfer(-1,0)


if __name__=="__main__":
    unittest.main()
