import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from models import PromptSnippet
from storage import PromptStorage
from storage import StorageError

try:
    import tkinter as tk

    from main import PromptSnippetManager
except ImportError:
    tk = None
    PromptSnippetManager = None


@unittest.skipIf(tk is None, "Tkinter is unavailable")
class PromptSnippetManagerGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.app = PromptSnippetManager()
            cls.app.withdraw()
        except tk.TclError as error:
            raise unittest.SkipTest(f"GUI environment is unavailable: {error}") from error

    @classmethod
    def tearDownClass(cls):
        if cls.app.winfo_exists():
            cls.app.destroy()

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.app.storage = PromptStorage(self.temp_dir / "prompts.json")
        self.app.prompts = [
            PromptSnippet.create("開発", "変数あり", "{target} を確認。{target} を修正。"),
            PromptSnippet.create("文章作成", "通常", "変数なしの本文"),
        ]
        self.app.search_var.set("")
        self.app.favorite_only.set(False)
        self.app.selected_category = "すべて"
        self.app.refresh_categories()
        self.app.refresh_prompt_list()

    def test_category_filter_and_template_area(self):
        self.app.select_category("開発")

        self.assertEqual(self.app.prompt_list.size(), 1)
        self.assertEqual(self.app.prompt_list.get(0), "変数あり")
        self.assertEqual(len(self.app.template_entries), 1)
        self.assertTrue(self.app.template_area.grid_info())
        self.assertEqual(self.app.prompt_text.get("1.0", "end-1c"), "{target} を確認。{target} を修正。")

        self.app.select_category("文章作成")

        self.assertEqual(self.app.prompt_list.size(), 1)
        self.assertEqual(len(self.app.template_entries), 0)
        self.assertFalse(self.app.template_area.grid_info())

    def test_copy_and_missing_value_status(self):
        self.app.select_category("開発")
        self.app.selected_prompt_id = self.app.filtered_prompts[0].id
        self.app.set_detail_prompt(self.app.filtered_prompts[0].prompt)
        self.app.clipboard_clear()

        self.app.copy_prompt()
        self.assertIn("{target}", self.app.status_var.get())
        with self.assertRaises(tk.TclError):
            self.app.clipboard_get()

        self.app.template_values["target"].set("main.py")
        self.app.copy_prompt()

        self.assertEqual(self.app.clipboard_get(), "main.py を確認。main.py を修正。")
        self.assertEqual(self.app.get_selected_prompt().use_count, 1)

    def test_copy_reports_history_save_failure_without_mutating_memory(self):
        self.app.select_category("開発")
        self.app.selected_prompt_id = self.app.filtered_prompts[0].id
        self.app.set_detail_prompt(self.app.filtered_prompts[0].prompt)
        self.app.template_values["target"].set("main.py")
        original_count = self.app.get_selected_prompt().use_count

        class BrokenStorage:
            def save(self, _prompts):
                raise StorageError("保存失敗")

        self.app.storage = BrokenStorage()
        with patch("main.messagebox.showerror"):
            self.app.copy_prompt()

        self.assertEqual(self.app.clipboard_get(), "main.py を確認。main.py を修正。")
        self.assertEqual(self.app.get_selected_prompt().use_count, original_count)
        self.assertIn("使用履歴の保存に失敗", self.app.status_var.get())

    def test_new_edit_delete_operations_keep_gui_in_sync(self):
        new_prompt = PromptSnippet.create("GitHub", "新規", "本文")
        dialog = type("Dialog", (), {"result": ("GitHub", "新規", "本文", [])})()
        with patch("main.PromptEditor", return_value=dialog), patch.object(self.app, "wait_window"):
            self.app.create_prompt()
        self.assertTrue(any(prompt.title == new_prompt.title for prompt in self.app.prompts))

        selected = next(prompt for prompt in self.app.prompts if prompt.title == "新規")
        self.app.selected_prompt_id = selected.id
        edit_dialog = type("Dialog", (), {"result": ("GitHub", "編集済み", "更新本文", [])})()
        with patch("main.PromptEditor", return_value=edit_dialog), patch.object(self.app, "wait_window"):
            self.app.edit_prompt()
        self.assertEqual(self.app.get_selected_prompt().title, "編集済み")

        with patch("main.messagebox.askyesno", return_value=True):
            self.app.delete_prompt()
        self.assertFalse(any(prompt.id == selected.id for prompt in self.app.prompts))

    def test_clipboard_variable_is_filled_from_system_clipboard(self):
        prompt = PromptSnippet.create("開発", "クリップボード", "内容:\n{clipboard}")
        self.app.prompts = [prompt]
        self.app.selected_prompt_id = prompt.id
        self.app.clipboard_clear()
        self.app.clipboard_append("貼り付ける内容")
        self.app.set_detail_prompt(prompt.prompt)

        self.assertEqual(self.app.template_values["clipboard"].get(), "貼り付ける内容")
        self.assertEqual(str(self.app.template_entries["clipboard"]["state"]), "readonly")

        self.app.copy_prompt()

        self.assertEqual(self.app.clipboard_get(), "内容:\n貼り付ける内容")


if __name__ == "__main__":
    unittest.main()
