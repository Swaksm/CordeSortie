"""Adapter Ludifolie — sélecteurs relevés manuellement le 2026-08-30 ; à
revalider s'ils cessent de matcher.

PrestaShop avec microdonnées schema.org sur les cartes produit (comme
Auchan) : vraie détection de rupture via `itemprop="availability"`.
"""

from __future__ import annotations

from playwright.async_api import ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..browser import parse_cards_resilient, raise_if_blocked
from ..models import Item

SEARCH_URL = "https://www.ludifolie.com/recherche?controller=search&s=pokemon"
CARD_SELECTOR = ".product-miniature[data-id-product]"


class LudifolieAdapter:
    name = "ludifolie"

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
        item_key = await card.get_attribute("data-id-product")
        if not item_key:
            return None

        link_el = await card.query_selector("a.product-thumbnail")
        href = await link_el.get_attribute("href") if link_el else None
        if not href:
            return None

        title_el = await card.query_selector('[itemprop="name"]')
        title = (await title_el.inner_text()).strip() if title_el else ""
        if not title:
            return None

        image_el = await card.query_selector("img")
        image_url = None
        if image_el is not None:
            image_url = await image_el.get_attribute("data-src") or await image_el.get_attribute(
                "src"
            )

        price = await self._parse_price(card)
        available = await self._parse_availability(card)

        return Item(
            site=self.name,
            item_key=item_key,
            title=title,
            price=price,
            available=available,
            url=href,
            image_url=image_url,
        )

    @staticmethod
    async def _parse_price(card: ElementHandle) -> float | None:
        price_el = await card.query_selector('[itemprop="price"]')
        if price_el is None:
            return None
        text = (await price_el.inner_text()).strip()
        try:
            return float(text)
        except ValueError:
            return None

    @staticmethod
    async def _parse_availability(card: ElementHandle) -> bool:
        avail_el = await card.query_selector('[itemprop="availability"]')
        if avail_el is None:
            return True
        text = (await avail_el.inner_text()).lower()
        return "outofstock" not in text
