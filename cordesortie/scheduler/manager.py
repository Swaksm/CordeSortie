"""Boucles de scrape (une par site actif et par serveur) + boucle de log.

Une tâche asyncio par (guild, site) — recalculées via refresh_guild() à chaque
mutation de la config (/filtre add|remove) plutôt qu'un polling périodique.
Chaque tâche recharge la config à chaque cycle, donc un changement d'intervalle
ou de profil est pris en compte au tour suivant sans redémarrer la tâche.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ..config.store import ConfigError
from ..filters import FilterSyntaxError, matches_item, parse_filter
from ..notifier import get_log_channel, log_event, send_alert, send_log_summary
from ..scraper import REGISTRY
from ..scraper.errors import BlockedError, short_error

if TYPE_CHECKING:
    from ..bot import CordeSortieBot

logger = logging.getLogger("cordesortie")

# Plancher dur, non contournable via la config — voir docs/PRD.md §3.4 et
# docs/RISKS.md (anti-détection).
_HARD_FLOOR_SECONDS = 60

# Garde-fou pour tout le cycle scrape (page + fetch_items + close) : sans ça,
# un site qui bloque indéfiniment (ex. page.close() qui ne répond jamais après
# une navigation intempestive côté site) gèlerait tout le scheduler pour tous
# les sites, pas juste celui-ci — scrape_lock (browser.py) ne sérialise qu'un
# scrape à la fois, donc un blocage se propagerait à tout le monde.
_SCRAPE_TIMEOUT_SECONDS = 60
_MAX_BACKOFF_MINUTES = 60


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _jitter(base_seconds: float, spread: float = 0.15) -> float:
    return base_seconds * random.uniform(1 - spread, 1 + spread)


def _compute_delay_seconds(
    interval_minutes: int, *, error: bool, consecutive_errors: int
) -> float:
    """Délai avant le prochain cycle. Le plancher dur s'applique dans TOUS les cas,
    y compris en backoff — sans ce `max()`, un backoff sur un intervalle très court
    (ex. 1 min) pourrait redescendre sous 60s une fois le jitter appliqué."""
    if error:
        backoff_minutes = min(
            interval_minutes * (2 ** min(consecutive_errors, 5)), _MAX_BACKOFF_MINUTES
        )
        return max(_HARD_FLOOR_SECONDS, _jitter(backoff_minutes * 60))
    return max(_HARD_FLOOR_SECONDS, _jitter(interval_minutes * 60))


class SchedulerManager:
    def __init__(self, bot: CordeSortieBot) -> None:
        self.bot = bot
        self._site_tasks: dict[tuple[int, str], asyncio.Task] = {}
        self._log_tasks: dict[int, asyncio.Task] = {}

    async def refresh_all(self) -> None:
        for guild in self.bot.guilds:
            try:
                await self.refresh_guild(guild.id)
            except ConfigError:
                logger.exception("Config invalide pour le serveur %s, ignoré", guild.id)

    async def refresh_guild(self, guild_id: int) -> None:
        config = self.bot.config_store.load(guild_id)

        site_intervals: dict[str, int] = {}
        for profile in config.profiles:
            if profile.paused:
                continue
            for site in profile.sites:
                if site not in REGISTRY:
                    continue
                current = site_intervals.get(site)
                site_intervals[site] = (
                    profile.scrape_interval_minutes
                    if current is None
                    else min(current, profile.scrape_interval_minutes)
                )

        for site in site_intervals:
            key = (guild_id, site)
            if key not in self._site_tasks or self._site_tasks[key].done():
                self._site_tasks[key] = asyncio.create_task(self._site_loop(guild_id, site))

        for key in list(self._site_tasks):
            g, site = key
            if g == guild_id and site not in site_intervals:
                self._site_tasks.pop(key).cancel()

        has_log_channel = config.log_channel_id is not None
        log_task = self._log_tasks.get(guild_id)
        if has_log_channel and (log_task is None or log_task.done()):
            self._log_tasks[guild_id] = asyncio.create_task(self._log_loop(guild_id))
        elif not has_log_channel and log_task is not None:
            self._log_tasks.pop(guild_id).cancel()

    async def stop_all(self) -> None:
        for task in [*self._site_tasks.values(), *self._log_tasks.values()]:
            task.cancel()
        self._site_tasks.clear()
        self._log_tasks.clear()

    async def _site_loop(self, guild_id: int, site: str) -> None:
        consecutive_errors = 0
        adapter = REGISTRY[site]

        while True:
            try:
                config = self.bot.config_store.load(guild_id)
            except ConfigError:
                # Config corrompue (édition manuelle ratée, etc.) : on retente au
                # prochain cycle plutôt que de tuer la tâche silencieusement pour
                # toujours (elle ne serait relancée qu'au prochain /filtre add|remove).
                logger.exception("Config invalide pour le serveur %s, nouvelle tentative dans 1 min", guild_id)
                await asyncio.sleep(_HARD_FLOOR_SECONDS)
                continue

            profiles = [p for p in config.profiles if site in p.sites and not p.paused]
            if not profiles:
                return  # plus aucun profil actif ne cible ce site : la tâche s'arrête

            interval_minutes = min(p.scrape_interval_minutes for p in profiles)

            if self.bot.paused:
                await asyncio.sleep(_HARD_FLOOR_SECONDS)
                continue

            guild = self.bot.get_guild(guild_id)
            if guild is None:
                await asyncio.sleep(_HARD_FLOOR_SECONDS)
                continue

            started_at = _now_iso()
            items = []
            error: str | None = None
            async def _scrape() -> list:
                page = await self.bot.browser.new_page()
                try:
                    return await adapter.fetch_items(page)
                finally:
                    await page.close()

            try:
                async with self.bot.browser.scrape_lock:
                    items = await asyncio.wait_for(_scrape(), timeout=_SCRAPE_TIMEOUT_SECONDS)
                consecutive_errors = 0
            except TimeoutError:
                consecutive_errors += 1
                error = f"scrape trop long, abandonné après {_SCRAPE_TIMEOUT_SECONDS}s"
                logger.warning(
                    "Scrape %s trop long (guild %s), abandonné après %ds",
                    site,
                    guild_id,
                    _SCRAPE_TIMEOUT_SECONDS,
                )
            except BlockedError as exc:
                consecutive_errors += 1
                error = short_error(exc)
                logger.warning("Scrape %s bloqué (guild %s) : %s", site, guild_id, exc)
            except Exception as exc:  # noqa: BLE001 - isole l'échec d'un site
                consecutive_errors += 1
                # str(exc) peut inclure un bloc "Call log:" de plusieurs
                # lignes (retries internes Playwright) — illisible dans le
                # salon log Discord. La ligne complète reste dans les logs
                # Python (journalctl) via le %s ci-dessous.
                error = short_error(exc)
                logger.warning("Échec du scrape %s (guild %s) : %s", site, guild_id, exc)

            matched_total = 0
            if error is None:
                # Un parse par profil et par cycle, pas par item — évite de
                # reparser la même expression des dizaines de fois par tour.
                profile_nodes = {}
                for profile in profiles:
                    try:
                        profile_nodes[profile.name] = parse_filter(profile.filter_expression)
                    except FilterSyntaxError:
                        # Ne devrait pas arriver (validé à la création) mais on
                        # n'arrête pas les autres profils pour ça.
                        logger.warning(
                            "Expression invalide pour le profil %s, ignoré ce cycle",
                            profile.name,
                        )

                for item in items:
                    for profile in profiles:
                        node = profile_nodes.get(profile.name)
                        if node is None:
                            continue
                        if not matches_item(
                            node,
                            text=item.text,
                            price=item.price,
                            available=item.available,
                            price_min=profile.price_min,
                            price_max=profile.price_max,
                            only_available=profile.only_available,
                        ):
                            continue

                        result = await self.bot.db.upsert_seen_item(
                            alert_channel_id=profile.alert_channel_id,
                            site=site,
                            item_key=item.item_key,
                            title=item.title,
                            price=item.price,
                            available=item.available,
                        )
                        matched_total += 1
                        if result.should_notify:
                            await send_alert(guild, profile, item)

            await self.bot.db.record_scrape_run(
                site=site,
                started_at=started_at,
                finished_at=_now_iso(),
                items_found=len(items),
                matched=matched_total,
                error=error,
            )

            if error is not None:
                await log_event(self.bot, guild, f"⚠️ **{site}** : erreur — `{error}`")
            elif not items:
                # Distinct du cas "0 match" ci-dessous : 0 item veut dire que le
                # site n'a rien renvoyé du tout (site down, adapter cassé par un
                # changement de structure...), pas juste que le filtre est strict.
                await log_event(self.bot, guild, f"⚠️ **{site}** : 0 item trouvé")
            elif matched_total == 0:
                # Le nombre d'items scrapés est plafonné à une page de résultats
                # (pas de pagination) donc peu informatif ici — seul le fait
                # qu'il y en ait au moins un compte (voir cas précédent).
                await log_event(self.bot, guild, f"🔍 **{site}** : 0 match")
            else:
                await log_event(
                    self.bot,
                    guild,
                    f"🔍 **{site}** : {len(items)} item(s), {matched_total} match(s)",
                )

            delay = _compute_delay_seconds(
                interval_minutes, error=error is not None, consecutive_errors=consecutive_errors
            )
            await asyncio.sleep(delay)

    async def _log_loop(self, guild_id: int) -> None:
        last_check = _now_iso()
        while True:
            try:
                config = self.bot.config_store.load(guild_id)
            except ConfigError:
                logger.exception("Config invalide pour le serveur %s, nouvelle tentative dans 1 min", guild_id)
                await asyncio.sleep(_HARD_FLOOR_SECONDS)
                continue

            if config.log_channel_id is None:
                return  # plus de salon log configuré : la tâche s'arrête

            delay = max(_HARD_FLOOR_SECONDS, _jitter(config.log_interval_minutes * 60))
            await asyncio.sleep(delay)

            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue
            channel = await get_log_channel(self.bot, guild)
            if channel is None:
                continue

            period_start = last_check
            runs = await self.bot.db.runs_since(last_check)
            last_check = _now_iso()
            await send_log_summary(channel, runs, since=period_start)
