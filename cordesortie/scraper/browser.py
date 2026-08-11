"""Navigateur Chromium partagé entre tous les cycles de scrape.

Un seul contexte de navigateur (cookies, session) réutilisé plutôt que relancer un
navigateur à chaque scrape — c'est la principale optimisation à ne pas sauter, voir
docs/ARCHITECTURE.md §2.4 et docs/RISKS.md §2.
"""

from __future__ import annotations

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from .errors import BlockedError

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

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


class BrowserManager:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
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
