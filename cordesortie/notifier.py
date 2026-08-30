"""Envoi des alertes (salon dédié par profil), du flux d'évènements en direct et du
résumé périodique (les deux dans le salon log).

Ne fait pas partie de scheduler/ car ce module ne connaît rien à la boucle de
scrape — il reçoit juste "cet item matche ce profil", "voici un évènement à
journaliser" ou "voici les runs récents", et s'occupe de la mise en forme + de
l'envoi Discord.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import discord

from .config import FilterProfile
from .scraper import Item

if TYPE_CHECKING:
    from .bot import CordeSortieBot

logger = logging.getLogger("cordesortie")


def build_alert_embed(item: Item, profile: FilterProfile) -> discord.Embed:
    embed = discord.Embed(
        title=item.title,
        url=item.url,
        description=f"Profil : **{profile.name}**",
        color=discord.Color.green(),
    )
    embed.add_field(name="Site", value=item.site, inline=True)
    embed.add_field(
        name="Prix",
        value=f"{item.price} €" if item.price is not None else "inconnu",
        inline=True,
    )
    embed.add_field(name="Disponible", value="Oui" if item.available else "Non", inline=True)
    if item.image_url:
        embed.set_thumbnail(url=item.image_url)
    return embed


_GHOST_PING_COUNT = 5


async def _ghost_ping(channel: discord.TextChannel, user_id: int) -> None:
    """Ping puis supprime immédiatement le message, répété plusieurs fois de
    suite — déclenche une notification mobile/desktop pour le créateur du
    profil sans laisser de mentions traîner dans le salon d'alerte. S'arrête
    au premier échec (rate limit, permission) plutôt que de s'acharner."""
    for _ in range(_GHOST_PING_COUNT):
        try:
            message = await channel.send(f"<@{user_id}>")
            await message.delete()
        except discord.HTTPException:
            logger.warning("Échec du ghost ping pour %s dans %s", user_id, channel.id)
            return


async def send_alert(guild: discord.Guild, profile: FilterProfile, item: Item) -> None:
    channel = guild.get_channel(profile.alert_channel_id)
    if not isinstance(channel, discord.TextChannel):
        logger.warning(
            "Salon d'alerte introuvable pour le profil %s (id=%s)",
            profile.name,
            profile.alert_channel_id,
        )
        return

    try:
        await channel.send(embed=build_alert_embed(item, profile))
    except discord.HTTPException:
        logger.warning("Échec d'envoi de l'alerte pour %s dans %s", profile.name, channel.id)
        return

    # None pour les profils créés avant l'ajout de cette fonctionnalité — on
    # poste quand même l'alerte, juste sans ghost ping (voir config/models.py).
    if profile.creator_id is not None:
        await _ghost_ping(channel, profile.creator_id)


async def get_log_channel(bot: CordeSortieBot, guild: discord.Guild) -> discord.TextChannel | None:
    config = bot.config_store.load(guild.id)
    if config.log_channel_id is None:
        return None
    channel = guild.get_channel(config.log_channel_id)
    return channel if isinstance(channel, discord.TextChannel) else None


async def log_event(bot: CordeSortieBot, guild: discord.Guild, message: str) -> None:
    """Poste un évènement concis et immédiat dans le salon log (création/suppression
    de filtre, résultat d'un cycle de scrape...) — flux en direct, distinct du résumé
    périodique agrégé (`send_log_summary`)."""
    channel = await get_log_channel(bot, guild)
    if channel is None:
        return
    try:
        await channel.send(message)
    except discord.HTTPException:
        logger.warning("Échec d'envoi de l'évènement log dans %s", channel.id)


def _format_since(since: str) -> str:
    # Discord horodate déjà chaque message (donc la fin de la période est
    # implicite), mais le résumé agrège plusieurs cycles en un seul message :
    # sans le début de la période, impossible de savoir sur combien de temps
    # ça porte juste en le relisant plus tard.
    try:
        dt = datetime.fromisoformat(since)
    except ValueError:
        return since
    return dt.strftime("%d/%m %H:%M UTC")


def format_log_summary(runs: list, *, since: str) -> str:
    header = f"**CordeSortie — log** (depuis {_format_since(since)})"

    if not runs:
        return f"{header}\n\nAucun scrape depuis le dernier résumé."

    per_site: dict[str, dict[str, int]] = {}
    # Regroupe les erreurs identiques au lieu de répéter la même ligne jusqu'à
    # 10 fois (ex. un site en panne pendant 2h peut générer des dizaines de
    # runs en erreur avec le même message) — beaucoup plus lisible.
    error_counts: dict[tuple[str, str], int] = {}
    for row in runs:
        site = row["site"]
        stats = per_site.setdefault(site, {"runs": 0, "items": 0, "matched": 0, "errors": 0})
        stats["runs"] += 1
        stats["items"] += row["items_found"]
        stats["matched"] += row["matched"]
        if row["error"]:
            stats["errors"] += 1
            key = (site, row["error"])
            error_counts[key] = error_counts.get(key, 0) + 1

    lines = [f"{header}\n"]
    for site, stats in per_site.items():
        error_suffix = f" — ⚠️ {stats['errors']} erreur(s)" if stats["errors"] else ""
        lines.append(
            f"- **{site}** : {stats['runs']} scrape(s), {stats['items']} item(s) vu(s), "
            f"{stats['matched']} match(s){error_suffix}"
        )

    if error_counts:
        lines.append("\n**Détail des erreurs**")
        top_errors = sorted(error_counts.items(), key=lambda kv: -kv[1])[:10]
        for (site, err), count in top_errors:
            occurrence = f" (x{count})" if count > 1 else ""
            lines.append(f"- **{site}** : `{err}`{occurrence}")

    return "\n".join(lines)


async def send_log_summary(channel: discord.TextChannel, runs: list, *, since: str) -> None:
    try:
        await channel.send(format_log_summary(runs, since=since))
    except discord.HTTPException:
        logger.warning("Échec d'envoi du résumé log dans %s", channel.id)
