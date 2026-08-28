from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from pydantic import ValidationError

from ..config import DEFAULT_SCRAPE_INTERVAL_MINUTES, FilterProfile
from ..filters import FilterSyntaxError, matches_item, parse_filter
from ..notifier import log_event
from ..scraper import REGISTRY
from ..sites import SUPPORTED_SITES
from .alert_channels import create_alert_channel, delete_alert_channel
from .formatting import format_profile_details, format_profile_line
from .info_channel import update_info_channel

_DRY_RUN_MAX_ITEMS_PER_SITE = 5
_DISCORD_MESSAGE_LIMIT = 1900

if TYPE_CHECKING:
    from ..bot import CordeSortieBot

logger = logging.getLogger("cordesortie")


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
        interval_minutes=(
            f"Intervalle de scrape en minutes (défaut : {DEFAULT_SCRAPE_INTERVAL_MINUTES}, "
            "minimum 1)"
        ),
        private="Salon visible uniquement par toi + les admins (défaut : non, visible par tout le serveur)",
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
        interval_minutes: int | None = None,
        private: bool = False,
    ) -> None:
        interval = interval_minutes if interval_minutes is not None else DEFAULT_SCRAPE_INTERVAL_MINUTES

        if interaction.guild_id is None or interaction.guild is None:
            await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        async with store.lock(interaction.guild_id):
            config = store.load(interaction.guild_id)

            if any(p.name.lower() == name.lower() for p in config.profiles):
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
                    scrape_interval_minutes=interval,
                    price_min=price_min,
                    price_max=price_max,
                    only_available=only_available,
                    private=private,
                )
            except ValidationError as exc:
                await interaction.response.send_message(
                    f"Profil invalide :\n{_format_validation_error(exc)}", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            try:
                channel = await create_alert_channel(
                    interaction.guild,
                    creator=interaction.user,
                    profile_name=name,
                    private=private,
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
                scrape_interval_minutes=interval,
                price_min=price_min,
                price_max=price_max,
                only_available=only_available,
                private=private,
            )
            config.profiles.append(profile)
            store.save(interaction.guild_id, config)

            created_at_str = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
            details = format_profile_details(
                profile, creator_mention=interaction.user.mention, created_at_str=created_at_str
            )
            try:
                info_message = await channel.send(details)
                await info_message.pin()
            except discord.HTTPException:
                logger.warning("Message/épinglage impossible dans le salon %s", channel.id)

            try:
                await update_info_channel(interaction.guild, config, store, interaction.guild_id)
            except discord.HTTPException:
                logger.warning("Mise à jour du salon info impossible")

            try:
                await self.bot.scheduler.refresh_guild(interaction.guild_id)
            except Exception:  # noqa: BLE001 - ne doit jamais laisser l'interaction en suspens
                logger.exception("Échec de refresh_guild pour %s", interaction.guild_id)

            await log_event(
                self.bot,
                interaction.guild,
                f"🆕 Filtre **{name}** créé — sites: {', '.join(site_list)}, "
                f"intervalle {interval} min, par {interaction.user.mention}",
            )

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
        async with store.lock(interaction.guild_id):
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

            try:
                await update_info_channel(interaction.guild, config, store, interaction.guild_id)
            except discord.HTTPException:
                logger.warning("Mise à jour du salon info impossible")

            try:
                await self.bot.scheduler.refresh_guild(interaction.guild_id)
            except Exception:  # noqa: BLE001 - ne doit jamais laisser l'interaction en suspens
                logger.exception("Échec de refresh_guild pour %s", interaction.guild_id)

            await log_event(self.bot, interaction.guild, f"🗑️ Filtre **{name}** supprimé")

            await interaction.response.send_message(
                f"Profil **{name}** supprimé.{note}", ephemeral=True
            )

    @filtre_group.command(name="edit", description="Modifier un profil de filtre existant")
    @app_commands.describe(
        name="Nom du profil à modifier",
        expression="Nouvelle expression de filtre (optionnel, sinon inchangé)",
        sites="Nouveaux sites séparés par des virgules (optionnel, sinon inchangé)",
        price_min="Nouveau prix minimum (optionnel, sinon inchangé)",
        price_max="Nouveau prix maximum (optionnel, sinon inchangé)",
        only_available="N'alerter que si disponible (optionnel, sinon inchangé)",
        interval_minutes="Nouvel intervalle de scrape en minutes (optionnel, sinon inchangé)",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def edit(
        self,
        interaction: discord.Interaction,
        name: str,
        expression: str | None = None,
        sites: str | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        only_available: bool | None = None,
        interval_minutes: int | None = None,
    ) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        if all(
            v is None
            for v in (expression, sites, price_min, price_max, only_available, interval_minutes)
        ):
            await interaction.response.send_message(
                "Aucun changement fourni. Précise au moins un paramètre à modifier.",
                ephemeral=True,
            )
            return

        store = self.bot.config_store
        async with store.lock(interaction.guild_id):
            config = store.load(interaction.guild_id)
            profile = config.get_profile(name)

            if profile is None:
                await interaction.response.send_message(
                    f"Aucun profil nommé **{name}**.", ephemeral=True
                )
                return

            # Note : il n'y a pas moyen d'effacer price_min/price_max via /filtre edit
            # (None signifie "inchangé" ici) — remove + add si besoin de les retirer.
            updated_fields = profile.model_dump()
            if expression is not None:
                updated_fields["filter_expression"] = expression
            if sites is not None:
                updated_fields["sites"] = [
                    s.strip().lower() for s in sites.split(",") if s.strip()
                ]
            if price_min is not None:
                updated_fields["price_min"] = price_min
            if price_max is not None:
                updated_fields["price_max"] = price_max
            if only_available is not None:
                updated_fields["only_available"] = only_available
            if interval_minutes is not None:
                updated_fields["scrape_interval_minutes"] = interval_minutes

            try:
                new_profile = FilterProfile(**updated_fields)
            except ValidationError as exc:
                await interaction.response.send_message(
                    f"Modification invalide :\n{_format_validation_error(exc)}", ephemeral=True
                )
                return

            config.profiles[config.profiles.index(profile)] = new_profile
            store.save(interaction.guild_id, config)

            try:
                await update_info_channel(interaction.guild, config, store, interaction.guild_id)
            except discord.HTTPException:
                logger.warning("Mise à jour du salon info impossible")

            try:
                await self.bot.scheduler.refresh_guild(interaction.guild_id)
            except Exception:  # noqa: BLE001 - ne doit jamais laisser l'interaction en suspens
                logger.exception("Échec de refresh_guild pour %s", interaction.guild_id)

            await log_event(
                self.bot,
                interaction.guild,
                f"✏️ Filtre **{name}** modifié par {interaction.user.mention}",
            )

            await interaction.response.send_message(
                f"Profil **{name}** mis à jour.\n{format_profile_line(new_profile)}",
                ephemeral=True,
            )

    async def _set_paused(
        self, interaction: discord.Interaction, name: str, *, paused: bool
    ) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        async with store.lock(interaction.guild_id):
            config = store.load(interaction.guild_id)
            profile = config.get_profile(name)

            if profile is None:
                await interaction.response.send_message(
                    f"Aucun profil nommé **{name}**.", ephemeral=True
                )
                return

            if profile.paused == paused:
                already = "déjà en pause" if paused else "déjà actif"
                await interaction.response.send_message(
                    f"Profil **{name}** {already}.", ephemeral=True
                )
                return

            config.profiles[config.profiles.index(profile)] = profile.model_copy(
                update={"paused": paused}
            )
            store.save(interaction.guild_id, config)

            try:
                await update_info_channel(interaction.guild, config, store, interaction.guild_id)
            except discord.HTTPException:
                logger.warning("Mise à jour du salon info impossible")

            try:
                await self.bot.scheduler.refresh_guild(interaction.guild_id)
            except Exception:  # noqa: BLE001 - ne doit jamais laisser l'interaction en suspens
                logger.exception("Échec de refresh_guild pour %s", interaction.guild_id)

            verb, emoji = ("mis en pause", "⏸️") if paused else ("repris", "▶️")
            await log_event(self.bot, interaction.guild, f"{emoji} Filtre **{name}** {verb}")

            await interaction.response.send_message(
                f"Profil **{name}** {verb}.", ephemeral=True
            )

    @filtre_group.command(
        name="pause", description="Met en pause un seul profil de filtre (pas tout le bot)"
    )
    @app_commands.describe(name="Nom du profil à mettre en pause")
    @app_commands.default_permissions(manage_guild=True)
    async def pause_filter(self, interaction: discord.Interaction, name: str) -> None:
        await self._set_paused(interaction, name, paused=True)

    @filtre_group.command(name="resume", description="Reprend un profil de filtre en pause")
    @app_commands.describe(name="Nom du profil à reprendre")
    @app_commands.default_permissions(manage_guild=True)
    async def resume_filter(self, interaction: discord.Interaction, name: str) -> None:
        await self._set_paused(interaction, name, paused=False)

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
        lines.extend(format_profile_line(profile) for profile in config.profiles)

        message = "\n".join(lines)
        if len(message) > _DISCORD_MESSAGE_LIMIT:
            message = message[:_DISCORD_MESSAGE_LIMIT] + "\n… (liste tronquée)"

        await interaction.response.send_message(message, ephemeral=True)

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

    @filtre_group.command(
        name="dry-run",
        description="Scraper en direct les sites d'un profil et voir ce qui matche (sans alerter)",
    )
    @app_commands.describe(name="Nom du profil à tester")
    async def dry_run(self, interaction: discord.Interaction, name: str) -> None:
        if interaction.guild_id is None:
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

        await interaction.response.defer(ephemeral=True)

        node = parse_filter(profile.filter_expression)
        lines: list[str] = []
        total_matches = 0

        # Réutilise le navigateur partagé du bot (celui du scheduler) plutôt que
        # d'en relancer un dédié — cohérent avec docs/ARCHITECTURE.md §2.4.
        for site in profile.sites:
            adapter = REGISTRY.get(site)
            if adapter is None:
                lines.append(f"- **{site}** : adapter pas encore disponible")
                continue

            try:
                page = await self.bot.browser.new_page()
                try:
                    items = await adapter.fetch_items(page)
                finally:
                    await page.close()
            except Exception as exc:  # noqa: BLE001 - isole l'échec d'un site
                logger.warning("dry-run : échec du scrape de %s : %s", site, exc)
                lines.append(f"- **{site}** : erreur de scrape ({exc})")
                continue

            matches = [
                item
                for item in items
                if matches_item(
                    node,
                    text=item.text,
                    price=item.price,
                    available=item.available,
                    price_min=profile.price_min,
                    price_max=profile.price_max,
                    only_available=profile.only_available,
                )
            ]
            total_matches += len(matches)
            lines.append(
                f"- **{site}** : {len(items)} item(s) scrapé(s), {len(matches)} match(s)"
            )
            for item in matches[:_DRY_RUN_MAX_ITEMS_PER_SITE]:
                price_str = f"{item.price} €" if item.price is not None else "prix inconnu"
                lines.append(f"  - {item.title} — {price_str} — <{item.url}>")
            if len(matches) > _DRY_RUN_MAX_ITEMS_PER_SITE:
                lines.append(
                    f"  - … et {len(matches) - _DRY_RUN_MAX_ITEMS_PER_SITE} de plus"
                )

        header = f"**Dry-run : {profile.name}** — {total_matches} match(s) au total\n"
        body = "\n".join(lines)
        message = (header + body)[:_DISCORD_MESSAGE_LIMIT]
        await interaction.followup.send(message, ephemeral=True)
