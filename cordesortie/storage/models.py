"""Structures de données pour le stockage — pas les Item du scraper (Phase 4),
juste ce qui est nécessaire pour la dédup et le suivi des runs de scrape."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SeenItem:
    site: str
    item_key: str
    title: str
    price: float | None
    available: bool
    first_seen_at: str
    last_seen_at: str


@dataclass(frozen=True, slots=True)
class UpsertResult:
    """Résultat d'un upsert dans seen_items — dit au caller s'il faut notifier."""

    is_new: bool
    changed: bool

    @property
    def should_notify(self) -> bool:
        return self.is_new or self.changed
