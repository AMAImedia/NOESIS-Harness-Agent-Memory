import unittest
from noesis_harness.flatten import flat_list, flat_dict

class TestFlatten(unittest.TestCase):
    def test_list(self): self.assertEqual(flat_list([1,[2,3],4]),[1,2,3,4])
    def test_nested(self): self.assertEqual(flat_list([1,[2,[3]]]),[1,2,3])
    def test_empty(self): self.assertEqual(flat_list([]),[])
    def test_flat(self): self.assertEqual(flat_list([1,2,3]),[1,2,3])
    def test_deep(self): self.assertEqual(flat_list([[[1]]]),[1])
    def test_dict(self): self.assertEqual(flat_dict({"a":{"b":1,"c":2}}),{"a.b":1,"a.c":2})
    def test_dict_nested(self): self.assertEqual(flat_dict({"a":{"b":{"c":1}}}),{"a.b.c":1})
    def test_dict_flat(self): self.assertEqual(flat_dict({"a":1}),{"a":1})
    def test_determinism(self): self.assertEqual(flat_list([1,[2]]), flat_list([1,[2]]))
    def test_no_mutate(self): a=[1,[2]]; flat_list(a); self.assertEqual(a,[1,[2]])
