from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from models import PromptSnippet
from storage import PromptStorage, StorageError


class PromptEditor(tk.Toplevel):
    def __init__(self, parent: tk.Misc, prompt: PromptSnippet | None = None):
        super().__init__(parent)
        self.result: tuple[str, str, str] | None = None
        self.title("プロンプトを編集" if prompt else "新しいプロンプト")
        self.geometry("580x460")
        self.minsize(480, 360)
        self.transient(parent)
        self.grab_set()

        form = ttk.Frame(self, padding=18)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(2, weight=1)

        ttk.Label(form, text="カテゴリ").grid(row=0, column=0, sticky="nw", padx=(0, 12), pady=(0, 12))
        self.category_entry = ttk.Entry(form)
        self.category_entry.grid(row=0, column=1, sticky="ew", pady=(0, 12))
        self.category_entry.insert(0, prompt.category if prompt else "その他")

        ttk.Label(form, text="タイトル *").grid(row=1, column=0, sticky="nw", padx=(0, 12), pady=(0, 12))
        self.title_entry = ttk.Entry(form)
        self.title_entry.grid(row=1, column=1, sticky="ew", pady=(0, 12))
        if prompt:
            self.title_entry.insert(0, prompt.title)

        ttk.Label(form, text="本文 *").grid(row=2, column=0, sticky="nw", padx=(0, 12))
        prompt_frame = ttk.Frame(form)
        prompt_frame.grid(row=2, column=1, sticky="nsew")
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)
        self.prompt_text = tk.Text(prompt_frame, wrap="word", undo=True, height=12)
        self.prompt_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(prompt_frame, orient="vertical", command=self.prompt_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.prompt_text.configure(yscrollcommand=scrollbar.set)
        if prompt:
            self.prompt_text.insert("1.0", prompt.prompt)

        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=1, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text="キャンセル", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="保存", command=self.submit).pack(side="right")
        self.category_entry.focus_set()

    def submit(self) -> None:
        category = self.category_entry.get().strip() or "その他"
        title = self.title_entry.get().strip()
        prompt = self.prompt_text.get("1.0", "end-1c").strip()
        if not title or not prompt:
            messagebox.showwarning("入力不足", "タイトルと本文は必須です。", parent=self)
            return
        self.result = (category, title, prompt)
        self.destroy()


class PromptSnippetManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Prompt Snippet Manager")
        self.geometry("980x700")
        self.minsize(760, 520)

        self.status_var = tk.StringVar(value="準備中")
        data_path = Path(__file__).resolve().parent / "data" / "prompts.json"
        self.storage = PromptStorage(data_path, self.show_status)
        self.prompts = self.storage.load()
        self.filtered_prompts: list[PromptSnippet] = []
        self.selected_prompt_id: str | None = None
        if self.status_var.get() == "準備中":
            self.status_var.set("準備完了")
        self.build_ui()
        self.refresh_categories()
        self.select_category("すべて")

    def build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(18, 16, 18, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Prompt Snippet Manager", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="定型プロンプトを選んで、すぐにコピー", foreground="#687078").grid(row=1, column=0, sticky="w", pady=(3, 0))

        content = ttk.PanedWindow(self, orient="horizontal")
        content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))

        category_frame = ttk.LabelFrame(content, text="カテゴリ", padding=8)
        category_frame.columnconfigure(0, weight=1)
        category_frame.rowconfigure(0, weight=1)
        self.category_list = tk.Listbox(category_frame, exportselection=False, activestyle="none", borderwidth=0, highlightthickness=0)
        self.category_list.grid(row=0, column=0, sticky="nsew")
        self.category_list.bind("<<ListboxSelect>>", self.on_category_selected)
        content.add(category_frame, weight=1)

        prompt_frame = ttk.LabelFrame(content, text="プロンプト一覧", padding=8)
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)
        self.prompt_list = tk.Listbox(prompt_frame, exportselection=False, activestyle="none", borderwidth=0, highlightthickness=0)
        self.prompt_list.grid(row=0, column=0, sticky="nsew")
        self.prompt_list.bind("<<ListboxSelect>>", self.on_prompt_selected)
        content.add(prompt_frame, weight=3)

        detail = ttk.LabelFrame(self, text="プロンプト本文", padding=10)
        detail.grid(row=2, column=0, sticky="nsew", padx=18)
        detail.columnconfigure(0, weight=1)
        detail.rowconfigure(0, weight=1)
        self.prompt_text = tk.Text(detail, height=8, wrap="word", state="disabled", background="#f7f8f9", relief="flat", padx=10, pady=8)
        self.prompt_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(detail, orient="vertical", command=self.prompt_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.prompt_text.configure(yscrollcommand=scrollbar.set)

        actions = ttk.Frame(self, padding=(18, 12, 18, 10))
        actions.grid(row=3, column=0, sticky="ew")
        ttk.Button(actions, text="新規", command=self.create_prompt).pack(side="left")
        ttk.Button(actions, text="編集", command=self.edit_prompt).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="削除", command=self.delete_prompt).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="コピー", command=self.copy_prompt).pack(side="right")

        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(18, 8), relief="sunken")
        status.grid(row=4, column=0, sticky="ew")

    def show_status(self, message: str) -> None:
        self.status_var.set(message)

    def refresh_categories(self, selected: str = "すべて") -> None:
        categories = sorted({prompt.category for prompt in self.prompts})
        self.category_list.delete(0, "end")
        all_categories = ["すべて", *categories]
        for category in all_categories:
            self.category_list.insert("end", category)
        if selected in all_categories:
            self.category_list.selection_set(all_categories.index(selected))
            self.category_list.see(all_categories.index(selected))

    def select_category(self, category: str) -> None:
        self.refresh_categories(category)
        self.update_prompt_list(category)

    def on_category_selected(self, _event: tk.Event) -> None:
        selection = self.category_list.curselection()
        if selection:
            self.update_prompt_list(self.category_list.get(selection[0]))

    def update_prompt_list(self, category: str) -> None:
        self.filtered_prompts = [prompt for prompt in self.prompts if category == "すべて" or prompt.category == category]
        self.filtered_prompts.sort(key=lambda prompt: prompt.title.casefold())
        self.prompt_list.delete(0, "end")
        for prompt in self.filtered_prompts:
            self.prompt_list.insert("end", prompt.title)
        if self.filtered_prompts:
            self.prompt_list.selection_set(0)
            self.on_prompt_selected(None)
        else:
            self.selected_prompt_id = None
            self.set_detail("")

    def on_prompt_selected(self, _event: tk.Event | None) -> None:
        selection = self.prompt_list.curselection()
        if not selection:
            return
        prompt = self.filtered_prompts[selection[0]]
        self.selected_prompt_id = prompt.id
        self.set_detail(prompt.prompt)

    def set_detail(self, value: str) -> None:
        self.prompt_text.configure(state="normal")
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", value)
        self.prompt_text.configure(state="disabled")

    def get_selected_prompt(self) -> PromptSnippet | None:
        return next((prompt for prompt in self.prompts if prompt.id == self.selected_prompt_id), None)

    def create_prompt(self) -> None:
        dialog = PromptEditor(self)
        self.wait_window(dialog)
        if dialog.result:
            category, title, prompt_text = dialog.result
            new_prompt = PromptSnippet.create(category, title, prompt_text)
            self.prompts.append(new_prompt)
            self.persist()
            self.select_category(category)
            self.selected_prompt_id = new_prompt.id
            self.update_prompt_list(category)
            self.select_prompt_in_list(new_prompt.id)
            self.show_status("新しいプロンプトを保存しました")

    def edit_prompt(self) -> None:
        prompt = self.get_selected_prompt()
        if not prompt:
            self.show_status("編集するプロンプトを選択してください")
            return
        dialog = PromptEditor(self, prompt)
        self.wait_window(dialog)
        if dialog.result:
            prompt.category, prompt.title, prompt.prompt = dialog.result
            self.persist()
            self.select_category(prompt.category)
            self.select_prompt_in_list(prompt.id)
            self.show_status("プロンプトを更新しました")

    def delete_prompt(self) -> None:
        prompt = self.get_selected_prompt()
        if not prompt:
            self.show_status("削除するプロンプトを選択してください")
            return
        confirmed = messagebox.askyesno("削除の確認", f"「{prompt.title}」を削除しますか？", parent=self)
        if not confirmed:
            return
        self.prompts = [item for item in self.prompts if item.id != prompt.id]
        self.persist()
        self.selected_prompt_id = None
        self.refresh_categories()
        self.select_category("すべて")
        self.show_status("プロンプトを削除しました")

    def copy_prompt(self) -> None:
        prompt = self.get_selected_prompt()
        if not prompt:
            self.show_status("コピーするプロンプトを選択してください")
            return
        self.clipboard_clear()
        self.clipboard_append(prompt.prompt)
        self.update()
        self.show_status("クリップボードにコピーしました")
        self.after(2500, lambda: self.show_status("準備完了"))

    def select_prompt_in_list(self, prompt_id: str) -> None:
        for index, prompt in enumerate(self.filtered_prompts):
            if prompt.id == prompt_id:
                self.prompt_list.selection_clear(0, "end")
                self.prompt_list.selection_set(index)
                self.prompt_list.see(index)
                self.on_prompt_selected(None)
                return

    def persist(self) -> None:
        try:
            self.storage.save(self.prompts)
        except StorageError as error:
            messagebox.showerror("保存エラー", str(error), parent=self)
            self.show_status(str(error))


def main() -> None:
    app = PromptSnippetManager()
    app.mainloop()


if __name__ == "__main__":
    main()
