import time
import unittest

from amigo.clock import CLOCK, Clock, lap


class ClockTest(unittest.TestCase):
    def test_two_laps_add_up_to_the_total(self):
        clock = Clock()
        token = CLOCK.set(clock)
        try:
            time.sleep(0.02)
            lap("a")
            time.sleep(0.03)
            lap("b")
            total = time.monotonic() - clock.started
        finally:
            CLOCK.reset(token)
        self.assertEqual(list(clock.seconds), ["a", "b"])
        self.assertAlmostEqual(sum(clock.seconds.values()), total, delta=0.01)

    def test_lap_without_a_clock_does_nothing(self):
        lap("a")  # no clock set in this context: no error, nothing booked
        self.assertIsNone(CLOCK.get())


if __name__ == "__main__":
    unittest.main()
