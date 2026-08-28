"""Création/suppression des salons d'alerte dédiés à chaque profil de filtre.

Un salon par profil, nommé <pseudo>-<nom du filtre>, regroupé dans une catégorie
"Alertes" dédiée — séparée de la catégorie "CordeSortie" (salons info/aide du bot)
pour ne pas mélanger les alertes avec les salons de pilotage. Visible par tout le
serveur par défaut ; `private=True` le restreint au créateur (+ les admins, qui
voient toujours tout via la permission Administrator, indépendamment des overwrites).
"""

from __future__ import annotations

import logging
import re

import discord

from ..config import GuildConfig

logger = logging.getLogger("cordesortie")

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

    # discord.py exige un dict pour `overwrites` (une TypeError si None) —
    # {} plutôt que d'omettre l'argument : garde le call site uniforme que
    # private soit True ou False.
    overwrites: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {}
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


async def cleanup_orphan_alert_channels(guild: discord.Guild, config: GuildConfig) -> int:
    """Supprime les salons de la catégorie Alertes qui ne correspondent plus à
    aucun profil de filtre de la config actuelle.

    Sans ça, un salon peut rester en permanence si sa suppression a échoué au
    moment d'un `/filtre remove` (permission manquante, erreur Discord
    temporaire) : le profil disparaît de la config mais le salon reste, et rien
    ne revient jamais nettoyer. Appelé à chaque connexion du bot pour que le
    serveur Discord reste toujours cohérent avec la config. Retourne le nombre
    de salons supprimés.
    """
    category = discord.utils.get(guild.categories, name=ALERT_CATEGORY_NAME)
    if category is None:
        return 0

    valid_ids = {profile.alert_channel_id for profile in config.profiles}
    deleted = 0
    for channel in category.channels:
        if channel.id in valid_ids:
            continue
        try:
            await channel.delete(reason="Salon d'alerte orphelin : aucun profil ne le référence")
            deleted += 1
        except discord.HTTPException:
            logger.warning("Impossible de supprimer le salon orphelin %s", channel.id)
    return deleted
