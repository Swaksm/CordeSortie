from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from .responses import respond

if TYPE_CHECKING:
    from ..bot import CordeSortieBot

_MESSAGE_LIMIT = 1900


def _format_scrape_stats(runs: list) -> str:
    if not runs:
        return "Aucun scrape enregistré sur cette période."

    per_site: dict[str, dict[str, int]] = {}
    errors = 0
    for row in runs:
        site = row["site"]
        stats = per_site.setdefault(site, {"runs": 0, "items": 0, "matched": 0})
        stats["runs"] += 1
        stats["items"] += row["items_found"]
        stats["matched"] += row["matched"]
        if row["error"]:
            errors += 1

    lines = [
        f"- **{site}** : {s['runs']} scrape(s), {s['items']} item(s) vu(s), {s['matched']} match(s)"
        for site, s in per_site.items()
    ]
    if errors:
        lines.append(f"- {errors} erreur(s) rencontrée(s) sur la période")
    return "\n".join(lines)


class StatsCog(commands.Cog):
    def __init__(self, bot: CordeSortieBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="stats", description="Statistiques de scraping et d'alertes"
    )
    @app_commands.describe(
        heures="Fenêtre de temps en heures pour les stats de scrape (défaut : 24)"
    )
    async def stats(self, interaction: discord.Interaction, heures: int = 24) -> None:
        if interaction.guild_id is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        config = store.load(interaction.guild_id)

        since = (datetime.now(UTC) - timedelta(hours=heures)).isoformat()
        runs = await self.bot.db.runs_since(since)

        lines = [
            f"**Statistiques — dernières {heures}h**",
            "",
            _format_scrape_stats(runs),
        ]

        if config.profiles:
            lines.append("\n**Alertes par profil (total historique)**")
            for profile in config.profiles:
                count = await self.bot.db.count_seen_items(profile.alert_channel_id)
                lines.append(f"- **{profile.name}** : {count} item(s) matché(s) au total")

        message = "\n".join(lines)
        if len(message) > _MESSAGE_LIMIT:
            message = message[:_MESSAGE_LIMIT] + "\n… (tronqué)"

        await respond(interaction, message, ephemeral=True)
