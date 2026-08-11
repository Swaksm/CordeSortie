from __future__ import annotations

import logging
from pathlib import Path

import discord
from discord.ext import commands

from .config import ConfigStore
from .storage import Database

logger = logging.getLogger("cordesortie")


class CordeSortieBot(commands.Bot):
    def __init__(self, *, data_dir: Path | str) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        data_dir = Path(data_dir)
        self.config_store = ConfigStore(data_dir)
        self.db = Database(data_dir / "cordesortie.db")

    async def setup_hook(self) -> None:
        await self.db.connect()

        from .commands.config_commands import ConfigCog
        from .commands.filter_commands import FilterCog

        await self.add_cog(ConfigCog(self))
        await self.add_cog(FilterCog(self))

    async def close(self) -> None:
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        user = self.user
        logger.info("Connecté en tant que %s (id=%s)", user, user.id if user else "?")

        # Copie les commandes globales vers chaque serveur puis sync sur ce
        # serveur précis : les commandes apparaissent immédiatement, au lieu
        # d'attendre jusqu'à une heure pour une sync globale côté Discord.
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info("Commandes synchronisées sur %s : %d", guild.name, len(synced))
            except discord.HTTPException:
                logger.exception("Échec de synchronisation des commandes sur %s", guild.name)
