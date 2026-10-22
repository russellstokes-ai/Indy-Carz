"""ROM-free regression for genuine original 32-category collision ROM reads.

The synthetic data is NOT authentic original copyrighted program data.
Private original source remains isolated from public GitHub CI.
"""
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from arcade_live_collision_category_parity import audit_rows
from arcade_collision_projection_classification import model


def fixture(category=24,frame=2500,d=12,e=255,angle3d=0):
    master=bytearray(0x90000)
    for i in range(32):
        master[0xBC5C+i*2]=(i*9)&255
    table=master[0xBC5C+category*2]
    row={'frame':str(frame),'pc':'B6FC','ix':'E080','iy':'E180',
         'd':str(d),'e':str(e),'angle3d':str(angle3d),
         'event_index':str(category),'table0':str(table),
         'e925_write':str(table&0x33),'prev_e925':'255',
         'course':'13','round':'0','reg_H':str(table),'reg_L':'52'}
    return bytes(master),row


class OriginalLiveCollisionCategoryTests(unittest.TestCase):
    def test_all_32_original_category_indices_can_be_read(self):
        rows=[]
        for i in range(32):
            master,row=fixture(i,2500+i)
            rows.append(row)
        report=audit_rows(rows,master)
        self.assertEqual(report['observed_category_indices'],list(range(32)))
        self.assertEqual(report['live_adjacent_code_rom_reads'],8)
        self.assertEqual(report['original_structured_category_count'],24)
        self.assertEqual(report['observed_source_or_mask_mismatches'],0)

    def test_adjacent_code_categories_24_to_31_are_not_rejected(self):
        for i in range(24,32):
            master,row=fixture(i)
            report=audit_rows([row],master)
            self.assertEqual(report['live_adjacent_code_rom_reads'],1)

    def test_original_mask_and_pending_other_byte_ignored(self):
        master,row=fixture(29)
        row['prev_e925']='17'
        self.assertEqual(audit_rows([row],master)['observed_source_or_mask_mismatches'],0)

    def test_predict_branch_counts_are_not_claimed_as_observed(self):
        master,row=fixture(25,d=255,e=3)
        result=audit_rows([row],master)
        self.assertEqual(sum(result['predicted_next_branch_counts'].values()),1)
        self.assertIn('not observed branch hits',result['limits'][1])

    def test_wrong_original_rom_source_is_rejected(self):
        master,row=fixture(26)
        row['table0']='0'
        with self.assertRaisesRegex(ValueError,'indexed ROM source'):
            audit_rows([row],master)

    def test_wrong_original_mask_is_rejected(self):
        master,row=fixture(25)
        row['e925_write']='255'
        with self.assertRaisesRegex(ValueError,'E925 contact mask'):
            audit_rows([row],master)

    def test_invalid_original_cpu_pc_car_pointer_and_category(self):
        for key,val in (('pc','0000'),('ix','0000'),('iy','C800'),
                        ('event_index','32')):
            master,row=fixture(25)
            row[key]=val
            with self.assertRaises(ValueError):audit_rows([row],master)

    def test_input_frame_and_byte_bounds(self):
        master,row=fixture()
        with self.assertRaises(ValueError):audit_rows([row,fixture(frame=2400)[1]],master)
        row['angle3d']='256'
        with self.assertRaises(ValueError):audit_rows([row],master)

    def test_truncated_and_empty_traces_rejected(self):
        master,row=fixture()
        with self.assertRaises(ValueError):audit_rows([],master)
        with self.assertRaises(ValueError):audit_rows([{'frame':'1'}],master)
        with self.assertRaises(ValueError):audit_rows([row],bytes(32))

    def test_branch_math_is_byte_safe_for_instruction_adjacent_sources(self):
        for source in (0,11,42,58,211,221,230,233,244):
            mask,projection,pc=model(source,255,128,255)
            self.assertEqual(mask,source&0x33)
            self.assertTrue(0<=projection<256)
            self.assertIn(pc,('B728','B778','B86C'))


if __name__=='__main__':unittest.main()
