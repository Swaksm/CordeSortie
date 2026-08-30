"""Adapter Comptoir des Écoliers — sélecteurs relevés manuellement le
2026-08-30 ; à revalider s'ils cessent de matcher.

WooCommerce standard : disponibilité directement dans la classe CSS de la
carte (`instock`/`outofstock`), comme la plupart des boutiques WooCommerce.
"""

from __future__ import annotations

import re

from playwright.async_api import ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..browser import parse_cards_resilient, raise_if_blocked
from ..models import Item

SEARCH_URL = "https://comptoirdesecoliers.com/?s=pokemon&post_type=product"
CARD_SELECTOR = "li.product"
_POST_ID_RE = re.compile(r"post-(\d+)")


class ComptoirDesEcoliersAdapter:
    name = "comptoirdesecoliers"

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
        class_attr = await card.get_attribute("class") or ""
        match = _POST_ID_RE.search(class_attr)
        item_key = match.group(1) if match else None
        if not item_key:
            return None

        link_el = await card.query_selector("a.woocommerce-loop-product__link")
        href = await link_el.get_attribute("href") if link_el else None
        if not href:
            return None

        title_el = await card.query_selector(".woocommerce-loop-product__title")
        title = (await title_el.inner_text()).strip() if title_el else ""
        if not title:
            return None

        image_el = await card.query_selector("img")
        image_url = await image_el.get_attribute("src") if image_el else None

        price = await self._parse_price(card)
        available = "outofstock" not in class_attr

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
        # Priorité au prix "ins" (soldé) : en promo, WooCommerce affiche le
        # prix barré (del) avant le prix soldé (ins) dans le DOM.
        price_el = await card.query_selector("ins .amount bdi")
        if price_el is None:
            price_el = await card.query_selector(".price .amount bdi")
        if price_el is None:
            return None
        text = (await price_el.inner_text()).strip()
        digits = re.sub(r"[^\d,]", "", text).replace(",", ".")
        try:
            return float(digits)
        except ValueError:
            return None
