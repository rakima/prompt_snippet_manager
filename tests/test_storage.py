import json
import tempfile
import unittest
from pathlib import Path

from models import PromptSnippet
from storage import PromptStorage


class PromptStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.path = self.temp_dir / "data" / "prompts.json"

    def test_creates_defaults_and_round_trips_extended_fields(self):
        storage = PromptStorage(self.path)
        prompts = storage.load()
        self.assertEqual(len(prompts), 5)
        prompt = PromptSnippet.create("開発", "テスト", "{name}を確認")
        prompt.tags = ["確認", "開発"]
        prompt.favorite = True
        prompt.use_count = 3
        prompt.last_used_at = "2026-08-19T12:00:00"
        storage.save([prompt])

        loaded = storage.load()[0]
        self.assertEqual(loaded.to_dict(), prompt.to_dict())

    def test_loads_legacy_json_with_defaults(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            json.dumps([{"id": "legacy", "category": "開発", "title": "旧形式", "prompt": "本文"}], ensure_ascii=False),
            encoding="utf-8",
        )

        prompt = PromptStorage(self.path).load()[0]
        self.assertEqual(prompt.tags, [])
        self.assertFalse(prompt.favorite)
        self.assertEqual(prompt.use_count, 0)
        self.assertIsNone(prompt.last_used_at)

    def test_invalid_json_returns_empty_list_and_notifies(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{broken", encoding="utf-8")
        messages = []

        prompts = PromptStorage(self.path, messages.append).load()

        self.assertEqual(prompts, [])
        self.assertEqual(len(messages), 1)

    def test_invalid_use_count_does_not_break_load(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            json.dumps([{"id": "bad-count", "title": "不正値", "prompt": "本文", "use_count": "not-a-number"}], ensure_ascii=False),
            encoding="utf-8",
        )

        prompt = PromptStorage(self.path).load()[0]
        self.assertEqual(prompt.use_count, 0)


if __name__ == "__main__":
    unittest.main()
