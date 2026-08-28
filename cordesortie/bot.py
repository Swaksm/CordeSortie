from __future__ import annotations

import logging
from pathlib import Path

import discord
from discord.ext import commands

from .config import ConfigStore
from .scheduler import SchedulerManager
from .scraper import BrowserManager
from .storage import Database

logger = logging.getLogger("cordesortie")


class CordeSortieBot(commands.Bot):
    def __init__(self, *, data_dir: Path | str) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        data_dir = Path(data_dir)
        self.config_store = ConfigStore(data_dir)
        self.db = Database(data_dir / "cordesortie.db")
        self.browser = BrowserManager()
        self.scheduler = SchedulerManager(self)
        self.paused = False

    async def setup_hook(self) -> None:
        await self.db.connect()
        await self.browser.start()

        from .commands.config_commands import ConfigCog
        from .commands.control_commands import ControlCog
        from .commands.filter_commands import FilterCog
        from .commands.site_commands import SiteCog
        from .commands.stats_commands import StatsCog

        await self.add_cog(ConfigCog(self))
        await self.add_cog(FilterCog(self))
        await self.add_cog(ControlCog(self))
        await self.add_cog(SiteCog())
        await self.add_cog(StatsCog(self))

    async def close(self) -> None:
        await self.scheduler.stop_all()
        await self.browser.stop()
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        user = self.user
        logger.info("Connecté en tant que %s (id=%s)", user, user.id if user else "?")

        from .commands.alert_channels import cleanup_orphan_alert_channels
        from .commands.help_channel import update_help_channel
        from .commands.info_channel import update_info_channel

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

            config = self.config_store.load(guild.id)

            try:
                deleted = await cleanup_orphan_alert_channels(guild, config)
                if deleted:
                    logger.info("%d salon(s) d'alerte orphelin(s) supprimé(s) sur %s", deleted, guild.name)
            except discord.HTTPException:
                logger.exception("Échec du nettoyage des salons d'alerte orphelins sur %s", guild.name)

            try:
                await update_info_channel(guild, config, self.config_store, guild.id)
            except discord.HTTPException:
                logger.exception("Échec de mise à jour du salon info sur %s", guild.name)

            try:
                await update_help_channel(guild, config, self.config_store, guild.id, self)
            except discord.HTTPException:
                logger.exception("Échec de mise à jour du salon d'aide sur %s", guild.name)

        # Idempotent : rappeler on_ready après une reconnexion ne duplique pas
        # les tâches déjà en cours (voir SchedulerManager.refresh_guild).
        await self.scheduler.refresh_all()
