from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from models import PromptSnippet


DEFAULT_PROMPTS = [
    PromptSnippet(
        id="default-task-check",
        category="開発",
        title="残タスク確認",
        prompt="現在の実装状況を確認し、未実装・未完了のタスクを整理してください。\n重要度と優先度も併せて提示してください。",
    ),
    PromptSnippet(
        id="default-code-review",
        category="開発",
        title="コードレビュー",
        prompt="現在の実装をレビューしてください。\n重大な不具合、保守性の問題、設計上の問題を優先して指摘してください。\n細かい好みレベルの指摘は省略してください。",
    ),
    PromptSnippet(
        id="default-backtest",
        category="EA研究",
        title="バックテスト作成",
        prompt="現在の戦略仕様を確認し、バックテスト可能なコードを作成してください。\n将来的にパラメータ探索できる構成を意識してください。",
    ),
    PromptSnippet(
        id="default-result-evaluation",
        category="EA研究",
        title="結果評価",
        prompt="バックテスト結果を確認し、この戦略に優位性があるか評価してください。\nPF、最大ドローダウン、取引回数、期間別成績などを確認し、\n過学習の可能性も含めて評価してください。",
    ),
    PromptSnippet(
        id="default-improvement",
        category="開発",
        title="改善案",
        prompt="現在のツールを確認し、追加すると有用そうな機能を提案してください。\n実装コストと効果を考慮し、優先順位を付けてください。",
    ),
]


class StorageError(Exception):
    """Raised when prompt data cannot be saved."""


class PromptStorage:
    def __init__(self, path: Path, on_load_error: Callable[[str], None] | None = None):
        self.path = path
        self.on_load_error = on_load_error

    def load(self) -> list[PromptSnippet]:
        if not self.path.exists():
            prompts = [PromptSnippet.from_dict(item.to_dict()) for item in DEFAULT_PROMPTS]
            self.save(prompts)
            return prompts

        try:
            with self.path.open("r", encoding="utf-8") as file:
                raw_data = json.load(file)
            if not isinstance(raw_data, list):
                raise ValueError("JSONのトップレベルは配列である必要があります")
            return [PromptSnippet.from_dict(item) for item in raw_data if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError, ValueError) as error:
            if self.on_load_error:
                self.on_load_error(f"保存データを読み込めませんでした: {error}")
            return []

    def save(self, prompts: list[PromptSnippet]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".tmp")
        try:
            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump([prompt.to_dict() for prompt in prompts], file, ensure_ascii=False, indent=2)
                file.write("\n")
            os.replace(temporary_path, self.path)
        except OSError as error:
            if temporary_path.exists():
                temporary_path.unlink()
            raise StorageError(f"保存に失敗しました: {error}") from error
