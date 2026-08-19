from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class PromptSnippet:
    id: str
    category: str
    title: str
    prompt: str
    tags: list[str] = field(default_factory=list)
    favorite: bool = False
    use_count: int = 0
    last_used_at: str | None = None

    @classmethod
    def create(cls, category: str, title: str, prompt: str) -> "PromptSnippet":
        return cls(id=str(uuid4()), category=category, title=title, prompt=prompt)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptSnippet":
        try:
            use_count = max(0, int(data.get("use_count", 0) or 0))
        except (TypeError, ValueError):
            use_count = 0
        raw_tags = data.get("tags", [])
        return cls(
            id=str(data.get("id") or uuid4()),
            category=str(data.get("category") or "その他"),
            title=str(data.get("title") or "無題"),
            prompt=str(data.get("prompt") or ""),
            tags=[str(tag).strip() for tag in raw_tags if str(tag).strip()] if isinstance(raw_tags, list) else [],
            favorite=bool(data.get("favorite", False)),
            use_count=use_count,
            last_used_at=str(data["last_used_at"]) if data.get("last_used_at") else None,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
