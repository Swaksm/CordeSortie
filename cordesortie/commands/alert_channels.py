"""Création/suppression des salons d'alerte dédiés à chaque profil de filtre.

Un salon par profil, nommé <pseudo>-<nom du filtre>, regroupé dans une catégorie
"Alertes" dédiée — séparée de la catégorie "CordeSortie" (salons info/aide du bot)
pour ne pas mélanger les alertes avec les salons de pilotage. Visible par tout le
serveur pour l'instant ; une version privée (créateur du filtre + admins
uniquement) est notée en backlog.
"""

from __future__ import annotations

import re

import discord

CATEGORY_NAME = "CordeSortie"
ALERT_CATEGORY_NAME = "Alertes"


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value[:90] or "filtre"


async def get_or_create_category(
    guild: discord.Guild, name: str = CATEGORY_NAME
) -> discord.CategoryChannel:
    existing = discord.utils.get(guild.categories, name=name)
    if existing is not None:
        return existing
    return await guild.create_category(name)


async def create_alert_channel(
    guild: discord.Guild, *, creator_name: str, profile_name: str
) -> discord.TextChannel:
    category = await get_or_create_category(guild, ALERT_CATEGORY_NAME)
    channel_name = slugify(f"{creator_name}-{profile_name}")
    return await guild.create_text_channel(
        channel_name,
        category=category,
        reason=f"Salon d'alerte pour le profil de filtre '{profile_name}'",
    )


async def delete_alert_channel(guild: discord.Guild, channel_id: int) -> bool:
    """Retourne True si le salon a été supprimé, False s'il n'existait déjà plus."""
    channel = guild.get_channel(channel_id)
    if channel is None:
        return False
    await channel.delete(reason="Profil de filtre supprimé")
    return True
