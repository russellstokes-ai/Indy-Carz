"""ROM-free tests: original collision B728..B777, verified 0971 fast path."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_contact_two_car_fastpath import (
    START, STOP, ACTIVE, GATE, CAR_FLAGS, CAR_FF, SOURCE, TARGET,
    FullHandlerUnverified, independent, execute_original, verify,
)


def car(active: bool = False, source: int = 13,
        target: int = 33, gate: int = 1, flags: int = 0x10) -> bytes:
    data = bytearray(256)
    data[ACTIVE] = 2 if active else 0
    data[SOURCE], data[TARGET] = source, target
    data[GATE], data[CAR_FLAGS] = gate, flags
    return bytes(data)


class OriginalTwoCarFastPathTests(unittest.TestCase):
    def test_original_bounded_span(self):
        self.assertEqual((START, STOP), (0xB728, 0xB778))

    def test_neither_car_active_is_state_preserving(self):
        first, second = car(), car()
        self.assertEqual(independent(first, second, 127), (first, second, 127))

    def test_first_car_event_writes_original_status_and_input(self):
        first, second, a = independent(car(active=True), car(), 54)
        self.assertEqual((a, first[ACTIVE], first[CAR_FF],
                          first[SOURCE], first[TARGET]), (54, 0x30, 255, 255, 126))
        self.assertEqual(first[CAR_FLAGS] & 0x18, 0x08)
        self.assertEqual(second, car())

    def test_second_car_call_to_0a30_still_operates_on_ix(self):
        first, second, a = independent(
            car(source=0x90), car(active=True, source=71), 117
        )
        self.assertEqual(a, 117)
        # Original CALL 0A30 occurs before IX/IY pointer swap for CALL 0971.
        self.assertEqual(first[TARGET], 0x48)
        self.assertEqual(second[TARGET], 33)
        self.assertEqual(second[SOURCE], 255)
        self.assertEqual(second[ACTIVE], 0x30)

    def test_both_car_events_do_not_write_second_input_response(self):
        first, second, _ = independent(car(active=True), car(active=True), 56)
        self.assertEqual((first[TARGET], second[TARGET]), (126, 33))
        self.assertEqual((first[ACTIVE], second[ACTIVE]), (0x30, 0x30))

    def test_unverified_0971_continue_fails_closed(self):
        with self.assertRaises(FullHandlerUnverified):
            independent(car(active=True, gate=0), car(), 4)
        with self.assertRaises(FullHandlerUnverified):
            independent(car(), car(active=True, gate=0), 4)

    def test_input_a_preserved_and_unrelated_fields_unchanged(self):
        first, second = car(active=True), car(active=True)
        actual_first, actual_second, result_a = independent(first, second, 4)
        self.assertEqual(result_a, 4)
        changed_first = {i for i in range(256) if first[i] != actual_first[i]}
        changed_second = {i for i in range(256) if second[i] != actual_second[i]}
        self.assertTrue(changed_first.issubset({ACTIVE, CAR_FLAGS, CAR_FF, SOURCE, TARGET}))
        self.assertTrue(changed_second.issubset({ACTIVE, CAR_FLAGS, CAR_FF, SOURCE}))

    def test_invalid_records_range_or_rom_fail_closed(self):
        with self.assertRaises(ValueError):
            independent(bytes(255), car(), 3)
        with self.assertRaises(ValueError):
            independent(car(), car(), 256)
        with self.assertRaises(ValueError):
            execute_original(bytes(0x90000), car(active=True), car(), 4)
        with self.assertRaisesRegex(ValueError, "Checksum-verified"):
            verify(bytes(0x90000), cases=0)


if __name__ == "__main__":
    unittest.main()
