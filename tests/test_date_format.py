import unittest
import datetime
from noesis_harness.date_format import format_date, format_iso, today_str

class TestDateFormat(unittest.TestCase):
    def test_format(self): dt = datetime.datetime(2026, 8, 29, 12, 30, 0); self.assertEqual(format_date(dt), "2026-08-29")
    def test_iso(self): dt = datetime.datetime(2026, 8, 29, 12, 30, 0); self.assertEqual(format_iso(dt), "2026-08-29T12:30:00")
    def test_today(self): self.assertEqual(len(today_str()), 10)
    def test_custom(self): dt = datetime.datetime(2026, 1, 5); self.assertEqual(format_date(dt, "%d/%m/%Y"), "05/01/2026")
    def test_time_only(self): dt = datetime.datetime(2026, 8, 29, 14, 30, 0); self.assertEqual(format_date(dt, "%H:%M"), "14:30")
    def test_deterministic(self): dt = datetime.datetime(2026, 8, 29); self.assertEqual(format_date(dt), format_date(dt))
    def test_weekday(self): dt = datetime.datetime(2026, 8, 29); self.assertIn(format_date(dt, "%A"), ["Saturday"])
    def test_month_name(self): dt = datetime.datetime(2026, 8, 29); self.assertEqual(format_date(dt, "%B"), "August")
    def test_long(self): dt = datetime.datetime(2026, 12, 31, 23, 59, 59); self.assertEqual(format_iso(dt), "2026-12-31T23:59:59")
    def test_custom_full(self): dt = datetime.datetime(2026, 8, 29, 12, 30, 0); self.assertEqual(format_date(dt, "%Y%m%d%H%M%S"), "20260829123000")
