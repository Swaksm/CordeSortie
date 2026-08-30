from __future__ import annotations

import asyncio
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
from .expression_builder import (
    DecomposedExpression,
    ExpressionBuilderError,
    build_expression,
    decompose_expression,
)
from .formatting import format_profile_details, format_profile_line
from .info_channel import update_info_channel
from .responses import respond

_DRY_RUN_MAX_ITEMS_PER_SITE = 5
_DISCORD_MESSAGE_LIMIT = 1900
# Garde-fou pour tout le cycle scrape (page + fetch_items + close), même
# raison que scheduler/manager.py::_SCRAPE_TIMEOUT_SECONDS : sans ça, un site
# qui bloque indéfiniment gèlerait scrape_lock pour tous les autres sites, pas
# juste celui-ci.
_SCRAPE_TIMEOUT_SECONDS = 60

if TYPE_CHECKING:
    from ..bot import CordeSortieBot

logger = logging.getLogger("cordesortie")


def _format_validation_error(exc: ValidationError) -> str:
    return "\n".join(f"- {error['msg']}" for error in exc.errors())


class _SiteSelect(discord.ui.Select):
    """Menu déroulant à sélection multiple (cases à cocher côté Discord) —
    remplace la saisie d'une liste de sites séparés par des virgules, source
    d'erreur de frappe/orthographe puisque l'utilisateur ne connaît pas la
    liste exacte des noms de site attendus.

    Ne liste que les sites avec un adapter fonctionnel (REGISTRY), pas
    `SUPPORTED_SITES` en entier : un site sans adapter (ex. Fnac, bloqué par
    CAPTCHA — voir docs/SITES.md) ne renverra jamais d'item, le proposer ici
    ne ferait que créer un profil qui a l'air de marcher mais n'alertera
    jamais. `/sites` reste l'endroit où voir le statut de tous les sites,
    disponibles ou non.
    """

    def __init__(self, preselected: frozenset[str] = frozenset()) -> None:
        options = [
            discord.SelectOption(label=site, value=site, default=site in preselected)
            for site in SUPPORTED_SITES
            if site in REGISTRY
        ]
        super().__init__(
            placeholder="Choisis un ou plusieurs sites à surveiller",
            min_values=1,
            max_values=len(options),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view: _SiteSelectView = self.view  # type: ignore[assignment]
        view.selected_sites = list(self.values)
        await interaction.response.edit_message(
            content=f"Sites sélectionnés : {', '.join(view.selected_sites)}\n"
            "Clique sur **Continuer** pour définir les conditions du filtre.",
            view=view,
        )


class _SiteSelectView(discord.ui.View):
    def __init__(
        self, on_confirm, preselected: list[str] | None = None  # noqa: ANN001
    ) -> None:
        super().__init__(timeout=300)
        # Pré-rempli via `default=True` sur les options (cases déjà cochées) —
        # mais initialisé aussi ici pour le cas où l'utilisateur clique
        # directement sur Continuer sans toucher au menu (callback jamais
        # déclenché, donc jamais mis à jour autrement).
        self.selected_sites: list[str] = list(preselected) if preselected else []
        self.message: discord.Message | None = None
        self._on_confirm = on_confirm
        self.add_item(_SiteSelect(preselected=frozenset(preselected or ())))

    @discord.ui.button(label="Continuer", style=discord.ButtonStyle.primary)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self.selected_sites:
            await respond(interaction,
                "Choisis au moins un site dans le menu avant de continuer.", ephemeral=True
            )
            return
        self.stop()
        await self._on_confirm(interaction, self.selected_sites)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class _FilterConditionsModal(discord.ui.Modal, title="Conditions du filtre"):
    """Formulaire interactif remplaçant la saisie d'une expression en texte
    libre (guillemets/ET/OU/parenthèses) — un mot par ligne dans 3 champs
    séparés, traduits en expression via cordesortie/commands/expression_builder.py.
    Utilisé par `/filtre add` (formulaire vide) et `/filtre edit` (pré-rempli
    via `decompose_expression`, voir `prefill`). Ne couvre pas l'imbrication
    arbitraire de la grammaire (voir `/filtre test` pour composer/valider une
    expression plus complexe à la main), mais couvre le cas d'usage courant
    sans risque de faute de syntaxe.
    """

    # Labels limités à 45 caractères côté Discord (erreur 400 sinon) — le détail
    # "un mot par ligne" est porté par les exemples multi-lignes en placeholder.
    must_all = discord.ui.TextInput(
        label="Doit contenir TOUS ces mots",
        style=discord.TextStyle.paragraph,
        placeholder="pokemon\ncoffret",
        required=False,
        max_length=500,
    )
    any_of = discord.ui.TextInput(
        label="Au moins UN de ces mots (optionnel)",
        style=discord.TextStyle.paragraph,
        placeholder="30 ans\n30 years",
        required=False,
        max_length=500,
    )
    exclude = discord.ui.TextInput(
        label="Ne doit PAS contenir (optionnel)",
        style=discord.TextStyle.paragraph,
        placeholder="peluche",
        required=False,
        max_length=500,
    )

    def __init__(
        self,
        on_submit,  # noqa: ANN001 - callback typé plus bas
        prefill: DecomposedExpression | None = None,
    ) -> None:
        super().__init__()
        self._on_submit = on_submit
        if prefill is not None:
            self.must_all.default = prefill.must_all
            self.any_of.default = prefill.any_of
            self.exclude.default = prefill.exclude

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            expression = build_expression(
                must_all=self.must_all.value,
                any_of=self.any_of.value,
                exclude=self.exclude.value,
            )
        except ExpressionBuilderError as exc:
            await respond(interaction, str(exc), ephemeral=True)
            return

        await self._on_submit(interaction, expression)


class FilterCog(commands.Cog):
    filtre_group = app_commands.Group(
        name="filtre", description="Gérer les profils de filtre CordeSortie"
    )

    def __init__(self, bot: CordeSortieBot) -> None:
        self.bot = bot

    @filtre_group.command(
        name="add",
        description="Créer un profil de filtre (menu + formulaire, rien à taper à la main)",
    )
    @app_commands.describe(
        name="Nom du profil (unique)",
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
        price_min: float | None = None,
        price_max: float | None = None,
        only_available: bool = True,
        interval_minutes: int | None = None,
        private: bool = False,
    ) -> None:
        interval = interval_minutes if interval_minutes is not None else DEFAULT_SCRAPE_INTERVAL_MINUTES

        if interaction.guild_id is None or interaction.guild is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        config = self.bot.config_store.load(interaction.guild_id)
        if any(p.name.lower() == name.lower() for p in config.profiles):
            await respond(interaction,
                f"Un profil nommé **{name}** existe déjà. Supprime-le d'abord avec "
                f"`/filtre remove name:{name}` si tu veux le remplacer.",
                ephemeral=True,
            )
            return

        # Deux étapes interactives avant la création : un menu à cocher pour les
        # sites (évite de deviner l'orthographe exacte), puis un modal pour les
        # conditions du filtre (voir _FilterConditionsModal). Chaque étape est une
        # interaction Discord distincte (menu → clic bouton → soumission modal),
        # donc chacune ne peut avoir qu'une seule réponse initiale.
        async def on_sites_confirmed(
            select_interaction: discord.Interaction, site_list: list[str]
        ) -> None:
            async def on_submit(modal_interaction: discord.Interaction, expression: str) -> None:
                await self._create_profile(
                    modal_interaction,
                    name=name,
                    site_list=site_list,
                    expression=expression,
                    price_min=price_min,
                    price_max=price_max,
                    only_available=only_available,
                    interval=interval,
                    private=private,
                )

            await select_interaction.response.send_modal(_FilterConditionsModal(on_submit))

        view = _SiteSelectView(on_sites_confirmed)
        await respond(interaction,
            "**Étape 1/2** — Choisis les sites à surveiller pour ce profil :",
            view=view,
            ephemeral=True,
        )
        view.message = await interaction.original_response()

    async def _create_profile(
        self,
        interaction: discord.Interaction,
        *,
        name: str,
        site_list: list[str],
        expression: str,
        price_min: float | None,
        price_max: float | None,
        only_available: bool,
        interval: int,
        private: bool,
    ) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        async with store.lock(interaction.guild_id):
            config = store.load(interaction.guild_id)

            if any(p.name.lower() == name.lower() for p in config.profiles):
                await respond(interaction,
                    f"Un profil nommé **{name}** existe déjà. Supprime-le d'abord avec "
                    f"`/filtre remove name:{name}` si tu veux le remplacer.",
                    ephemeral=True,
                )
                return

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
                await respond(interaction,
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
                creator_id=interaction.user.id,
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
                f"Profil **{name}** créé sur {', '.join(site_list)}.\n"
                f"Expression générée : `{expression}`\n"
                f"Alertes dans {channel.mention}.",
                ephemeral=True,
            )

    @filtre_group.command(name="remove", description="Supprimer un profil de filtre")
    @app_commands.describe(name="Nom du profil à supprimer")
    @app_commands.default_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, name: str) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        async with store.lock(interaction.guild_id):
            config = store.load(interaction.guild_id)
            profile = config.get_profile(name)

            if profile is None:
                await respond(interaction,
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

            await respond(interaction,
                f"Profil **{name}** supprimé.{note}", ephemeral=True
            )

    @filtre_group.command(
        name="edit",
        description="Modifier un profil existant (menu + formulaire, pré-remplis)",
    )
    @app_commands.describe(
        name="Nom du profil à modifier",
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
        price_min: float | None = None,
        price_max: float | None = None,
        only_available: bool | None = None,
        interval_minutes: int | None = None,
    ) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        config = self.bot.config_store.load(interaction.guild_id)
        profile = config.get_profile(name)
        if profile is None:
            await respond(interaction,
                f"Aucun profil nommé **{name}**.", ephemeral=True
            )
            return

        # Même flux en 2 étapes que /filtre add, mais menu et formulaire
        # pré-remplis avec les valeurs actuelles du profil : il suffit de
        # cliquer Continuer / soumettre sans rien changer pour ne rien
        # modifier, ou de retoucher juste ce qu'on veut changer.
        prefill = decompose_expression(profile.filter_expression)

        async def on_sites_confirmed(
            select_interaction: discord.Interaction, site_list: list[str]
        ) -> None:
            async def on_submit(modal_interaction: discord.Interaction, expression: str) -> None:
                await self._apply_edit(
                    modal_interaction,
                    name=name,
                    site_list=site_list,
                    expression=expression,
                    price_min=price_min,
                    price_max=price_max,
                    only_available=only_available,
                    interval_minutes=interval_minutes,
                )

            await select_interaction.response.send_modal(
                _FilterConditionsModal(on_submit, prefill=prefill)
            )

        view = _SiteSelectView(on_sites_confirmed, preselected=profile.sites)
        await respond(interaction,
            f"**Étape 1/2** — Sites surveillés par **{name}** :", view=view, ephemeral=True
        )
        view.message = await interaction.original_response()

    async def _apply_edit(
        self,
        interaction: discord.Interaction,
        *,
        name: str,
        site_list: list[str],
        expression: str,
        price_min: float | None,
        price_max: float | None,
        only_available: bool | None,
        interval_minutes: int | None,
    ) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        async with store.lock(interaction.guild_id):
            config = store.load(interaction.guild_id)
            profile = config.get_profile(name)

            if profile is None:
                await respond(interaction,
                    f"Aucun profil nommé **{name}**.", ephemeral=True
                )
                return

            # Sites et expression viennent toujours du menu/formulaire (déjà
            # pré-remplis avec les valeurs actuelles). Note : il n'y a pas
            # moyen d'effacer price_min/price_max ici (None = inchangé pour
            # ces deux champs précis) — remove + add si besoin de les retirer.
            updated_fields = profile.model_dump()
            updated_fields["sites"] = site_list
            updated_fields["filter_expression"] = expression
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
                await respond(interaction,
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

            await respond(interaction,
                f"Profil **{name}** mis à jour.\n{format_profile_line(new_profile)}",
                ephemeral=True,
            )

    async def _set_paused(
        self, interaction: discord.Interaction, name: str, *, paused: bool
    ) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        async with store.lock(interaction.guild_id):
            config = store.load(interaction.guild_id)
            profile = config.get_profile(name)

            if profile is None:
                await respond(interaction,
                    f"Aucun profil nommé **{name}**.", ephemeral=True
                )
                return

            if profile.paused == paused:
                already = "déjà en pause" if paused else "déjà actif"
                await respond(interaction,
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

            await respond(interaction,
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
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        config = store.load(interaction.guild_id)

        if not config.profiles:
            await respond(interaction,
                "Aucun profil de filtre défini pour l'instant.", ephemeral=True
            )
            return

        lines = ["**Profils de filtre**"]
        lines.extend(format_profile_line(profile) for profile in config.profiles)

        message = "\n".join(lines)
        if len(message) > _DISCORD_MESSAGE_LIMIT:
            message = message[:_DISCORD_MESSAGE_LIMIT] + "\n… (liste tronquée)"

        await respond(interaction, message, ephemeral=True)

    @filtre_group.command(
        name="test", description="Tester une expression de filtre sur un texte fictif"
    )
    @app_commands.describe(
        expression='Expression à tester, ex. "pokemon" ET ("30 ans" OU "30 years")',
        texte="Texte fictif d'item (titre + description) à tester contre l'expression",
    )
    async def test(
        self, interaction: discord.Interaction, expression: str, texte: str
    ) -> None:
        try:
            node = parse_filter(expression)
        except FilterSyntaxError as exc:
            await respond(interaction,
                f"Expression invalide : {exc}", ephemeral=True
            )
            return

        # Seule la grammaire texte est testée ici (prix/dispo sont des critères de
        # profil séparés, pas des tokens de l'expression) — voir docs/RISKS.md §3.
        result = matches_item(
            node, text=texte, price=None, available=True, only_available=False
        )

        verdict = "✅ Match" if result else "❌ Pas de match"
        await respond(interaction, verdict, ephemeral=True)

    @filtre_group.command(
        name="dry-run",
        description="Scraper en direct les sites d'un profil et voir ce qui matche (sans alerter)",
    )
    @app_commands.describe(name="Nom du profil à tester")
    async def dry_run(self, interaction: discord.Interaction, name: str) -> None:
        if interaction.guild_id is None:
            await respond(interaction,
                "Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        store = self.bot.config_store
        config = store.load(interaction.guild_id)
        profile = config.get_profile(name)

        if profile is None:
            await respond(interaction,
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

            async def _scrape() -> list:
                page = await self.bot.browser.new_page()
                try:
                    return await adapter.fetch_items(page)
                finally:
                    await page.close()

            try:
                async with self.bot.browser.scrape_lock:
                    items = await asyncio.wait_for(_scrape(), timeout=_SCRAPE_TIMEOUT_SECONDS)
            except TimeoutError:
                logger.warning("dry-run : scrape de %s trop long, abandonné", site)
                lines.append(
                    f"- **{site}** : scrape trop long (>{_SCRAPE_TIMEOUT_SECONDS}s), abandonné"
                )
                continue
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
            if not items:
                # Distinct du cas "0 match" ci-dessous : 0 item veut dire que le
                # site n'a rien renvoyé du tout (site down, adapter cassé...),
                # pas juste que le filtre est strict.
                lines.append(f"- **{site}** : 0 item trouvé")
            elif not matches:
                # Le nombre d'items scrapés est plafonné à une page de résultats
                # (pas de pagination) donc peu informatif ici.
                lines.append(f"- **{site}** : 0 match")
            else:
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
