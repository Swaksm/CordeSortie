from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from pydantic import ValidationError

from ..config import FilterProfile
from ..filters import FilterSyntaxError, matches_item, parse_filter
from ..sites import SUPPORTED_SITES
from .alert_channels import create_alert_channel, delete_alert_channel

if TYPE_CHECKING:
    from ..bot import CordeSortieBot


def _format_validation_error(exc: ValidationError) -> str:
    return "\n".join(f"- {error['msg']}" for error in exc.errors())


class FilterCog(commands.Cog):
    filtre_group = app_commands.Group(
        name="filtre", description="Gérer les profils de filtre CordeSortie"
    )

    def __init__(self, bot: CordeSortieBot) -> None:
        self.bot = bot

    @filtre_group.command(name="add", description="Créer un profil de filtre")
    @app_commands.describe(
        name="Nom du profil (unique)",
        sites=f"Sites ciblés, séparés par des virgules ({', '.join(SUPPORTED_SITES)})",
        expression='Expression de filtre, ex. contient("30 ans") ET contient("coffret")',
        price_min="Prix minimum (optionnel)",
        price_max="Prix maximum (optionnel)",
        only_available="N'alerter que si l'item est disponible (par défaut : oui)",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def add(
        self,
        interaction: discord.Interaction,
        name: str,
        sites: str,
        expression: str,
        price_min: float | None = None,
        price_max: float | None = None,
        only_available: bool = True,
    ) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        config = store.load(interaction.guild_id)

        if config.get_profile(name) is not None:
            await interaction.response.send_message(
                f"Un profil nommé **{name}** existe déjà. Supprime-le d'abord avec "
                f"`/filtre remove name:{name}` si tu veux le remplacer.",
                ephemeral=True,
            )
            return

        site_list = [s.strip().lower() for s in sites.split(",") if s.strip()]

        # Valide les champs avant de créer quoi que ce soit sur Discord — évite de
        # créer un salon pour un profil qui sera de toute façon rejeté.
        try:
            FilterProfile(
                name=name,
                sites=site_list,
                filter_expression=expression,
                alert_channel_id=0,
                price_min=price_min,
                price_max=price_max,
                only_available=only_available,
            )
        except ValidationError as exc:
            await interaction.response.send_message(
                f"Profil invalide :\n{_format_validation_error(exc)}", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            channel = await create_alert_channel(
                interaction.guild, creator_name=interaction.user.name, profile_name=name
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Je n'ai pas la permission de créer un salon (il me faut "
                "**Gérer les salons**). Profil non créé.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.followup.send(
                f"Échec de création du salon d'alerte : {exc}. Profil non créé.",
                ephemeral=True,
            )
            return

        profile = FilterProfile(
            name=name,
            sites=site_list,
            filter_expression=expression,
            alert_channel_id=channel.id,
            price_min=price_min,
            price_max=price_max,
            only_available=only_available,
        )
        config.profiles.append(profile)
        store.save(interaction.guild_id, config)

        await interaction.followup.send(
            f"Profil **{name}** créé sur {', '.join(site_list)}. "
            f"Alertes dans {channel.mention}.",
            ephemeral=True,
        )

    @filtre_group.command(name="remove", description="Supprimer un profil de filtre")
    @app_commands.describe(name="Nom du profil à supprimer")
    @app_commands.default_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, name: str) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        config = store.load(interaction.guild_id)
        profile = config.get_profile(name)

        if profile is None:
            await interaction.response.send_message(
                f"Aucun profil nommé **{name}**.", ephemeral=True
            )
            return

        config.profiles.remove(profile)
        store.save(interaction.guild_id, config)

        note = ""
        try:
            deleted = await delete_alert_channel(interaction.guild, profile.alert_channel_id)
            if not deleted:
                note = " (le salon d'alerte était déjà supprimé)"
        except discord.Forbidden:
            note = " (permission manquante pour supprimer le salon, à faire manuellement)"
        except discord.HTTPException:
            note = " (erreur lors de la suppression du salon)"

        await interaction.response.send_message(
            f"Profil **{name}** supprimé.{note}", ephemeral=True
        )

    @filtre_group.command(name="list", description="Lister les profils de filtre")
    @app_commands.default_permissions(manage_guild=True)
    async def list_profiles(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        config = store.load(interaction.guild_id)

        if not config.profiles:
            await interaction.response.send_message(
                "Aucun profil de filtre défini pour l'instant.", ephemeral=True
            )
            return

        lines = ["**Profils de filtre**"]
        for profile in config.profiles:
            bounds = []
            if profile.price_min is not None:
                bounds.append(f"prix >= {profile.price_min}")
            if profile.price_max is not None:
                bounds.append(f"prix <= {profile.price_max}")
            bounds_str = f" ({', '.join(bounds)})" if bounds else ""
            dispo = "disponible uniquement" if profile.only_available else "avec rupture"
            lines.append(
                f"- **{profile.name}** — sites: {', '.join(profile.sites)} — "
                f"`{profile.filter_expression}`{bounds_str} — {dispo} — "
                f"<#{profile.alert_channel_id}>"
            )

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @filtre_group.command(
        name="test", description="Tester une expression de filtre sur un texte fictif"
    )
    @app_commands.describe(
        expression='Expression à tester, ex. contient("30 ans") ET contient("coffret")',
        texte="Texte fictif d'item (titre + description) à tester contre l'expression",
    )
    async def test(
        self, interaction: discord.Interaction, expression: str, texte: str
    ) -> None:
        try:
            node = parse_filter(expression)
        except FilterSyntaxError as exc:
            await interaction.response.send_message(
                f"Expression invalide : {exc}", ephemeral=True
            )
            return

        # Seule la grammaire texte est testée ici (prix/dispo sont des critères de
        # profil séparés, pas des tokens de l'expression) — voir docs/RISKS.md §3.
        result = matches_item(
            node, text=texte, price=None, available=True, only_available=False
        )

        verdict = "✅ Match" if result else "❌ Pas de match"
        await interaction.response.send_message(verdict, ephemeral=True)
