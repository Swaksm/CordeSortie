"""Salon "log" : flux d'évènements en direct (création/suppression de filtre,
résultat de chaque cycle de scrape) + résumé périodique — voir notifier.py.

Auto-créé à la connexion, comme les salons info/aide (voir info_channel.py,
help_channel.py) — plus besoin de lancer `/config set-log-channel` à la main
pour avoir des logs. Cette commande reste disponible pour rediriger vers un
salon existant si l'utilisateur préfère.
"""

from __future__ import annotations

import logging

import discord

from ..config import ConfigStore, GuildConfig
from .alert_channels import CATEGORY_NAME, get_or_create_category

logger = logging.getLogger("cordesortie")

LOG_CHANNEL_BASENAME = "cordesortie-log"


async def cleanup_duplicate_log_channels(
    guild: discord.Guild, config: GuildConfig, store: ConfigStore, guild_id: int
) -> int:
    """Même logique que cleanup_duplicate_info_channels (info_channel.py) :
    supprime les salons log en trop si plusieurs existent (ID stocké pointant
    vers un salon supprimé, ou plusieurs instances du bot ayant tourné en
    parallèle). Le nom du salon log ne change jamais après création, donc un
    simple match par nom exact suffit ici (pas besoin d'une regex comme pour
    le salon info qui se renomme)."""
    category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
    if category is None:
        return 0

    candidates = [c for c in category.text_channels if c.name == LOG_CHANNEL_BASENAME]
    if len(candidates) <= 1:
        return 0

    keep = next((c for c in candidates if c.id == config.log_channel_id), None)
    if keep is None:
        keep = min(candidates, key=lambda c: c.id)

    deleted = 0
    for channel in candidates:
        if channel.id == keep.id:
            continue
        try:
            await channel.delete(reason="Doublon du salon log CordeSortie")
            deleted += 1
        except discord.HTTPException:
            logger.warning("Impossible de supprimer le salon log en double %s", channel.id)

    if config.log_channel_id != keep.id:
        config.log_channel_id = keep.id
        store.save(guild_id, config)

    return deleted


async def ensure_log_channel(
    guild: discord.Guild, config: GuildConfig, store: ConfigStore, guild_id: int
) -> discord.TextChannel:
    """Crée le salon log s'il n'existe pas encore (première connexion, ou salon
    supprimé depuis), sans toucher à un salon déjà configuré/redirigé
    manuellement via `/config set-log-channel`."""
    await cleanup_duplicate_log_channels(guild, config, store, guild_id)

    if config.log_channel_id is not None:
        existing = guild.get_channel(config.log_channel_id)
        if isinstance(existing, discord.TextChannel):
            return existing

    category = await get_or_create_category(guild)
    channel = await guild.create_text_channel(
        LOG_CHANNEL_BASENAME,
        category=category,
        position=2,
        reason="Salon log CordeSortie (créé automatiquement)",
    )
    config.log_channel_id = channel.id
    store.save(guild_id, config)
    return channel
