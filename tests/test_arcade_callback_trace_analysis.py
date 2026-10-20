"""Synthetic MAME write traces (no original ROM or private runtime data)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_callback_trace_analysis import analyse, describe_address


def fake_trace() -> str:
    lines = ["frame,kind,address,value,master_pc"]
    for slot in range(6):
        base = 0xE000 + slot*0x100
        for offset, value in ((0x94, 0xAF), (0x95, 0x2E),
                              (0x96, 0x1E), (0x97, 0x2F)):
            lines.append(f"1,snapshot,{base+offset:04X},{value:02X},FFFF")
    for addr, val in ((0xE699, 0), (0xE69B, 0), (0xE67D, 0)):
        lines.append(f"1,snapshot_global,{addr:04X},{val:02X},FFFF")
    # Write high byte first, then low: should produce ONE actual new PC
    # at end-of-frame rather than an imaginary intermediate callback.
    lines.extend([
        "2,callback_write,E095,74,756B",
        "2,callback_write,E094,C9,756F",
        "3,global_write,E699,03,62C2",
        "3,global_write,E69B,01,62B9",
        "3,callback_write,E095,75,77BF",
        "3,callback_write,E094,6B,77C2",
    ])
    return "\n".join(lines) + "\n"


class OriginalCallbackTraceTests(unittest.TestCase):
    def test_slot_and_callback_byte_mapping(self):
        self.assertEqual(describe_address(0xE094), (0, "first", 0))
        self.assertEqual(describe_address(0xE095), (0, "first", 1))
        self.assertEqual(describe_address(0xE596), (5, "second", 0))
        self.assertIsNone(describe_address(0xE699))
        self.assertIsNone(describe_address(0xE398))

    def test_frame_boundary_prevents_intermediate_false_callback(self):
        result = analyse(fake_trace())
        self.assertEqual(result["observed_frames"], 3)
        self.assertEqual(result["callback_byte_writes"], 4)
        events = result["callback_pointer_transitions"]
        self.assertEqual(len(events), 2)
        self.assertEqual([(r["frame"], r["previous_pc"], r["new_pc"])
                          for r in events],
                         [(2, "2EAF", "74C9"), (3, "74C9", "756B")])
        self.assertEqual(len(result["last_observed_callback_pcs"]), 12)

    def test_course_and_championship_changes(self):
        result = analyse(fake_trace())
        fields = result["global_counter_changes"]
        self.assertEqual([(r["field"], r["old"], r["new"]) for r in fields],
                         [("course_index", 0, 3), ("round_counter", 0, 1)])

    def test_refuse_wrong_structure(self):
        with self.assertRaisesRegex(ValueError, "callback write CSV"):
            analyse("frame,kind,value\n1,hello,42\n")
        with self.assertRaisesRegex(ValueError, "backwards"):
            analyse("frame,kind,address,value,master_pc\n"
                    "2,snapshot,E094,AF,FFFF\n"
                    "1,snapshot,E095,2E,FFFF\n")
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            analyse("frame,kind,address,value,master_pc\n"
                    "1,callback_write,F000,AA,1000\n")


if __name__ == "__main__":
    unittest.main()
