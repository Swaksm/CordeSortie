"""Navigateur Chromium partagé entre tous les cycles de scrape.

Un seul contexte de navigateur (cookies, session) réutilisé plutôt que relancer un
navigateur à chaque scrape — c'est la principale optimisation à ne pas sauter, voir
docs/ARCHITECTURE.md §2.4 et docs/RISKS.md §2.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from playwright.async_api import (
    Browser,
    BrowserContext,
    ElementHandle,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import Error as PlaywrightError

from .errors import BlockedError

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Coupe tout ce que Chromium fait par défaut mais qui ne sert à rien en scraping
# headless (rendu GPU, sync compte, traduction, télémétrie...) — pensé pour les
# déploiements à mémoire contrainte (ex. Raspberry Pi bas de gamme, voir
# README.md). --disable-dev-shm-usage évite aussi des crashs sur les systèmes
# où /dev/shm est petit (cas fréquent sur Raspberry Pi OS).
_LAUNCH_ARGS = [
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-translate",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--metrics-recording-only",
    "--mute-audio",
    "--no-first-run",
]

# Domaines connus de prestataires de challenge antibot — si l'URL finale d'une
# page en fait partie, on n'a pas eu le contenu attendu mais un CAPTCHA.
_BLOCKED_URL_MARKERS = (
    "captcha-delivery.com",
    "hcaptcha.com",
    "geo.captcha",
    "challenges.cloudflare.com",
)


def raise_if_blocked(page: Page, site: str) -> None:
    if any(marker in page.url for marker in _BLOCKED_URL_MARKERS):
        raise BlockedError(f"{site} : page bloquée par un challenge antibot ({page.url})")


async def parse_cards_resilient[T](
    cards: list[ElementHandle],
    parse_one: Callable[[ElementHandle], Awaitable[T | None]],
) -> list[T]:
    """Parse chaque carte, mais s'arrête et garde ce qui a déjà été extrait si
    le site recharge la page en plein milieu de l'extraction — le contexte JS
    des handles restants devient alors invalide (`playwright.async_api.Error:
    Execution context was destroyed, most likely because of a navigation`).
    Observé en usage réel (rechargement déclenché par une pub/tracker
    tiers) : mieux vaut renvoyer un sous-ensemble d'items que de perdre tout
    le cycle de scrape pour ce site."""
    items: list[T] = []
    for card in cards:
        try:
            item = await parse_one(card)
        except PlaywrightError:
            break
        if item is not None:
            items.append(item)
    return items


class BrowserManager:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        # Sérialise les scrapes (voir scheduler/manager.py et
        # commands/filter_commands.py::dry_run) : sans ça, les boucles par site
        # tournent en parallèle et peuvent ouvrir jusqu'à une page Chromium par
        # site actif en même temps, ce qui multiplie le pic mémoire d'autant sur
        # une machine à mémoire contrainte. Un seul scrape à la fois coûte un
        # peu de latence globale (les sites passent l'un après l'autre plutôt
        # qu'en parallèle) mais plafonne le pic à une seule page ouverte.
        self.scrape_lock = asyncio.Lock()

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True, args=_LAUNCH_ARGS
        )
        self._context = await self._browser.new_context(
            user_agent=USER_AGENT, locale="fr-FR"
        )

    async def stop(self) -> None:
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def new_page(self) -> Page:
        if self._context is None:
            raise RuntimeError("BrowserManager.start() n'a pas été appelé")
        return await self._context.new_page()

    async def __aenter__(self) -> BrowserManager:
        await self.start()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.stop()
