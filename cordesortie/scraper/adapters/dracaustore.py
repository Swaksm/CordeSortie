"""Adapter Dracaustore — sélecteurs relevés manuellement le 2026-08-30 ; à
revalider s'ils cessent de matcher.

Boutique Shopify (thème plus ancien que le Dawn de La Taverne de Dream, mais
même famille de plateforme). Recherche via `/search?type=product&q=...`.

Limitation connue : aucun marqueur de rupture de stock trouvé sur les cartes
de résultats de recherche (pas de badge "Épuisé" observé, même sur un
échantillon de plusieurs dizaines de cartes) — comme Carrefour/Leclerc, tous
les items sont marqués `available=True` (pas de vraie détection de rupture
pour ce site).
"""

from __future__ import annotations

import re

from playwright.async_api import ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..browser import parse_cards_resilient, raise_if_blocked
from ..models import Item

SEARCH_URL = "https://www.dracaustore.fr/search?type=product&q=pokemon"
BASE_URL = "https://www.dracaustore.fr"
CARD_SELECTOR = ".grid-item.search-result"


class DracaustoreAdapter:
    name = "dracaustore"

    async def fetch_items(self, page: Page) -> list[Item]:
        await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_selector(CARD_SELECTOR, timeout=15000)
        except PlaywrightTimeoutError:
            pass
        raise_if_blocked(page, self.name)

        cards = await page.query_selector_all(CARD_SELECTOR)
        return await parse_cards_resilient(cards, self._parse_card)

    async def _parse_card(self, card: ElementHandle) -> Item | None:
        link_el = await card.query_selector("a.product-grid-item")
        href = await link_el.get_attribute("href") if link_el else None
        if not href:
            return None
        path = href.split("?", 1)[0]
        url = f"{BASE_URL}{path}"
        # Le slug d'URL sert de clé stable : pas d'ID numérique exposé sur la
        # carte, mais Shopify ne change pas l'URL d'un produit une fois publié.
        item_key = path.rstrip("/").rsplit("/", 1)[-1]

        title_el = await card.query_selector("p")
        title = (await title_el.inner_text()).strip() if title_el else ""
        if not title:
            return None

        image_el = await card.query_selector("img")
        image_url = None
        if image_el is not None:
            src = await image_el.get_attribute("src")
            if src:
                image_url = f"https:{src}" if src.startswith("//") else src

        price = await self._parse_price(card)

        return Item(
            site=self.name,
            item_key=item_key,
            title=title,
            price=price,
            available=True,
            url=url,
            image_url=image_url,
        )

    @staticmethod
    async def _parse_price(card: ElementHandle) -> float | None:
        price_el = await card.query_selector('small[aria-hidden="true"]')
        if price_el is None:
            return None
        text = (await price_el.inner_text()).strip()
        digits = re.sub(r"[^\d,]", "", text).replace(",", ".")
        try:
            return float(digits)
        except ValueError:
            return None
