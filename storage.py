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
    PromptSnippet(
        id="default-requirements",
        category="開発",
        title="要件整理",
        prompt="以下の要望を、目的・機能要件・制約・未確定事項に整理してください。\n不足している情報があれば質問として列挙してください。",
    ),
    PromptSnippet(
        id="default-error-investigation",
        category="開発",
        title="エラー調査",
        prompt="以下のエラーについて、原因の候補、確認すべき箇所、再現手順、修正案を整理してください。\n推測と確認済みの事実を分けて説明してください。",
    ),
    PromptSnippet(
        id="default-test-design",
        category="開発",
        title="テスト設計",
        prompt="この機能に必要なテストケースを洗い出してください。\n正常系・異常系・境界値・回帰テストに分け、優先度も付けてください。",
    ),
    PromptSnippet(
        id="default-explanation",
        category="文章作成",
        title="わかりやすく説明",
        prompt="以下の内容を、前提知識がない人にも伝わるように説明してください。\n重要な用語は簡潔に定義し、具体例を1つ含めてください。",
    ),
    PromptSnippet(
        id="default-rewrite",
        category="文章作成",
        title="文章改善",
        prompt="以下の文章を、意味を変えずに読みやすく改善してください。\n変更点と変更理由も簡潔に示してください。",
    ),
    PromptSnippet(
        id="default-comparison",
        category="その他",
        title="比較検討",
        prompt="以下の選択肢を、目的への適合度・メリット・デメリット・コスト・リスクで比較してください。\n最後に推奨案とその理由を示してください。",
    ),
    PromptSnippet(
        id="default-symbol-review",
        category="開発",
        title="シンボル別コードレビュー",
        prompt="{symbol} の現在の実装をレビューしてください。\n重大な不具合、保守性の問題、設計上の問題を優先して指摘してください。",
        tags=["レビュー", "テンプレート"],
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
            try:
                self.save(prompts)
            except StorageError as error:
                if self.on_load_error:
                    self.on_load_error(str(error))
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
