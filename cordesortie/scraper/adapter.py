from __future__ import annotations

from typing import Protocol

from playwright.async_api import Page

from .models import Item


class SiteAdapter(Protocol):
    """Un adapter par site (voir cordesortie/scraper/adapters/) — encapsule l'URL
    de recherche et le parsing DOM propres à ce site. Ne jamais mettre de logique
    spécifique à un site ailleurs qu'ici (voir CLAUDE.md)."""

    name: str

    async def fetch_items(self, page: Page) -> list[Item]: ...
