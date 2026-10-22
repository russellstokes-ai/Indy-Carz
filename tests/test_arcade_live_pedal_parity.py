"""ROM-free exhaustive original-Z80 pedal trace parity regression tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_live_pedal_parity import expected_response,audit_rows


def row(frame=2301,raw=0,factor=75,bias=250,ix='E080',addr='E0D7',pc='67D2'):
    return {'frame':str(frame),'pc':pc,'ix':ix,'addr':addr,
            'data':str(expected_response(raw,factor,bias)),
            'pedal':str(raw),'factor':str(factor),'bias':str(bias),
            'car_b1':'2','car_b2':'0'}


class LivePedalParityTests(unittest.TestCase):
    def test_all_256_original_analog_values(self):
        rows=[row(frame=i+1,raw=i) for i in range(256)]
        report=audit_rows(rows,True)
        self.assertEqual(report['original_opcode_writes'],256)
        self.assertEqual(report['unique_8bit_pedal_inputs'],256)
        self.assertEqual(report['mismatches'],0)
        self.assertEqual(report['physical_slot_address'],'E0D7')

    def test_original_byte_formula_exhaustive(self):
        for raw in range(256):
            for factor in (0,1,75,128,254,255):
                for bias in (0,1,128,250,255):
                    result=expected_response(raw,factor,bias)
                    self.assertTrue(0<=result<=126 and result%2==0)

    def test_original_8bit_pedal_no_carry(self):
        self.assertEqual(expected_response(0,75,250),0)
        self.assertEqual(expected_response(255,0,250),0)

    def test_original_carry_saturation(self):
        self.assertEqual(expected_response(255,75,250),126)
        self.assertEqual(expected_response(255,255,255),126)

    def test_single_original_car_pointer_location_required(self):
        with self.assertRaisesRegex(ValueError,'physical'):
            audit_rows([row(ix='E180')])
        with self.assertRaisesRegex(ValueError,'physical'):
            audit_rows([row(addr='E057')])

    def test_original_rom_pc_site_required(self):
        with self.assertRaisesRegex(ValueError,'opcode'):
            audit_rows([row(pc='67CD')])

    def test_original_corrupted_byte_detected(self):
        source=row(raw=255)
        source['data']='0'
        with self.assertRaisesRegex(ValueError,'mismatch'):
            audit_rows([source])

    def test_original_frame_sequence_required(self):
        with self.assertRaisesRegex(ValueError,'monotonically'):
            audit_rows([row(frame=10),row(frame=9)])

    def test_8bit_field_range_required(self):
        source=row()
        source['pedal']='256'
        with self.assertRaisesRegex(ValueError,'byte'):
            audit_rows([source])

    def test_fail_closed_missing_original_inputs(self):
        with self.assertRaises(ValueError):
            audit_rows([])
        with self.assertRaises(ValueError):
            audit_rows([{'frame':'100'}])
        with self.assertRaises(ValueError):
            audit_rows([row()],True)

    def test_allow_same_frame_multiple_real_instruction_writes(self):
        r=audit_rows([row(frame=2301,raw=0),row(frame=2301,raw=255)])
        self.assertEqual(r['original_opcode_writes'],2)


if __name__=='__main__':
    unittest.main()
