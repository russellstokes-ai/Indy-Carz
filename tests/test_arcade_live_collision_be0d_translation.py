"""ROM-free regression for original BE0D/BE65 read-only MAME trace audit."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_live_collision_be0d_translation import (
    audit_rows,X_KEYS,Y_KEYS,FIELDS,
)


def pair(x_delta=0,y_delta=0,frame=2500,ix=0xE080):
    source={"frame":frame,"ix":ix,"target_x":(30000+x_delta)&65535,
            "target_y":(0xFFFE+y_delta)&65535,
            "base_x":30000,"base_y":0xFFFE,
            "x1":0xFFFF,"x2":2,"x3":3000,"x4":0xFFFE,
            "y1":1,"y2":65535,"y3":0x8000,"y4":150}
    output=dict(source)
    output["base_x"]=source["target_x"]
    output["base_y"]=source["target_y"]
    for key in X_KEYS:output[key]=(source[key]+x_delta)&65535
    for key in Y_KEYS:output[key]=(source[key]+y_delta)&65535
    def encode(data,phase):
        return {key:(str(data[key]) if key=="frame" else phase if key=="phase"
                     else f"{data[key]:04X}") for key in FIELDS
                if key in data or key=="phase"}
    return [encode(source,"ENTRY"),encode(output,"EXIT")]


class OriginalLiveBE0DAuditTests(unittest.TestCase):
    def test_all_four_original_branch_combinations(self):
        rows=[]
        for j,(x,y) in enumerate(((0,0),(1,0),(0,65535),(50000,65535))):
            rows+=pair(x,y,frame=2500+j)
        result=audit_rows(rows)
        self.assertEqual(result["original_translation_events"],4)
        self.assertEqual(result["branch_counts"],
                         {"both":1,"neither":1,"x_only":1,"y_only":1})
        self.assertEqual(result["original_position_geometry_mismatches"],0)

    def test_exact_wrapping_and_negative_delta(self):
        result=audit_rows(pair(65535,65535))
        self.assertEqual(result["branch_counts"],{"both":1})

    def test_five_original_car_pointers(self):
        rows=[]
        for n in range(5):
            rows+=pair(n,1,frame=2400+n,ix=0xE080+0x100*n)
        result=audit_rows(rows)
        self.assertEqual(len(result["events_by_car"]),5)
        self.assertEqual(result["original_debugger_snapshots"],10)

    def test_original_target_never_mutates_mid_instruction(self):
        rows=pair(1,2)
        rows[1]["target_y"]="ABCD"
        with self.assertRaisesRegex(ValueError,"target words"):
            audit_rows(rows)

    def test_original_geometry_byte_difference_detected(self):
        for axis in X_KEYS+Y_KEYS:
            rows=pair(100,200)
            rows[1][axis]=f"{(int(rows[1][axis],16)+1)&65535:04X}"
            with self.assertRaisesRegex(ValueError,"geometry translation"):
                audit_rows(rows)

    def test_original_base_replacement_detected(self):
        rows=pair(1,2)
        rows[1]["base_x"]="0123"
        with self.assertRaisesRegex(ValueError,"reference word"):
            audit_rows(rows)

    def test_exact_original_entry_exit_order(self):
        rows=pair(1,2)
        with self.assertRaisesRegex(ValueError,"instruction order"):
            audit_rows(rows[::-1])

    def test_wrong_original_car_or_frame_rejected(self):
        rows=pair(1,2)
        rows[1]["ix"]="E180"
        with self.assertRaisesRegex(ValueError,"another frame or car"):
            audit_rows(rows)
        rows=pair(1,2)
        rows[1]["frame"]="2501"
        with self.assertRaisesRegex(ValueError,"another frame or car"):
            audit_rows(rows)

    def test_original_frame_sequence_is_monotonic(self):
        rows=pair(1,1,frame=2501)+pair(1,1,frame=2500)
        with self.assertRaisesRegex(ValueError,"another frame or car"):
            audit_rows(rows)

    def test_unsupported_master_ix_and_wrong_word_domain(self):
        rows=pair()
        rows[0]["ix"]="D000"
        with self.assertRaisesRegex(ValueError,"outside verified"):
            audit_rows(rows)
        rows=pair()
        rows[1]["base_x"]="10000"
        with self.assertRaisesRegex(ValueError,"outside verified"):
            audit_rows(rows)

    def test_corrupt_record_and_truncated_pair_rejected(self):
        with self.assertRaisesRegex(ValueError,"complete ENTRY"):
            audit_rows([])
        with self.assertRaisesRegex(ValueError,"complete ENTRY"):
            audit_rows(pair()[:-1])
        rows=pair()
        del rows[0]["x1"]
        with self.assertRaisesRegex(ValueError,"missing columns"):
            audit_rows(rows)


if __name__=="__main__":
    unittest.main()
