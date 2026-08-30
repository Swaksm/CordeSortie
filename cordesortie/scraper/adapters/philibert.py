"""Adapter Philibert — sélecteurs relevés manuellement le 2026-08-30 ; à
revalider s'ils cessent de matcher.

VOLONTAIREMENT ABSENT DE REGISTRY (voir scraper/registry.py) : le moteur de
recherche est un widget tiers (Doofinder) qui se re-render de façon
imprévisible pendant la frappe automatisée (`press_sequentially` comme
`page.keyboard.type`), tronquant la requête différemment à chaque tentative
(3/3 essais ratés : "pokem"+"on" séparés, recherche vide, puis "emon" seul).
Le code ci-dessous est celui qui a le mieux marché en test manuel mais reste
non fiable — à retenter si le widget change, pas à réactiver tel quel sans
revalidation.

Prix et disponibilité sont exposés via des attributs `data-*` dédiés
(`data-value`, `data-availability`) plutôt que du texte à parser — ça, en
revanche, a été vérifié fiable une fois la page de résultats obtenue.
"""

from __future__ import annotations

from playwright.async_api import ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..browser import parse_cards_resilient, raise_if_blocked
from ..models import Item

HOME_URL = "https://www.philibertnet.com/fr/"
CARD_SELECTOR = ".dfd-card-live[data-product-id]"


class PhilibertAdapter:
    name = "philibert"

    async def fetch_items(self, page: Page) -> list[Item]:
        await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=30000)
        raise_if_blocked(page, self.name)

        # Le bandeau cookies doit être fermé avant d'interagir avec le champ
        # de recherche, sinon certains clics échouent avec "element is not
        # visible" (overlay au-dessus). #search_query_top (bouton mobile pour
        # révéler la recherche) est caché en desktop — pas besoin d'y cliquer,
        # le champ #search-input est déjà présent dans le DOM.
        try:
            await page.click("button:has-text('Refuser')", timeout=5000)
        except PlaywrightTimeoutError:
            pass

        search_input = page.locator("#search-input")
        await search_input.wait_for(timeout=10000)
        await search_input.press_sequentially("pokemon", delay=50)
        await search_input.press("Enter")

        try:
            await page.wait_for_selector(CARD_SELECTOR, timeout=15000)
        except PlaywrightTimeoutError:
            pass

        cards = await page.query_selector_all(CARD_SELECTOR)
        return await parse_cards_resilient(cards, self._parse_card)

    async def _parse_card(self, card: ElementHandle) -> Item | None:
        item_key = await card.get_attribute("data-product-id")
        if not item_key:
            return None

        link_el = await card.query_selector("[dfd-value-link]")
        url = await link_el.get_attribute("dfd-value-link") if link_el else None
        if not url:
            return None

        title_el = await card.query_selector(".dfd-card-title")
        title = (await title_el.inner_text()).strip() if title_el else ""
        if not title:
            return None

        image_el = await card.query_selector(".dfd-card-thumbnail img")
        image_url = await image_el.get_attribute("src") if image_el else None

        price = await self._parse_price(card)
        available = await self._parse_availability(card)

        return Item(
            site=self.name,
            item_key=item_key,
            title=title,
            price=price,
            available=available,
            url=url,
            image_url=image_url,
        )

    @staticmethod
    async def _parse_price(card: ElementHandle) -> float | None:
        price_el = await card.query_selector(".dfd-card-price")
        if price_el is None:
            return None
        value = await price_el.get_attribute("data-value")
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    async def _parse_availability(card: ElementHandle) -> bool:
        status_el = await card.query_selector("[data-availability]")
        if status_el is None:
            return True
        status = await status_el.get_attribute("data-availability")
        return status == "in-stock"
