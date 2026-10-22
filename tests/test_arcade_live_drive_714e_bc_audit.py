"""ROM-free regression for real original 714E/71C8 live trace audit."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_7124_carry_projection import independent as projection
from arcade_drive_714e_control_selector import independent as select_bc
from arcade_live_drive_714e_bc_audit import audit_rows


def sample(e76b=0x1234,e76d=0,e76f=0,idx0=1,idx1=19,
           frame=2410,ix=0xE080):
    master=bytearray(0x90000)
    ptr=0x6587
    window=bytes((29+17*i)&255 for i in range(257))
    master[ptr:ptr+257]=window
    e768=e769=0
    p=projection(e768,e769,e76b)
    q=select_bc(e76d,e76f,idx0,idx1,(e76b>>8),
                window,0,0,p["carry"])
    if q["next_pc"]!=0x71C8:
        raise ValueError("This fixture should represent a completed normal exit")
    beginning=("SE714E,IX=%04X,AF=%04X,E76D=%04X,E76F=%04X,"
               "E76B=%04X,E768=%02X,E769=%04X,E933=%04X,"
               "IDX0=%02X,IDX1=%02X,TABLE=%04X,E76C=%02X")%(
                   ix,0x40|p["carry"],e76d,e76f,e76b,e768,e769,
                   p["e933"],idx0,idx1,ptr,e76b>>8)
    end="SE71C8,IX=%04X,BC=%04X,AF=0044"%(
        ix,(q["b"]<<8)|q["c"])
    return bytes(master),[
        f"{frame},LINE,{beginning}",
        f"{frame},LINE,{end}"
    ]


class Original714ELiveAuditTests(unittest.TestCase):
    def test_cpu_carry_and_bc_output_agree(self):
        master,rows=sample()
        r=audit_rows(rows,master)
        self.assertEqual(r["paired_original_cpu_events"],1)
        self.assertEqual(r["verified_motion_carry_1"],1)
        self.assertEqual(r["original_BC_output_mismatches"],0)
        self.assertEqual(r["original_7124_projection_carry_mismatches"],0)

    def test_multiple_original_car_slots_and_frame_order(self):
        master,_=sample()
        rows=[]
        for i in range(5):
            _,pair=sample(frame=2410+i,ix=0xE080+256*i)
            rows+=pair
        r=audit_rows(rows,master)
        self.assertEqual(r["paired_original_cpu_events"],5)
        self.assertEqual(len(r["per_car_counts"]),5)

    def test_correctly_detects_original_motion_carry_zero(self):
        master,rows=sample(e76b=0)
        r=audit_rows(rows,master)
        self.assertEqual((r["verified_motion_carry_0"],
                          r["verified_motion_carry_1"]),(1,0))

    def test_live_blended_BC_output_detects_corruption(self):
        master,rows=sample()
        rows[1]=rows[1].replace("BC=", "BC=FFFF_")
        with self.assertRaises(ValueError):
            audit_rows(rows,master)

    def test_original_7124_e933_word_corruption_rejected(self):
        master,rows=sample()
        rows[0]=rows[0].replace("E933=120E","E933=0000")
        with self.assertRaisesRegex(ValueError,"projection or inherited carry"):
            audit_rows(rows,master)

    def test_original_714e_inherited_carry_corruption_rejected(self):
        master,rows=sample()
        rows[0]=rows[0].replace("AF=0041","AF=0040")
        with self.assertRaisesRegex(ValueError,"projection or inherited carry"):
            audit_rows(rows,master)

    def test_cpu_original_table_pointer_restriction(self):
        master,rows=sample()
        rows[0]=rows[0].replace("TABLE=6587","TABLE=E000")
        with self.assertRaisesRegex(ValueError,"pointer"):
            audit_rows(rows,master)

    def test_pointer_bytes_are_checked_against_actual_source(self):
        master,rows=sample()
        altered=bytearray(master)
        altered[0x6587+2]+=1
        with self.assertRaisesRegex(ValueError,"control B/C"):
            audit_rows(rows,bytes(altered))

    def test_original_pc_and_ix_pairing_required(self):
        master,rows=sample()
        rows[1]=rows[1].replace("IX=E080","IX=E180")
        with self.assertRaisesRegex(ValueError,"pairing"):
            audit_rows(rows,master)
        _,rows=sample()
        rows[1]=rows[1].replace("SE71C8","SE714E")
        with self.assertRaisesRegex(ValueError,"pair order"):
            audit_rows(rows,master)

    def test_nonreturning_bypass_not_counted_as_passed(self):
        master,rows=sample()
        rows[0]=rows[0].replace("E76D=0000","E76D=0100").replace(
            "E76F=0000","E76F=0100")
        with self.assertRaisesRegex(ValueError,"bypass"):
            audit_rows(rows,master)

    def test_truncated_and_malformed_rows_fail_closed(self):
        master,rows=sample()
        with self.assertRaisesRegex(ValueError,"complete"):audit_rows([],master)
        with self.assertRaisesRegex(ValueError,"complete"):audit_rows(rows[:1],master)
        with self.assertRaisesRegex(ValueError,"row format"):
            audit_rows(["abc","whatever"],master)


if __name__=="__main__":
    unittest.main()
