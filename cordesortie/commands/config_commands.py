from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from .responses import respond

if TYPE_CHECKING:
    from ..bot import CordeSortieBot

logger = logging.getLogger("cordesortie")


class ConfigCog(commands.Cog):
    config_group = app_commands.Group(
        name="config", description="Configurer CordeSortie sur ce serveur"
    )

    def __init__(self, bot: CordeSortieBot) -> None:
        self.bot = bot

    @config_group.command(
        name="set-log-channel",
        description="Assigner le salon log (flux d'évènements + résumé périodique)",
    )
    @app_commands.describe(channel="Salon à utiliser pour les logs")
    @app_commands.default_permissions(manage_guild=True)
    async def set_log_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        if interaction.guild_id is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        async with store.lock(interaction.guild_id):
            config = store.load(interaction.guild_id)
            config.log_channel_id = channel.id
            store.save(interaction.guild_id, config)

        try:
            await self.bot.scheduler.refresh_guild(interaction.guild_id)
        except Exception:  # noqa: BLE001 - ne doit jamais laisser l'interaction en suspens
            logger.exception("Échec de refresh_guild pour %s", interaction.guild_id)

        await respond(interaction,
            f"Salon log défini sur {channel.mention}.", ephemeral=True
        )

    @config_group.command(name="show", description="Afficher la configuration actuelle")
    @app_commands.default_permissions(manage_guild=True)
    async def show(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        config = store.load(interaction.guild_id)

        lines = ["**Configuration CordeSortie**"]
        lines.append(
            f"- salon log : <#{config.log_channel_id}>"
            if config.log_channel_id
            else "- salon log : _non défini_"
        )
        lines.append(f"- intervalle du résumé périodique : {config.log_interval_minutes} min")
        lines.append(f"- profils de filtre actifs : {len(config.profiles)}")
        lines.append(f"- scraping en pause : {'oui' if self.bot.paused else 'non'}")

        await respond(interaction, "\n".join(lines), ephemeral=True)
