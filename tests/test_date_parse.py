import unittest
import datetime
from noesis_harness.date_parse import parse_date, parse_datetime, parse_or_default

class TestDateParse(unittest.TestCase):
    def test_ymd(self): self.assertEqual(parse_date("2026-08-29"), datetime.date(2026, 8, 29))
    def test_dmy(self): self.assertEqual(parse_date("29/08/2026"), datetime.date(2026, 8, 29))
    def test_mdy(self): self.assertEqual(parse_date("08/29/2026"), datetime.date(2026, 8, 29))
    def test_ymd_dot(self): self.assertEqual(parse_date("29.08.2026"), datetime.date(2026, 8, 29))
    def test_compact(self): self.assertEqual(parse_date("20260829"), datetime.date(2026, 8, 29))
    def test_datetime(self): self.assertEqual(parse_datetime("2026-08-29T12:30:00"), datetime.datetime(2026, 8, 29, 12, 30, 0))
    def test_invalid(self):
        with self.assertRaises(ValueError): parse_date("not-a-date")
    def test_or_default(self):
        d = datetime.date(2026, 1, 1)
        self.assertEqual(parse_or_default("2026-08-29", d), datetime.date(2026, 8, 29))
    def test_or_default_bad(self):
        d = datetime.date(2026, 1, 1)
        self.assertEqual(parse_or_default("bad", d), d)
    def test_deterministic(self): self.assertEqual(parse_date("2026-08-29"), parse_date("2026-08-29"))
