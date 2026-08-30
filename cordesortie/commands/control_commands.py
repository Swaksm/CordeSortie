from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from .responses import respond

if TYPE_CHECKING:
    from ..bot import CordeSortieBot


class ControlCog(commands.Cog):
    def __init__(self, bot: CordeSortieBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="pause", description="Coupe immédiatement tout scraping (tous sites, tous profils)"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def pause(self, interaction: discord.Interaction) -> None:
        self.bot.paused = True
        await respond(interaction,
            "⏸️ Scraping mis en pause. Utilise `/resume` pour reprendre.", ephemeral=True
        )

    @app_commands.command(name="resume", description="Reprend le scraping après un /pause")
    @app_commands.default_permissions(manage_guild=True)
    async def resume(self, interaction: discord.Interaction) -> None:
        self.bot.paused = False
        await respond(interaction, "▶️ Scraping repris.", ephemeral=True)
