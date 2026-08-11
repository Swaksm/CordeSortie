from __future__ import annotations

import logging
from pathlib import Path

import discord
from discord.ext import commands

from .config import ConfigStore

logger = logging.getLogger("cordesortie")


class CordeSortieBot(commands.Bot):
    def __init__(self, *, data_dir: Path | str) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.config_store = ConfigStore(data_dir)

    async def setup_hook(self) -> None:
        from .commands.config_commands import ConfigCog

        await self.add_cog(ConfigCog(self))

    async def on_ready(self) -> None:
        user = self.user
        logger.info("Connecté en tant que %s (id=%s)", user, user.id if user else "?")

        # Sync par serveur (pas de sync globale) : les commandes apparaissent
        # immédiatement au lieu d'attendre jusqu'à une heure côté Discord.
        for guild in self.guilds:
            try:
                synced = await self.tree.sync(guild=guild)
                logger.info("Commandes synchronisées sur %s : %d", guild.name, len(synced))
            except discord.HTTPException:
                logger.exception("Échec de synchronisation des commandes sur %s", guild.name)
