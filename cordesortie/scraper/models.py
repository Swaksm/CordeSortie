from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Item:
    site: str
    item_key: str
    title: str
    price: float | None
    available: bool
    url: str
    image_url: str | None = None
    description: str = field(default="")

    @property
    def text(self) -> str:
        """Texte combiné évalué par le moteur de filtres (contient/ET/OU/NON)."""
        return f"{self.title} {self.description}".strip()
