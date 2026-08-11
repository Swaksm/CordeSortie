"""Adapter Auchan — sélecteurs relevés manuellement le 2026-08-12 ; à revalider
s'ils cessent de matcher.

Auchan utilise des microdonnées schema.org (`itemprop="price"`,
`itemprop="availability"`) sur ses cartes produit — plus fiable à parser qu'un
texte affiché, et une vraie détection de rupture via la classe CSS `outOfStock`
sur la carte.
"""

from __future__ import annotations

from playwright.async_api import ElementHandle, Page

from ..models import Item

SEARCH_URL = "https://www.auchan.fr/recherche?text=pokemon"
BASE_URL = "https://www.auchan.fr"
CARD_SELECTOR = "article.product-thumbnail"


class AuchanAdapter:
    name = "auchan"

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
        item_key = await card.get_attribute("data-id")
        if not item_key:
            return None

        link_el = await card.query_selector("a.product-thumbnail__details-wrapper")
        href = await link_el.get_attribute("href") if link_el else None
        if not href:
            return None
        url = f"{BASE_URL}{href}"

        image_el = await card.query_selector("img[alt]")
        title = await image_el.get_attribute("alt") if image_el else None
        image_url = await image_el.get_attribute("src") if image_el else None
        if not title:
            return None

        price_el = await card.query_selector('meta[itemprop="price"]')
        price = None
        if price_el is not None:
            content = await price_el.get_attribute("content")
            if content:
                try:
                    price = float(content)
                except ValueError:
                    price = None

        class_attr = await card.get_attribute("class") or ""
        available = "outOfStock" not in class_attr

        return Item(
            site=self.name,
            item_key=item_key,
            title=title.strip(),
            price=price,
            available=available,
            url=url,
            image_url=image_url,
        )
