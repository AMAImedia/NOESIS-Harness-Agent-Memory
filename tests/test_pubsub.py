import unittest
from noesis_harness.pubsub import PubSub

class TestPubSub(unittest.TestCase):
    def test_publish(self):
        ps = PubSub(); got = []; ps.subscribe("t", lambda m: got.append(m)); self.assertEqual(ps.publish("t", 1), 1); self.assertEqual(got, [1])
    def test_multiple_subs(self):
        ps = PubSub(); a = []; b = []; ps.subscribe("t", lambda m: a.append(m)); ps.subscribe("t", lambda m: b.append(m))
        self.assertEqual(ps.publish("t", 5), 2); self.assertEqual(a, [5]); self.assertEqual(b, [5])
    def test_no_subs(self): ps = PubSub(); self.assertEqual(ps.publish("x", 1), 0)
    def test_topics(self): ps = PubSub(); ps.subscribe("a", lambda m: None); ps.subscribe("b", lambda m: None); self.assertEqual(set(ps.topics()), {"a", "b"})
    def test_unrelated_topic(self):
        ps = PubSub(); got = []; ps.subscribe("a", lambda m: got.append(m)); ps.publish("b", 1); self.assertEqual(got, [])
    def test_determinism(self): ps = PubSub(); ps.subscribe("t", lambda m: None); self.assertEqual(ps.publish("t", 1), 1)
    def test_order(self):
        ps = PubSub(); got = []; ps.subscribe("t", lambda m: got.append(1)); ps.subscribe("t", lambda m: got.append(2)); ps.publish("t", None); self.assertEqual(got, [1, 2])
    def test_many(self):
        ps = PubSub(); got = []; [ps.subscribe("t", lambda m: got.append(m)) for _ in range(5)]; ps.publish("t", 1); self.assertEqual(len(got), 5)
    def test_value(self): ps = PubSub(); got = []; ps.subscribe("t", lambda m: got.append(m)); ps.publish("t", "hi"); self.assertEqual(got, ["hi"])
    def test_empty_msg(self): ps = PubSub(); got = []; ps.subscribe("t", lambda m: got.append(m)); ps.publish("t", None); self.assertEqual(got, [None])
