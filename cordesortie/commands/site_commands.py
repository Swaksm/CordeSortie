from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..scraper import REGISTRY
from ..sites import SITE_NOTES, SUPPORTED_SITES


class SiteCog(commands.Cog):
    @app_commands.command(
        name="sites", description="Lister les sites supportés et leur statut"
    )
    async def sites(self, interaction: discord.Interaction) -> None:
        lines = ["**Sites supportés**"]
        for site in SUPPORTED_SITES:
            status = "✅ disponible" if site in REGISTRY else "⏳ pas encore disponible"
            note = SITE_NOTES.get(site)
            suffix = f" — {note}" if note else ""
            lines.append(f"- **{site}** : {status}{suffix}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)
