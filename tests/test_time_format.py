import unittest
import datetime
from noesis_harness.time_format import format_time, format_hm, now_str

class TestTimeFormat(unittest.TestCase):
    def test_format(self): t = datetime.time(14, 30, 0); self.assertEqual(format_time(t), "14:30:00")
    def test_hm(self): t = datetime.time(14, 30, 0); self.assertEqual(format_hm(t), "14:30")
    def test_now(self): self.assertEqual(len(now_str()), 8)
    def test_custom(self): t = datetime.time(9, 5, 3); self.assertEqual(format_time(t, "%I:%M %p"), "09:05 AM")
    def test_midnight(self): t = datetime.time(0, 0, 0); self.assertEqual(format_time(t), "00:00:00")
    def test_noon(self): t = datetime.time(12, 0, 0); self.assertEqual(format_hm(t), "12:00")
    def test_deterministic(self): t = datetime.time(8, 0); self.assertEqual(format_time(t), format_time(t))
    def test_seconds(self): t = datetime.time(0, 0, 59); self.assertEqual(format_time(t), "00:00:59")
    def test_custom_full(self): t = datetime.time(15, 30, 45); self.assertEqual(format_time(t, "%H%M%S"), "153045")
    def test_ampm(self): t = datetime.time(13, 0); self.assertEqual(format_time(t, "%I:%M %p"), "01:00 PM")
