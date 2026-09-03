from __future__ import annotations

import re
import tkinter as tk
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from models import PromptSnippet
from storage import PromptStorage, StorageError


class PromptEditor(tk.Toplevel):
    def __init__(self, parent: tk.Misc, prompt: PromptSnippet | None = None):
        super().__init__(parent)
        self.result: tuple[str, str, str, list[str]] | None = None
        self.title("プロンプトを編集" if prompt else "新しいプロンプト")
        self.geometry("580x460")
        self.minsize(480, 360)
        self.transient(parent)
        self.grab_set()

        form = ttk.Frame(self, padding=18)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(3, weight=1)

        ttk.Label(form, text="カテゴリ").grid(row=0, column=0, sticky="nw", padx=(0, 12), pady=(0, 12))
        self.category_entry = ttk.Entry(form)
        self.category_entry.grid(row=0, column=1, sticky="ew", pady=(0, 12))
        self.category_entry.insert(0, prompt.category if prompt else "その他")

        ttk.Label(form, text="タイトル *").grid(row=1, column=0, sticky="nw", padx=(0, 12), pady=(0, 12))
        self.title_entry = ttk.Entry(form)
        self.title_entry.grid(row=1, column=1, sticky="ew", pady=(0, 12))
        if prompt:
            self.title_entry.insert(0, prompt.title)

        ttk.Label(form, text="タグ").grid(row=2, column=0, sticky="nw", padx=(0, 12), pady=(0, 12))
        self.tags_entry = ttk.Entry(form)
        self.tags_entry.grid(row=2, column=1, sticky="ew", pady=(0, 12))
        self.tags_entry.insert(0, ", ".join(prompt.tags) if prompt else "")

        ttk.Label(form, text="本文 *").grid(row=3, column=0, sticky="nw", padx=(0, 12))
        prompt_frame = ttk.Frame(form)
        prompt_frame.grid(row=3, column=1, sticky="nsew")
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
        buttons.grid(row=4, column=1, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text="キャンセル", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="保存", command=self.submit).pack(side="right")
        self.category_entry.focus_set()

    def submit(self) -> None:
        category = self.category_entry.get().strip() or "その他"
        title = self.title_entry.get().strip()
        prompt = self.prompt_text.get("1.0", "end-1c").strip()
        tags = [tag.strip() for tag in self.tags_entry.get().split(",") if tag.strip()]
        if not title or not prompt:
            messagebox.showwarning("入力不足", "タイトルと本文は必須です。", parent=self)
            return
        self.result = (category, title, prompt, tags)
        self.destroy()


TEMPLATE_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def template_variables(value: str) -> list[str]:
    return list(dict.fromkeys(match.group(1) for match in TEMPLATE_PATTERN.finditer(value)))


def render_template(value: str, replacements: dict[str, str]) -> str:
    return TEMPLATE_PATTERN.sub(lambda match: replacements[match.group(1)], value)


def read_clipboard(root: tk.Misc) -> str:
    try:
        return root.clipboard_get()
    except tk.TclError:
        return ""


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
        self.selected_category = "すべて"
        self.search_var = tk.StringVar()
        self.sort_var = tk.StringVar(value="タイトル順")
        self.favorite_only = tk.BooleanVar(value=False)
        self.template_entries: dict[str, ttk.Entry] = {}
        self.template_values: dict[str, tk.StringVar] = {}
        self.template_entry_order: list[ttk.Entry] = []
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
        controls = ttk.Frame(header)
        controls.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        controls.columnconfigure(1, weight=1)
        ttk.Label(controls, text="検索").grid(row=0, column=0, padx=(0, 8))
        search_entry = ttk.Entry(controls, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_prompt_list())
        ttk.Label(controls, text="並び替え").grid(row=0, column=2, padx=(14, 8))
        sort_box = ttk.Combobox(controls, textvariable=self.sort_var, values=("タイトル順", "使用回数順", "新しく使った順"), state="readonly", width=15)
        sort_box.grid(row=0, column=3)
        sort_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_prompt_list())
        ttk.Checkbutton(controls, text="お気に入りのみ", variable=self.favorite_only, command=self.refresh_prompt_list).grid(row=0, column=4, padx=(14, 0))

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

        self.template_area = ttk.Frame(detail)
        self.template_area.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.template_area.columnconfigure(0, weight=1)
        self.template_area.rowconfigure(0, weight=1)
        self.template_canvas = tk.Canvas(self.template_area, height=130, background="#f7f8f9", highlightthickness=0)
        self.template_canvas.grid(row=0, column=0, sticky="ew")
        self.template_scrollbar = ttk.Scrollbar(self.template_area, orient="vertical", command=self.template_canvas.yview)
        self.template_scrollbar.grid(row=0, column=1, sticky="ns")
        self.template_canvas.configure(yscrollcommand=self.template_scrollbar.set)
        self.template_frame = ttk.Frame(self.template_canvas)
        self.template_window = self.template_canvas.create_window((0, 0), window=self.template_frame, anchor="nw")
        self.template_frame.columnconfigure(1, weight=1)
        self.template_frame.bind("<Configure>", lambda _event: self.template_canvas.configure(scrollregion=self.template_canvas.bbox("all")))
        self.template_canvas.bind("<Configure>", lambda event: self.template_canvas.itemconfigure(self.template_window, width=event.width))
        self.template_area.grid_remove()

        actions = ttk.Frame(self, padding=(18, 12, 18, 10))
        actions.grid(row=3, column=0, sticky="ew")
        ttk.Button(actions, text="新規", command=self.create_prompt).pack(side="left")
        ttk.Button(actions, text="編集", command=self.edit_prompt).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="削除", command=self.delete_prompt).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="お気に入り切替", command=self.toggle_favorite).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="コピー", command=self.copy_prompt).pack(side="right")

        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(18, 8), relief="sunken")
        status.grid(row=4, column=0, sticky="ew")

    def show_status(self, message: str) -> None:
        self.status_var.set(message)

    def refresh_categories(self, selected: str = "すべて") -> None:
        categories = sorted({prompt.category for prompt in self.prompts})
        self.category_list.delete(0, "end")
        all_categories = ["すべて", "お気に入り", *categories]
        for category in all_categories:
            self.category_list.insert("end", category)
        if selected in all_categories:
            self.category_list.selection_set(all_categories.index(selected))
            self.category_list.see(all_categories.index(selected))

    def select_category(self, category: str) -> None:
        self.selected_category = category
        self.refresh_categories(category)
        self.refresh_prompt_list()

    def on_category_selected(self, _event: tk.Event) -> None:
        selection = self.category_list.curselection()
        if selection:
            self.selected_category = self.category_list.get(selection[0])
            self.refresh_prompt_list()

    def refresh_prompt_list(self) -> None:
        query = self.search_var.get().strip().casefold()
        category = self.selected_category
        self.filtered_prompts = [
            prompt for prompt in self.prompts
            if (category == "すべて" or (category == "お気に入り" and prompt.favorite) or prompt.category == category)
            and (not self.favorite_only.get() or prompt.favorite)
            and (not query or query in prompt.title.casefold() or query in prompt.prompt.casefold() or query in prompt.category.casefold() or any(query in tag.casefold() for tag in prompt.tags))
        ]
        if self.sort_var.get() == "使用回数順":
            self.filtered_prompts.sort(key=lambda prompt: (-prompt.use_count, prompt.title.casefold()))
        elif self.sort_var.get() == "新しく使った順":
            self.filtered_prompts.sort(key=lambda prompt: (prompt.last_used_at or "", prompt.title.casefold()), reverse=True)
        else:
            self.filtered_prompts.sort(key=lambda prompt: prompt.title.casefold())
        self.prompt_list.delete(0, "end")
        for prompt in self.filtered_prompts:
            marker = "★ " if prompt.favorite else ""
            self.prompt_list.insert("end", f"{marker}{prompt.title}")
        if self.filtered_prompts:
            self.prompt_list.selection_set(0)
            self.on_prompt_selected(None)
        else:
            self.selected_prompt_id = None
            self.set_detail_prompt("")

    def on_prompt_selected(self, _event: tk.Event | None) -> None:
        selection = self.prompt_list.curselection()
        if not selection:
            return
        prompt = self.filtered_prompts[selection[0]]
        self.selected_prompt_id = prompt.id
        self.set_detail_prompt(prompt.prompt)

    def set_detail_prompt(self, value: str) -> None:
        for entry in self.template_entry_order:
            entry.destroy()
        self.template_entries.clear()
        self.template_values.clear()
        self.template_entry_order.clear()
        for child in self.template_frame.winfo_children():
            child.destroy()
        self.prompt_text.configure(state="normal")
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", value)
        self.prompt_text.configure(state="disabled")

        variables = template_variables(value)
        if not variables:
            self.template_area.grid_remove()
            return

        ttk.Label(self.template_frame, text="テンプレート変数").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        for row, variable in enumerate(variables, start=1):
            ttk.Label(self.template_frame, text=variable, width=18, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=2)
            variable_value = tk.StringVar(value=read_clipboard(self) if variable == "clipboard" else "")
            entry = ttk.Entry(self.template_frame, textvariable=variable_value)
            entry.grid(row=row, column=1, sticky="ew", pady=2)
            if variable == "clipboard":
                entry.configure(state="readonly")
            entry.bind("<Return>", lambda _event: self.copy_prompt() or "break")
            entry.bind("<Tab>", self.focus_next_template_entry)
            entry.bind("<Shift-Tab>", self.focus_previous_template_entry)
            self.template_values[variable] = variable_value
            self.template_entries[variable] = entry
            self.template_entry_order.append(entry)
        self.template_area.grid()

    def focus_next_template_entry(self, _event: tk.Event) -> str:
        if not self.template_entry_order:
            return "break"
        current = self.focus_get()
        try:
            index = self.template_entry_order.index(current)
        except ValueError:
            index = -1
        self.template_entry_order[(index + 1) % len(self.template_entry_order)].focus_set()
        return "break"

    def focus_previous_template_entry(self, _event: tk.Event) -> str:
        if not self.template_entry_order:
            return "break"
        current = self.focus_get()
        try:
            index = self.template_entry_order.index(current)
        except ValueError:
            index = 0
        self.template_entry_order[(index - 1) % len(self.template_entry_order)].focus_set()
        return "break"

    def get_selected_prompt(self) -> PromptSnippet | None:
        return next((prompt for prompt in self.prompts if prompt.id == self.selected_prompt_id), None)

    def create_prompt(self) -> None:
        dialog = PromptEditor(self)
        self.wait_window(dialog)
        if dialog.result:
            category, title, prompt_text, tags = dialog.result
            new_prompt = PromptSnippet.create(category, title, prompt_text)
            new_prompt.tags = tags
            updated_prompts = [*self.prompts, new_prompt]
            if not self.persist(updated_prompts):
                return
            self.prompts = updated_prompts
            self.select_category(category)
            self.selected_prompt_id = new_prompt.id
            self.refresh_prompt_list()
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
            category, title, prompt_text, tags = dialog.result
            updated_prompt = replace(prompt, category=category, title=title, prompt=prompt_text, tags=tags)
            updated_prompts = [updated_prompt if item.id == prompt.id else item for item in self.prompts]
            if not self.persist(updated_prompts):
                return
            self.prompts = updated_prompts
            self.select_category(updated_prompt.category)
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
        updated_prompts = [item for item in self.prompts if item.id != prompt.id]
        if not self.persist(updated_prompts):
            return
        self.prompts = updated_prompts
        self.selected_prompt_id = None
        self.refresh_categories()
        self.select_category("すべて")
        self.show_status("プロンプトを削除しました")

    def toggle_favorite(self) -> None:
        prompt = self.get_selected_prompt()
        if not prompt:
            self.show_status("お気に入りにするプロンプトを選択してください")
            return
        updated_prompt = replace(prompt, favorite=not prompt.favorite)
        updated_prompts = [updated_prompt if item.id == prompt.id else item for item in self.prompts]
        if not self.persist(updated_prompts):
            return
        self.prompts = updated_prompts
        self.refresh_prompt_list()
        self.select_prompt_in_list(prompt.id)
        self.show_status("お気に入りを更新しました")

    def copy_prompt(self) -> None:
        prompt = self.get_selected_prompt()
        if not prompt:
            self.show_status("コピーするプロンプトを選択してください")
            return
        replacement_values = {variable: value.get() for variable, value in self.template_values.items()}
        for variable, value in replacement_values.items():
            if not value.strip():
                self.template_entries[variable].focus_set()
                self.show_status(f"{{{variable}}} を入力してください")
                return
        copied_text = render_template(prompt.prompt, replacement_values)
        self.clipboard_clear()
        self.clipboard_append(copied_text)
        self.update()
        updated_prompt = replace(prompt, use_count=prompt.use_count + 1, last_used_at=datetime.now().isoformat(timespec="seconds"))
        updated_prompts = [updated_prompt if item.id == prompt.id else item for item in self.prompts]
        if not self.persist(updated_prompts):
            self.show_status("クリップボードにコピーしました（使用履歴の保存に失敗しました）")
            return
        self.prompts = updated_prompts
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

    def persist(self, prompts: list[PromptSnippet]) -> bool:
        try:
            self.storage.save(prompts)
            return True
        except StorageError as error:
            messagebox.showerror("保存エラー", str(error), parent=self)
            self.show_status(str(error))
            return False


def main() -> None:
    app = PromptSnippetManager()
    app.mainloop()


if __name__ == "__main__":
    main()
