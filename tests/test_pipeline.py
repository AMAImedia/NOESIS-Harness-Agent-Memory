import unittest
from noesis_harness.pipeline import Pipeline

class TestPipeline(unittest.TestCase):
    def test_run(self): p = Pipeline([lambda x: x+1, lambda x: x*2]); self.assertEqual(p.run(3), 8)
    def test_empty(self): self.assertEqual(Pipeline().run(5), 5)
    def test_add(self): p = Pipeline(); p.add(lambda x: x+1); self.assertEqual(len(p), 1); self.assertEqual(p.run(1), 2)
    def test_len(self): self.assertEqual(len(Pipeline([lambda x: x])), 1)
    def test_order(self): p = Pipeline([lambda x: x+"a", lambda x: x+"b"]); self.assertEqual(p.run(""), "ab")
    def test_determinism(self): p = Pipeline([lambda x: x+1]); self.assertEqual(p.run(1), p.run(1))
    def test_many(self): p = Pipeline([lambda x: x+1 for _ in range(5)]); self.assertEqual(p.run(0), 5)
    def test_no_mutation(self): p = Pipeline([lambda x: x+1]); p.run(1); self.assertEqual(len(p), 1)
    def test_init_steps(self): p = Pipeline([lambda x: x]); self.assertEqual(len(p), 1)
    def test_string(self): p = Pipeline([str.upper]); self.assertEqual(p.run("hi"), "HI")
