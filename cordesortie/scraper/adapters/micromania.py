"""Adapter Micromania — sélecteurs relevés manuellement le 2026-08-30 ; à
revalider s'ils cessent de matcher.

Salesforce Commerce Cloud avec microdonnées schema.org sur les cartes produit
(comme Auchan/Ludifolie) : vraie détection de rupture via
`link[itemprop="availability"]`.
"""

from __future__ import annotations

from playwright.async_api import ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..browser import parse_cards_resilient, raise_if_blocked
from ..models import Item

SEARCH_URL = (
    "https://www.micromania.fr/on/demandware.store/Sites-Micromania-Site/"
    "fr_FR/Search-Show?q=pokemon"
)
CARD_SELECTOR = ".product-tile[data-pid]"


class MicromaniaAdapter:
    name = "micromania"

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
        item_key = await card.get_attribute("data-pid")
        if not item_key:
            return None

        link_el = await card.query_selector("a.pdp-link")
        if link_el is None:
            return None
        url = await link_el.get_attribute("href")
        title = await link_el.get_attribute("title")
        if not url or not title:
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
            title=title.strip(),
            price=price,
            available=available,
            url=url,
            image_url=image_url,
        )

    @staticmethod
    async def _parse_price(card: ElementHandle) -> float | None:
        price_el = await card.query_selector('[itemprop="price"]')
        if price_el is None:
            return None
        content = await price_el.get_attribute("content")
        if not content:
            return None
        try:
            return float(content)
        except ValueError:
            return None

    @staticmethod
    async def _parse_availability(card: ElementHandle) -> bool:
        avail_el = await card.query_selector('[itemprop="availability"]')
        if avail_el is None:
            return True
        href = (await avail_el.get_attribute("href")) or ""
        return "outofstock" not in href.lower()
