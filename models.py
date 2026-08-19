from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4


@dataclass
class PromptSnippet:
    id: str
    category: str
    title: str
    prompt: str

    @classmethod
    def create(cls, category: str, title: str, prompt: str) -> "PromptSnippet":
        return cls(id=str(uuid4()), category=category, title=title, prompt=prompt)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptSnippet":
        return cls(
            id=str(data.get("id") or uuid4()),
            category=str(data.get("category") or "その他"),
            title=str(data.get("title") or "無題"),
            prompt=str(data.get("prompt") or ""),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
