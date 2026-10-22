"""No-ROM regression tests for the bounded original Z80 7EA3 event stage."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_drive_event_7ea3 import independent, read, write, IXS


class Original7EA3EventTests(unittest.TestCase):
    def seed(self, ix=IXS[0]):
        ram = bytearray(0x2000)
        write(ram, ix + 0x4E, 4)
        write(ram, ix - 3, 2)
        write(ram, 0xE699, 3)
        write(ram, ix + 0x75, 0x34)
        for i in range(16):
            write(ram, 0xE800 + i * 16, 2)
            write(ram, 0xE800 + i * 16 + 1, 100 + i)
        return ram

    def test_original_8022_0971_early_returns_and_0985_stop(self):
        for category in (0, 1, 2, 11):
            ram = self.seed()
            write(ram, IXS[0] + 0x4E, category)
            write(ram, IXS[0] + 0x31, 0)
            write(ram, IXS[0] - 3, 2)
            write(ram, IXS[0] + 0x23, 0)
            before = bytes(ram)
            result = independent(ram, IXS[0])
            self.assertEqual((result["branch"], result["next_pc"], result["complete"],
                              result["collision_gate"]),
                             ("collision_0985_pending", 0x0985, False, "pending_0985"))
            self.assertEqual(read(result["ram"], IXS[0] + 0x4E), 1)
            self.assertEqual(read(result["ram"], IXS[0] + 0x31) & 0x40, 0x40)
            self.assertEqual(bytes(ram), before)

        for gate in ("return_status", "return_car_id", "return_secondary"):
            ram = self.seed()
            write(ram, IXS[0] + 0x4E, 0)
            write(ram, IXS[0] + 0x31, 1 if gate == "return_status" else 0)
            write(ram, IXS[0] - 3, 4 if gate == "return_car_id" else 2)
            write(ram, IXS[0] + 0x23, 1 if gate == "return_secondary" else 0)
            result = independent(ram, IXS[0], bytes(280))
            self.assertEqual(result["collision_gate"], gate)
            self.assertEqual(result["next_pc"], 0x7091)
            self.assertTrue(result["complete"])
            self.assertEqual(read(result["ram"], IXS[0] + 0x4E),
                             0 if gate == "return_status" else 1)


    def test_reuse_updates_existing_event_without_allocation(self):
        for ix in IXS:
            ram = self.seed(ix)
            write(ram, ix + 0x33, 0x80)
            write(ram, ix + 0x64, 0xF0)
            result = independent(ram, ix)
            self.assertEqual((result["branch"], result["slot"], result["next_pc"]),
                             ("reuse_event", 15, 0x7091))
            self.assertEqual(read(result["ram"], ix + 0x33), 0x40)
            self.assertEqual([read(result["ram"], 0xE8F0 + k) for k in (2, 3, 8, 14)],
                             [0x39, 0x7F, 4, 0])

    def test_full_pool_rejects_priority_tie(self):
        ram = self.seed()
        for i in range(16):
            write(ram, 0xE800 + i * 16 + 1, 0xDF)
        result = independent(ram, IXS[0])
        self.assertEqual((result["branch"], result["slot"], result["next_pc"]),
                         ("allocation_rejected", None, 0x7091))
        self.assertEqual(result["ram"][0x800:0x900], bytes(ram)[0x800:0x900])

    def test_free_slot_populates_original_record_and_course_tuple(self):
        table = bytes((i * 19 + 3) & 255 for i in range(280))
        for ix in IXS:
            ram = self.seed(ix)
            write(ram, 0xE860, 0)
            before = bytes(ram)
            result = independent(ram, ix, table)
            self.assertEqual((result["branch"], result["slot"], result["next_pc"]),
                             ("allocated_free", 6, 0x7091))
            self.assertEqual([read(result["ram"], 0xE860 + k) for k in
                              (0, 1, 2, 3, 8, 11, 14, 15)],
                             [3, 0xDF, 0x33, 0x7F, 1, 0xFF, 0, 2])
            entry = (3 * 5 + 2) * 4
            self.assertEqual([read(result["ram"], 0xE860 + k) for k in (4, 5, 6, 7)],
                             list(table[entry:entry + 4]))
            self.assertEqual([read(result["ram"], 0xE860 + k) for k in (9, 10)],
                             [0x35, 0x3E])
            self.assertEqual(read(result["ram"], ix + 0x64), 0x60)
            self.assertEqual(bytes(ram), before)

    def test_replacement_tie_chooses_earliest_slot(self):
        ram = self.seed()
        for i in range(16):
            write(ram, 0xE800 + i * 16 + 1, 0xF0)
        for i in (4, 8):
            write(ram, 0xE800 + i * 16 + 1, 3)
        result = independent(ram, IXS[0], bytes(280))
        self.assertEqual((result["branch"], result["slot"]), ("allocated_replace", 4))
        self.assertEqual(read(result["ram"], 0xE841), 0xDF)
        self.assertEqual(read(result["ram"], 0xE881), 3)

    def test_missing_table_preserves_partial_original_writes(self):
        ram = self.seed()
        write(ram, 0xE800, 0)
        result = independent(ram, IXS[0])
        self.assertEqual((result["branch"], result["next_pc"], result["complete"]),
                         ("course_lookup_pending", 0x1767, False))
        self.assertEqual([read(result["ram"], 0xE800 + k) for k in (0, 1, 2, 3, 15)],
                         [3, 0xDF, 0x33, 0x7F, 2])
        self.assertEqual(read(result["ram"], 0xE808), 0)

    def test_invalid_reuse_pointer_fails_closed(self):
        ram = self.seed()
        write(ram, IXS[0] + 0x33, 0x80)
        write(ram, IXS[0] + 0x64, 0x21)
        result = independent(ram, IXS[0])
        self.assertEqual((result["branch"], result["next_pc"], result["complete"]),
                         ("invalid_reuse_slot", 0x7F1A, False))

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            independent(bytes(0x2000), 0xE680)
        with self.assertRaises(ValueError):
            independent(bytes(0x2000), IXS[0], bytes(20))


if __name__ == "__main__":
    unittest.main()
