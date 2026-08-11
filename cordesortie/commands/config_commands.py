from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ..config import ChannelRole

if TYPE_CHECKING:
    from ..bot import CordeSortieBot


class ConfigCog(commands.Cog):
    config_group = app_commands.Group(
        name="config", description="Configurer CordeSortie sur ce serveur"
    )

    def __init__(self, bot: CordeSortieBot) -> None:
        self.bot = bot

    @config_group.command(
        name="set-channel", description="Assigner un salon (config, alerte ou log)"
    )
    @app_commands.describe(role="Rôle du salon", channel="Salon à assigner")
    @app_commands.default_permissions(manage_guild=True)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        role: ChannelRole,
        channel: discord.TextChannel,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        config = store.load(interaction.guild_id)
        config.channels[role] = channel.id
        store.save(interaction.guild_id, config)

        await interaction.response.send_message(
            f"Salon **{role.value}** défini sur {channel.mention}.", ephemeral=True
        )

    @config_group.command(name="show", description="Afficher la configuration actuelle")
    @app_commands.default_permissions(manage_guild=True)
    async def show(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        config = store.load(interaction.guild_id)

        lines = ["**Configuration CordeSortie**"]
        for role in ChannelRole:
            channel_id = config.channel_id(role)
            lines.append(
                f"- {role.value} : <#{channel_id}>"
                if channel_id
                else f"- {role.value} : _non défini_"
            )
        lines.append(f"- intervalle de log : {config.log_interval_minutes} min")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)
