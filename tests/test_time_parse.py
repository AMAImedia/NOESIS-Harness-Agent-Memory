import unittest
import datetime
from noesis_harness.time_parse import parse_time, parse_or_default

class TestTimeParse(unittest.TestCase):
    def test_hms(self): self.assertEqual(parse_time("14:30:00"), datetime.time(14, 30, 0))
    def test_hm(self): self.assertEqual(parse_time("14:30"), datetime.time(14, 30))
    def test_ampm(self): self.assertEqual(parse_time("02:30 PM"), datetime.time(14, 30))
    def test_midnight(self): self.assertEqual(parse_time("00:00:00"), datetime.time(0, 0))
    def test_noon(self): self.assertEqual(parse_time("12:00"), datetime.time(12, 0))
    def test_invalid(self):
        with self.assertRaises(ValueError): parse_time("not-a-time")
    def test_or_default(self):
        d = datetime.time(9, 0)
        self.assertEqual(parse_or_default("14:30", d), datetime.time(14, 30))
    def test_or_default_bad(self):
        d = datetime.time(9, 0)
        self.assertEqual(parse_or_default("bad", d), d)
    def test_deterministic(self): self.assertEqual(parse_time("08:00"), parse_time("08:00"))
    def test_ampm_s(self): self.assertEqual(parse_time("12:30:45 PM"), datetime.time(12, 30, 45))
