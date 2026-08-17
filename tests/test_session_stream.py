import unittest

from noesis_harness.session_stream import (
    MAX_EVENT_BYTES,
    CancellationToken,
    SessionEventBuffer,
    StreamContractError,
)


class SessionStreamTests(unittest.TestCase):
    def test_publish_and_reconnect(self):
        buffer = SessionEventBuffer("sess-1", max_events=3)
        first = buffer.publish("session_started", {"status": "ready"})
        second = buffer.publish("token", {"text": "hello"})
        self.assertEqual(first.sequence, 1)
        self.assertEqual([event.sequence for event in buffer.since(1)], [2])
        self.assertIn("event: token", second.sse())
        self.assertIn('"schema_version":"noesis.session-stream.v1"', second.sse())

    def test_buffer_is_bounded(self):
        buffer = SessionEventBuffer("sess-1", max_events=2)
        buffer.publish("a", {})
        buffer.publish("b", {})
        buffer.publish("c", {})
        self.assertEqual([event.sequence for event in buffer.since()], [2, 3])

    def test_oversized_event_and_bad_cursor_fail_closed(self):
        buffer = SessionEventBuffer("sess-1")
        with self.assertRaises(StreamContractError):
            buffer.publish("large", {"text": "x" * MAX_EVENT_BYTES})
        with self.assertRaises(StreamContractError):
            buffer.since(-1)

    def test_cancellation(self):
        token = CancellationToken()
        token.raise_if_cancelled()
        token.cancel()
        self.assertTrue(token.cancelled)
        with self.assertRaises(StreamContractError):
            token.raise_if_cancelled()


if __name__ == "__main__":
    unittest.main()
