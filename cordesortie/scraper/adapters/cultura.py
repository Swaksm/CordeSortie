"""Adapter Cultura — sélecteurs relevés manuellement le 2026-08-28 ; à revalider
s'ils cessent de matcher.

Cultura vend aussi via des vendeurs partenaires (marketplace) en plus de son
propre stock : on ne retient que le prix Cultura lui-même (`div.price`), pas
le "+N neufs dès X€" du marketplace qui peut être plus élevé et n'a aucune
raison d'être au prix constructeur.

La disponibilité vient du texte affiché sur la carte ("en stock Cultura",
"Précommande - sortie le ...", "Dispo sous N jours en ligne") : une précommande
ou un article disponible sous délai comptent comme "disponibles" au même titre
qu'un article en stock immédiat — l'utilisateur veut être alerté dès qu'il peut
commander l'item, pas seulement quand il est déjà en rayon. Seul un texte
signalant explicitement une rupture ("épuisé", "rupture", "indisponible") est
traité comme non disponible.
"""

from __future__ import annotations

import re

from playwright.async_api import ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..browser import raise_if_blocked
from ..models import Item

SEARCH_URL = "https://www.cultura.com/search/results?search_query=pokemon"
BASE_URL = "https://www.cultura.com"
CARD_SELECTOR = "article.one-card--product"


class CulturaAdapter:
    name = "cultura"

    async def fetch_items(self, page: Page) -> list[Item]:
        await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        # Les résultats sont peuplés en JS après le chargement initial : on
        # attend qu'au moins une carte apparaisse plutôt qu'un délai fixe, qui
        # peut être trop court sur un CPU lent (ex. Raspberry Pi bas de gamme)
        # et faire remonter "0 item trouvé" à tort. Si rien n'apparaît dans le
        # temps imparti, `cards` sera juste vide (0 vrai résultat ou page
        # anormalement lente ce cycle-ci) — pas une erreur en soi.
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
        item_key = await card.get_attribute("data-product-sku")
        if not item_key:
            return None

        link_el = await card.query_selector("a.one-product")
        href = await link_el.get_attribute("href") if link_el else None
        if not href:
            return None
        url = f"{BASE_URL}{href}"

        title_el = await card.query_selector(".one-product__desc__name")
        title = (await title_el.inner_text()).strip() if title_el else ""
        if not title:
            return None

        image_el = await card.query_selector(".one-product__img img")
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
        price_el = await card.query_selector(".price")
        if price_el is None:
            return None
        text = (await price_el.inner_text()).strip()
        digits = re.sub(r"[^\d,]", "", text).replace(",", ".")
        try:
            return float(digits)
        except ValueError:
            return None

    _UNAVAILABLE_MARKERS = ("épuisé", "rupture", "indisponible")

    async def _parse_availability(self, card: ElementHandle) -> bool:
        stock_el = await card.query_selector(".stock.color-green")
        if stock_el is None:
            # Pas d'info de stock trouvée : on suppose disponible plutôt que de
            # masquer un item par excès de prudence (cf. adapter JouéClub).
            return True
        text = (await stock_el.inner_text()).strip().lower()
        # "en stock", "précommande" et "dispo sous N jours" comptent tous comme
        # disponibles (l'item est commandable maintenant) — seule une mention
        # explicite de rupture est traitée comme non disponible.
        return not any(marker in text for marker in self._UNAVAILABLE_MARKERS)
