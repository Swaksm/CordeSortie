"""Adapter La Taverne de Dream — sélecteurs relevés manuellement le
2026-08-30 ; à revalider s'ils cessent de matcher.

Boutique Shopify (thème Dawn) : utilise la catégorie Pokémon dédiée plutôt
qu'une recherche plein texte (moins de bruit, catalogue déjà filtré par le
site). Pas de vraie détection de rupture trouvée sur les cartes de la grille —
seulement un badge visuel ("Épuisé"/"Rupture") quand présent : on le détecte
via son texte, sinon `available=True` par défaut (cf. adapter JouéClub).
"""

from __future__ import annotations

import re

from playwright.async_api import ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..browser import parse_cards_resilient, raise_if_blocked
from ..models import Item

SEARCH_URL = "https://latavernededream.com/collections/pokemon-nouveau-site"
BASE_URL = "https://latavernededream.com"
CARD_SELECTOR = "li.grid__item"
_UNAVAILABLE_MARKERS = ("épuisé", "rupture", "sold out")


class LaTaverneDeDreamAdapter:
    name = "latavernededream"

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
        link_el = await card.query_selector("a.full-unstyled-link")
        href = await link_el.get_attribute("href") if link_el else None
        if not href:
            return None
        url = f"{BASE_URL}{href}"
        # Le slug d'URL sert de clé stable : pas d'ID numérique exposé sur la
        # carte, mais Shopify ne change pas l'URL d'un produit une fois publié.
        item_key = href.rstrip("/").rsplit("/", 1)[-1]

        title_el = await card.query_selector(".card__heading")
        title = (await title_el.inner_text()).strip() if title_el else ""
        if not title:
            return None

        image_el = await card.query_selector("img")
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
        # Priorité au prix soldé s'il existe (les deux blocs coexistent dans
        # le DOM du thème Dawn, seul le CSS décide lequel s'affiche).
        price_el = await card.query_selector(".price__sale .price-item--sale")
        if price_el is None:
            price_el = await card.query_selector(".price-item--regular")
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
        badge_el = await card.query_selector(".card__badge")
        if badge_el is None:
            return True
        text = (await badge_el.inner_text()).strip().lower()
        return not any(marker in text for marker in _UNAVAILABLE_MARKERS)
