"""Salon "tableau de bord" : un salon tout en haut de la catégorie CordeSortie,
renommé avec le nombre de filtres actifs, avec un message épinglé récapitulant
tous les profils — pour voir l'état du bot d'un coup d'œil."""

from __future__ import annotations

import asyncio
import logging

import discord

from ..config import ConfigStore, GuildConfig
from .alert_channels import CATEGORY_NAME, get_or_create_category
from .formatting import format_info_summary

logger = logging.getLogger("cordesortie")

INFO_CHANNEL_BASENAME = "cordesortie-info"

# discord.py retente automatiquement en interne sur un 429 (rate limit) au lieu de
# lever une exception — sans timeout ici, un renommage rate-limité (Discord limite
# à ~2 renommages de salon / 10 min) bloquerait la commande pendant plusieurs
# minutes. On abandonne le renommage plutôt que d'attendre.
_RENAME_TIMEOUT_SECONDS = 5


def _looks_like_info_channel(name: str) -> bool:
    # Le salon est renommé "📊-info-N-filtres" après sa création (voir
    # update_info_channel) — on ne peut donc pas matcher son nom exact.
    return "info" in name.lower()


async def cleanup_duplicate_info_channels(
    guild: discord.Guild, config: GuildConfig, store: ConfigStore, guild_id: int
) -> int:
    """Supprime les salons tableau de bord en trop s'il y en a plusieurs.

    Peut arriver si `config.info_channel_id` pointe vers un salon supprimé (ou
    si plusieurs instances du bot ont tourné en parallèle par erreur, chacune
    créant le sien sans connaître l'ID déjà utilisé par l'autre — voir
    docs/TASKS.md phase 7). Garde le salon référencé par la config si possible,
    sinon le plus ancien (id Discord = snowflake croissant). Retourne le
    nombre de salons supprimés.
    """
    category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
    if category is None:
        return 0

    candidates = [c for c in category.text_channels if _looks_like_info_channel(c.name)]
    if len(candidates) <= 1:
        return 0

    keep = next((c for c in candidates if c.id == config.info_channel_id), None)
    if keep is None:
        keep = min(candidates, key=lambda c: c.id)

    deleted = 0
    for channel in candidates:
        if channel.id == keep.id:
            continue
        try:
            await channel.delete(reason="Doublon du salon tableau de bord CordeSortie")
            deleted += 1
        except discord.HTTPException:
            logger.warning("Impossible de supprimer le salon info en double %s", channel.id)

    if config.info_channel_id != keep.id:
        config.info_channel_id = keep.id
        config.info_message_id = None  # redétecté/recréé par update_info_channel
        store.save(guild_id, config)

    return deleted


async def _ensure_channel(guild: discord.Guild, config: GuildConfig) -> discord.TextChannel:
    if config.info_channel_id is not None:
        existing = guild.get_channel(config.info_channel_id)
        if isinstance(existing, discord.TextChannel):
            return existing

    category = await get_or_create_category(guild)
    channel = await guild.create_text_channel(
        INFO_CHANNEL_BASENAME,
        category=category,
        position=0,
        reason="Salon tableau de bord CordeSortie",
    )
    config.info_channel_id = channel.id
    config.info_message_id = None
    return channel


async def update_info_channel(
    guild: discord.Guild, config: GuildConfig, store: ConfigStore, guild_id: int
) -> None:
    """Crée/retrouve le salon info, met à jour son nom et son message épinglé.

    Peut lever discord.Forbidden/HTTPException si le bot manque de permissions —
    au caller de décider si ça doit bloquer l'action en cours (ne devrait pas :
    voir usage dans filter_commands.py, où on log un warning sans faire échouer
    /filtre add ou /filtre remove).
    """
    deleted = await cleanup_duplicate_info_channels(guild, config, store, guild_id)
    if deleted:
        logger.info("%d salon(s) tableau de bord en double supprimé(s) sur %s", deleted, guild.name)

    channel = await _ensure_channel(guild, config)

    new_name = f"📊-info-{len(config.profiles)}-filtres"
    if channel.name != new_name:
        try:
            await asyncio.wait_for(
                channel.edit(name=new_name), timeout=_RENAME_TIMEOUT_SECONDS
            )
        except (discord.HTTPException, TimeoutError):
            # Rate limit Discord ou autre échec : pas grave, le nom se remettra à
            # jour au prochain ajout/suppression de filtre.
            logger.warning("Renommage du salon info impossible (rate limit Discord ?)")

    summary = format_info_summary(config)
    message: discord.Message | None = None
    if config.info_message_id is not None:
        try:
            message = await channel.fetch_message(config.info_message_id)
        except discord.NotFound:
            message = None

    if message is not None:
        if message.content != summary:
            await message.edit(content=summary)
    else:
        message = await channel.send(summary)
        try:
            await message.pin()
        except discord.HTTPException:
            logger.warning("Impossible d'épingler le message info (permission manquante ?)")
        config.info_message_id = message.id

    store.save(guild_id, config)
