import unittest
from noesis_harness.compact_util import compact, compact_list

class TestCompact(unittest.TestCase):
    def test_dict(self): self.assertEqual(compact({"a":1,"b":None}),{"a":1})
    def test_list(self): self.assertEqual(compact_list([1,None,2,None]),[1,2])
    def test_empty(self): self.assertEqual(compact({}),{})
    def test_all_none(self): self.assertEqual(compact_list([None,None]),[])
    def test_keep_zero(self): self.assertEqual(compact({"a":0,"b":None}),{"a":0})
    def test_keep_empty_str(self): self.assertEqual(compact({"a":""}),{"a":""})
    def test_no_mutate(self): d={"a":1,"b":None}; compact(d); self.assertEqual(d,{"a":1,"b":None})
    def test_determinism(self): self.assertEqual(compact({"a":1,"b":None}), compact({"a":1,"b":None}))
    def test_list_zero(self): self.assertEqual(compact_list([0,None]),[0])
    def test_dict_many(self): self.assertEqual(compact({"a":1,"b":None,"c":2,"d":None}),{"a":1,"c":2})
