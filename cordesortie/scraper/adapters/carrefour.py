"""Adapter Carrefour — site de validation de l'approche Playwright (voir
docs/SITES.md). Sélecteurs relevés manuellement sur www.carrefour.fr le 2026-08-11 ;
à revalider s'ils cessent de matcher (le site peut changer sa structure sans préavis).

Limitation connue : le moteur de recherche Carrefour exclut par défaut les produits
indisponibles (`displayUnavailable=false` côté API) — tous les items retournés ici
sont donc marqués `available=True`. Pas de vraie détection de rupture pour ce site.
"""

from __future__ import annotations

import re

from playwright.async_api import ElementHandle, Page

from ..browser import raise_if_blocked
from ..models import Item

SEARCH_URL = "https://www.carrefour.fr/s?q=pokemon"
BASE_URL = "https://www.carrefour.fr"
CARD_SELECTOR = "article.product-list-card-plp-grid-new"


class CarrefourAdapter:
    name = "carrefour"

    async def fetch_items(self, page: Page) -> list[Item]:
        await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        # La grille de résultats est peuplée en JS après le chargement initial.
        await page.wait_for_timeout(2000)
        raise_if_blocked(page, self.name)

        cards = await page.query_selector_all(CARD_SELECTOR)

        items: list[Item] = []
        for card in cards:
            item = await self._parse_card(card)
            if item is not None:
                items.append(item)
        return items

    async def _parse_card(self, card: ElementHandle) -> Item | None:
        item_key = await card.get_attribute("data-testid")
        if not item_key:
            return None

        title_el = await card.query_selector(".product-card-title__text")
        title = (await title_el.inner_text()).strip() if title_el else ""
        if not title:
            return None

        link_el = await card.query_selector(
            "a.product-list-card-plp-grid-new__title-container"
        )
        href = await link_el.get_attribute("href") if link_el else None
        url = f"{BASE_URL}{href}" if href else SEARCH_URL

        image_el = await card.query_selector(".product-card-image-new__content")
        image_url = await image_el.get_attribute("src") if image_el else None

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
        amount_el = await card.query_selector(
            '[data-testid="product-price__amount--main"]'
        )
        if amount_el is None:
            return None

        text = (await amount_el.inner_text()).strip()
        digits = re.sub(r"[^\d,]", "", text).replace(",", ".")
        try:
            return float(digits)
        except ValueError:
            return None
