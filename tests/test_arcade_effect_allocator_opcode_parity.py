"""ROM-free regression tests for the arcade effect pool priority semantics."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_effect_allocator_opcode_parity import (
    independent_allocator, original_opcodes, verify, STRIDE,
)


def full_pool(priorities, status=3):
    pool = bytearray(256)
    for slot, priority in enumerate(priorities):
        pool[slot*STRIDE] = status
        pool[slot*STRIDE+1] = priority
    return pool


class OriginalEffectPoolTests(unittest.TestCase):
    def test_first_free_slot_overrides_priority(self):
        pool = full_pool([0]*16)
        pool[7*STRIDE] = 0
        pool[15*STRIDE] = 0
        result, slot, updated = independent_allocator(pool, 64)
        self.assertEqual((result, slot), (1, 7))
        self.assertEqual(updated[7*STRIDE+1], 64)
        self.assertEqual(updated[15*STRIDE], 0)
        self.assertEqual(updated[0], 3)

    def test_full_pool_replaces_first_lowest_priority(self):
        priorities = [30, 40, 6, 60, 6] + [80]*11
        before = full_pool(priorities)
        result, slot, after = independent_allocator(before, 7)
        self.assertEqual((result, slot), (0, 2))
        self.assertEqual(after[2*STRIDE+1], 7)
        self.assertEqual(after[4*STRIDE+1], 6)
        self.assertEqual(after[2*STRIDE], 3)  # status set by caller, not allocator
        self.assertEqual(before[2*STRIDE+1], 6)

    def test_full_pool_equal_priority_rejected_without_mutation(self):
        pool = full_pool([16]*16)
        self.assertEqual(independent_allocator(pool, 16), (255, None, bytes(pool)))
        self.assertEqual(independent_allocator(pool, 0), (255, None, bytes(pool)))
        self.assertEqual(independent_allocator(pool, 17)[1], 0)

    def test_nonzero_status_is_occupied(self):
        for status in (1, 2, 3, 255):
            pool = full_pool([12]*16, status=status)
            self.assertEqual(independent_allocator(pool, 12)[0], 255)

    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            independent_allocator(bytes(255), 1)
        with self.assertRaises(ValueError):
            independent_allocator(bytes(256), 256)
        with self.assertRaisesRegex(ValueError, "Verified original"):
            original_opcodes(bytes(0x90000), bytes(256), 10)
        with self.assertRaises(ValueError):
            verify(bytes(0x90000), -1)


if __name__ == "__main__":
    unittest.main()
