"""Adapter Leclerc (e.leclerc) — sélecteurs relevés manuellement le 2026-08-12 ;
à revalider s'ils cessent de matcher.

Limitation connue : pas de marqueur de rupture de stock trouvé sur les cartes de
résultats de recherche — comme Carrefour, tous les items sont marqués
`available=True` (pas de vraie détection de rupture pour ce site).
"""

from __future__ import annotations

import re

from playwright.async_api import ElementHandle, Page

from ..models import Item

SEARCH_URL = "https://www.e.leclerc/recherche?q=pokemon"
BASE_URL = "https://www.e.leclerc"
CARD_SELECTOR = "article[data-product-card]"


class LeclercAdapter:
    name = "leclerc"

    async def fetch_items(self, page: Page) -> list[Item]:
        await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        cards = await page.query_selector_all(CARD_SELECTOR)

        items: list[Item] = []
        for card in cards:
            item = await self._parse_card(card)
            if item is not None:
                items.append(item)
        return items

    async def _parse_card(self, card: ElementHandle) -> Item | None:
        item_key = await card.get_attribute("data-ean")
        if not item_key:
            return None

        title_el = await card.query_selector("a[data-product-card-title]")
        if title_el is None:
            return None

        title = await title_el.get_attribute("title")
        href = await title_el.get_attribute("href")
        if not title or not href:
            return None

        url = f"{BASE_URL}{href}"

        image_el = await card.query_selector("[data-pc-media] img")
        image_url = await image_el.get_attribute("src") if image_el else None

        price = await self._parse_price(card)

        return Item(
            site=self.name,
            item_key=item_key,
            title=title.strip(),
            price=price,
            available=True,
            url=url,
            image_url=image_url,
        )

    @staticmethod
    async def _parse_price(card: ElementHandle) -> float | None:
        # [currency] contient le prix barré (slot="price-striked-content") ET le
        # prix courant : on exclut le premier pour ne garder que le prix affiché.
        price_el = await card.query_selector("[currency] > div:not([slot])")
        if price_el is None:
            return None
        text = (await price_el.inner_text()).strip()
        digits = re.sub(r"[^\d,]", "", text).replace(",", ".")
        try:
            return float(digits)
        except ValueError:
            return None
