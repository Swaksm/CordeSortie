"""Adapter JouéClub — sélecteurs relevés manuellement le 2026-08-12 ; à revalider
s'ils cessent de matcher.

Contrairement à Carrefour, JouéClub affiche une vraie disponibilité en ligne
("Web" vs "En magasin") : on ne retient que le statut "Web" pour `available`.
"""

from __future__ import annotations

import re

from playwright.async_api import ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..browser import raise_if_blocked
from ..models import Item

SEARCH_URL = (
    "https://www.joueclub.fr/contenu/resultat-de-recherche-produits.html"
    "?searchText=pokemon"
)
CARD_SELECTOR = "div.product__content"
_URL_KEY_RE = re.compile(r"-(\d{10,14})\.html$")


class JoueClubAdapter:
    name = "joueclub"

    async def fetch_items(self, page: Page) -> list[Item]:
        await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        # Attend l'apparition d'au moins une carte plutôt qu'un délai fixe, qui
        # peut être trop court sur un CPU lent (ex. Raspberry Pi bas de gamme).
        try:
            await page.wait_for_selector(CARD_SELECTOR, timeout=15000)
        except PlaywrightTimeoutError:
            pass
        raise_if_blocked(page, self.name)

        cards = await page.query_selector_all(CARD_SELECTOR)

        items: list[Item] = []
        for card in cards:
            item = await self._parse_card(card)
            if item is not None:
                items.append(item)
        return items

    async def _parse_card(self, card: ElementHandle) -> Item | None:
        link_el = await card.query_selector("a.product__title-card")
        if link_el is None:
            return None

        href = await link_el.get_attribute("href")
        title = await link_el.get_attribute("title")
        if not href or not title:
            return None

        match = _URL_KEY_RE.search(href)
        item_key = match.group(1) if match else href

        image_el = await card.query_selector(".product__visualContainer img")
        image_url = await image_el.get_attribute("src") if image_el else None

        price = await self._parse_price(card)
        available = await self._parse_availability(card)

        return Item(
            site=self.name,
            item_key=item_key,
            title=title.strip(),
            price=price,
            available=available,
            url=href,
            image_url=image_url,
        )

    @staticmethod
    async def _parse_price(card: ElementHandle) -> float | None:
        price_el = await card.query_selector(".price-value")
        if price_el is None:
            return None
        text = (await price_el.inner_text()).strip()
        digits = re.sub(r"[^\d,]", "", text).replace(",", ".")
        try:
            return float(digits)
        except ValueError:
            return None

    @staticmethod
    async def _parse_availability(card: ElementHandle) -> bool:
        icons = await card.query_selector_all(".product__stockIcon-card")
        for icon in icons:
            text = (await icon.inner_text()).lower()
            if "web" not in text:
                continue
            return "indisponible" not in text
        # Pas d'info de stock trouvée : on suppose disponible plutôt que de
        # masquer un item par excès de prudence.
        return True
