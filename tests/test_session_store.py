"""Unit tests for session persistence (save / load / legacy migration)."""

import json
import os
import tempfile
import unittest
from unittest import mock

from session_store import (
    SessionLoadError,
    SessionState,
    delete_session_file,
    describe_session,
    ensure_json_serializable,
    load_session,
    save_session_state,
)


class TestSessionStore(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.session_path = os.path.join(self._dir.name, "session.json")
        self.env = mock.patch.dict(os.environ, {"NEXCODE_SESSION_FILE": self.session_path})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_missing_file_returns_empty_state(self):
        state = load_session(self.session_path)
        self.assertEqual(state.messages, [])
        self.assertEqual(state.version, 1)

    def test_roundtrip_preserves_messages_and_metadata(self):
        original = SessionState(
            messages=[
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            provider="groq",
            model="llama-3.3-70b-versatile",
            mode="confirm",
            workspace="/tmp/ws",
        )
        save_session_state(original, self.session_path)
        loaded = load_session(self.session_path)
        self.assertEqual(loaded.messages, original.messages)
        self.assertEqual(loaded.provider, "groq")
        self.assertEqual(loaded.model, "llama-3.3-70b-versatile")
        self.assertEqual(loaded.mode, "confirm")
        self.assertEqual(loaded.workspace, "/tmp/ws")
        self.assertEqual(loaded.version, 1)
        self.assertTrue(loaded.saved_at)

    def test_legacy_list_format_loads_as_messages(self):
        legacy = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
        ]
        with open(self.session_path, "w", encoding="utf-8") as f:
            json.dump(legacy, f)
        loaded = load_session(self.session_path)
        self.assertEqual(loaded.version, 0)
        self.assertEqual(loaded.messages, legacy)

    def test_invalid_json_raises(self):
        with open(self.session_path, "w", encoding="utf-8") as f:
            f.write("{not json")
        with self.assertRaises(SessionLoadError):
            load_session(self.session_path)

    def test_ensure_json_serializable_nested(self):
        raw = {"role": "user", "content": [{"type": "text", "text": "x"}]}
        safe = ensure_json_serializable(raw)
        self.assertIsInstance(safe["content"], list)
        json.dumps(safe)

    def test_delete_session_file(self):
        save_session_state(
            SessionState(messages=[{"role": "user", "content": "a"}]),
            self.session_path,
        )
        self.assertTrue(os.path.exists(self.session_path))
        delete_session_file(self.session_path)
        self.assertFalse(os.path.exists(self.session_path))

    def test_describe_session(self):
        s = SessionState(
            messages=[{}, {}],
            saved_at="2025-01-01T12:00:00+00:00",
            workspace="/proj",
        )
        text = describe_session(s)
        self.assertIn("2 messages", text)
        self.assertIn("/proj", text)


if __name__ == "__main__":
    unittest.main()
