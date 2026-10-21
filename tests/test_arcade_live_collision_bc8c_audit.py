"""ROM-free test coverage for authentic MAME BC8C collision retry traces."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_live_collision_bc8c_audit import audit_rows, audit_file


def row(pc,frame=2301,ix="E080",bank="A5",counter="00",
        car="02",e768="35",e76a="35",e76b="C000",e765="ABCD"):
    return dict(frame=str(frame),pc=pc,ix=ix,iy="64E8",e608=bank,
                e976="05",e92e=counter,e92c="00",car_b1=car,
                e768=e768,e76a=e76a,e76b=e76b,e765=e765)


def original_normal():
    return [
        row("BC8C",bank="A0",counter="BE",car="82"),
        row("BC9E",bank="A5",counter="BE"),
        row("BCA5",bank="A5",counter="00"),
        row("BCFA",bank="A5",counter="01"),
    ]


def original_retry(iterations=2, fallback=False):
    rows=original_normal()
    for count in range(1,iterations):
        rows.append(row("BCA5",counter=f"{count:02X}"))
        if count+1>=18 and fallback:
            rows.append(row("BCB2",counter=f"{count+1:02X}"))
            rows.append(row("C468",counter=f"{count+1:02X}"))
            rows.append(row("BCF7",counter=f"{count+1:02X}",
                            e76a="35",e76b="CC00",e765="0000"))
            rows.append(row("BC9E",counter=f"{count+1:02X}",
                            e76a="35",e76b="CC00",e765="0000"))
            rows.append(row("BCA5",counter="00",e76b="CC00",e765="0000"))
            rows.append(row("BCFA",counter="01",e76b="CC00",e765="0000"))
            break
        else:
            rows.append(row("BCFA",counter=f"{count+1:02X}"))
    return rows


class OriginalCollisionBC8CLiveTests(unittest.TestCase):
    def test_fresh_entry_bank_bit_and_counters(self):
        result=audit_rows(original_normal())
        self.assertEqual(result["bc8c_entries"],1)
        self.assertEqual(result["bca5_retry_checks"],1)
        self.assertEqual(result["normal_collision_processing_entries"],1)
        self.assertEqual(result["c468_reset_invocations"],0)
        self.assertEqual(result["mismatches"],0)

    def test_original_retry_second_and_third_attempt(self):
        result=audit_rows(original_retry(3))
        self.assertEqual(result["original_counter_before_retry"],{0:1,1:1,2:1})
        self.assertEqual(result["bca5_retry_checks"],3)

    def test_original_fallback_after_eighteenth_attempt(self):
        result=audit_rows(original_retry(18,True))
        self.assertEqual(result["c468_reset_invocations"],1)
        self.assertEqual(result["original_fallbacks_to_bc9e"],1)
        self.assertEqual(result["normal_collision_processing_entries"],18)

    def test_invalid_initial_stage_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"must start"):
            audit_rows(original_normal()[1:])

    def test_original_bank_setup_bitwise_OR_enforced(self):
        data=original_normal()
        data[1]["e608"]="A0"
        with self.assertRaisesRegex(ValueError,"F4 bank"):
            audit_rows(data)

    def test_original_status_bit7_must_be_cleared(self):
        data=original_normal()
        data[1]["car_b1"]="82"
        with self.assertRaisesRegex(ValueError,"RES7"):
            audit_rows(data)

    def test_original_counter_reset_and_increment_enforced(self):
        for pos,byte in ((2,"01"),(3,"00")):
            data=original_normal()
            data[pos]["e92e"]=byte
            with self.assertRaises(ValueError):audit_rows(data)

    def test_fallback_requires_original_C468_motion_reset(self):
        data=original_retry(18,True)
        index=next(i for i,x in enumerate(data) if x["pc"]=="BCF7")
        data[index]["e76b"]="FFFF"
        with self.assertRaisesRegex(ValueError,"reset callback"):
            audit_rows(data)

    def test_invalid_reordered_PC_fails_closed(self):
        data=original_normal()
        data[2]["pc"]="BCB2"
        with self.assertRaisesRegex(ValueError,"ordering"):
            audit_rows(data)

    def test_original_car_continuity_required(self):
        data=original_normal()
        data[2]["ix"]="E180"
        with self.assertRaisesRegex(ValueError,"changed frame/car"):
            audit_rows(data)

    def test_original_frame_order_enforced(self):
        data=original_normal()
        data[2]["frame"]="2300"
        with self.assertRaisesRegex(ValueError,"monotonic"):
            audit_rows(data)

    def test_original_bad_field_or_car_pointer_rejected(self):
        data=original_normal()
        data[0]["ix"]="F000"
        with self.assertRaisesRegex(ValueError,"Unexpected original"):
            audit_rows(data)
        data=original_normal()
        data[0]["e976"]="100"
        with self.assertRaisesRegex(ValueError,"8-bit"):
            audit_rows(data)

    def test_empty_and_broken_ROM_rejected(self):
        with self.assertRaises(ValueError):audit_rows([])
        with self.assertRaises(ValueError):audit_rows([{"frame":"1"}])
        with self.assertRaises((OSError,ValueError)):
            audit_file(Path("/no/such.csv"),Path("/no/rom.bin"))

if __name__=="__main__":
    unittest.main()
