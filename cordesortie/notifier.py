"""Envoi des alertes (salon dédié par profil), du flux d'évènements en direct et du
résumé périodique (les deux dans le salon log).

Ne fait pas partie de scheduler/ car ce module ne connaît rien à la boucle de
scrape — il reçoit juste "cet item matche ce profil", "voici un évènement à
journaliser" ou "voici les runs récents", et s'occupe de la mise en forme + de
l'envoi Discord.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from .config import ChannelRole, FilterProfile
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


async def get_log_channel(bot: CordeSortieBot, guild: discord.Guild) -> discord.TextChannel | None:
    config = bot.config_store.load(guild.id)
    channel_id = config.channel_id(ChannelRole.LOG)
    if channel_id is None:
        return None
    channel = guild.get_channel(channel_id)
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


def format_log_summary(runs: list) -> str:
    if not runs:
        return "**CordeSortie — log**\n\nAucun scrape depuis le dernier résumé."

    per_site: dict[str, dict[str, int]] = {}
    errors: list[str] = []
    for row in runs:
        site = row["site"]
        stats = per_site.setdefault(site, {"runs": 0, "items": 0, "matched": 0})
        stats["runs"] += 1
        stats["items"] += row["items_found"]
        stats["matched"] += row["matched"]
        if row["error"]:
            errors.append(f"{site} : {row['error']}")

    lines = ["**CordeSortie — log**\n"]
    for site, stats in per_site.items():
        lines.append(
            f"- {site} : {stats['runs']} scrape(s), {stats['items']} item(s) vu(s), "
            f"{stats['matched']} match(s)"
        )
    if errors:
        lines.append("\n**Erreurs**")
        lines.extend(f"- {err}" for err in errors[:10])

    return "\n".join(lines)


async def send_log_summary(channel: discord.TextChannel, runs: list) -> None:
    try:
        await channel.send(format_log_summary(runs))
    except discord.HTTPException:
        logger.warning("Échec d'envoi du résumé log dans %s", channel.id)
