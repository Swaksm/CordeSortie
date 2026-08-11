"""Création/suppression des salons d'alerte dédiés à chaque profil de filtre.

Un salon par profil, nommé <pseudo>-<nom du filtre>, regroupé dans une catégorie
"Alertes" dédiée — séparée de la catégorie "CordeSortie" (salons info/aide du bot)
pour ne pas mélanger les alertes avec les salons de pilotage. Visible par tout le
serveur par défaut ; `private=True` le restreint au créateur (+ les admins, qui
voient toujours tout via la permission Administrator, indépendamment des overwrites).
"""

from __future__ import annotations

import re

import discord

CATEGORY_NAME = "CordeSortie"
ALERT_CATEGORY_NAME = "Alertes"

# Discord limite les noms de salon à 100 caractères ; on garde de la marge pour
# le préfixe pseudo- et un éventuel suffixe de désambiguïsation.
_MAX_SLUG_LENGTH = 90


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value[:_MAX_SLUG_LENGTH] or "filtre"


async def get_or_create_category(
    guild: discord.Guild, name: str = CATEGORY_NAME
) -> discord.CategoryChannel:
    existing = discord.utils.get(guild.categories, name=name)
    if existing is not None:
        return existing
    return await guild.create_category(name)


async def create_alert_channel(
    guild: discord.Guild,
    *,
    creator: discord.Member,
    profile_name: str,
    private: bool = False,
) -> discord.TextChannel:
    category = await get_or_create_category(guild, ALERT_CATEGORY_NAME)
    channel_name = slugify(f"{creator.name}-{profile_name}")

    overwrites = None
    if private:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            creator: discord.PermissionOverwrite(view_channel=True),
        }

    return await guild.create_text_channel(
        channel_name,
        category=category,
        overwrites=overwrites,
        reason=f"Salon d'alerte pour le profil de filtre '{profile_name}'",
    )


async def delete_alert_channel(guild: discord.Guild, channel_id: int) -> bool:
    """Retourne True si le salon a été supprimé, False s'il n'existait déjà plus."""
    channel = guild.get_channel(channel_id)
    if channel is None:
        return False
    await channel.delete(reason="Profil de filtre supprimé")
    return True
