"""Salon "aide" : documentation de toutes les commandes, générée depuis les
commandes réellement enregistrées dans le bot (pas un texte maintenu à la main —
ne peut donc pas désynchroniser du code). Régénéré à chaque connexion du bot.

Si le contenu dépasse la limite d'un message Discord (2000 caractères), il est
découpé en plusieurs messages épinglés plutôt que tronqué — jamais une commande
coupée au milieu (le découpage se fait entre deux blocs de commande)."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from ..config import ConfigStore, GuildConfig
from .alert_channels import get_or_create_category

logger = logging.getLogger("cordesortie")

HELP_CHANNEL_BASENAME = "cordesortie-aide"
_MESSAGE_LIMIT = 1900
_HEADER = "**CordeSortie — commandes disponibles**"
_CONTINUATION_HEADER = "**CordeSortie — commandes (suite)**"

# Bloc statique (pas généré depuis les commandes, contrairement au reste de ce
# fichier) : les paramètres `expression` des commandes /filtre expliquent la
# syntaxe en une ligne, mais un exemple posé avec du texte autour est plus
# facile à suivre pour un premier filtre que de la déduire depuis 3 commandes
# différentes.
_FILTER_SYNTAX_GUIDE = """**🔎 Créer un filtre — comment ça marche**

`/filtre add` te guide en 2 étapes, sans rien taper à la main pour la partie
piège :
1. Un **menu à cocher** pour choisir les sites à surveiller (fini les fautes
   de frappe sur le nom d'un site).
2. Un **formulaire** avec 3 champs, un mot-clé par ligne :
> **Doit contenir TOUS ces mots** — ex. `pokemon`
> **Au moins UN de ces mots** (optionnel) — ex. `30 ans` puis `30 years` sur
> une autre ligne
> **Ne doit PAS contenir** (optionnel) — ex. `peluche`

Le bot combine tout ça automatiquement en une expression valide. Pas de
guillemets, ET/OU/NON ou parenthèses à taper toi-même.

`/filtre edit` fonctionne pareil, en pré-remplissant le menu et le formulaire
avec les valeurs actuelles du profil : clique juste Continuer/Valider sans
rien changer pour ne rien modifier, ou ajuste ce que tu veux changer.

**Pour aller plus loin** (`/filtre test`, pour composer/valider une expression
plus complexe à la main sans créer de profil) — même logique, écrite en
texte libre :
> `"pokemon"` → contient "pokemon"
> `"pokemon" ET "coffret"` → doit contenir les deux
> `("pokemon" OU "poke") ET ("30 ans" OU "30 years")` → parenthèses
> obligatoires dès que tu mélanges ET et OU (sinon le bot refuse, pour éviter
> toute ambiguïté)
> `"pokemon" ET NON "peluche"` → exclut un mot"""


def _generate_command_blocks(bot: commands.Bot) -> list[str]:
    leaf_commands = sorted(
        (c for c in bot.tree.walk_commands() if isinstance(c, app_commands.Command)),
        key=lambda c: c.qualified_name,
    )
    blocks = []
    for command in leaf_commands:
        lines = [f"**/{command.qualified_name}**", command.description or "_(pas de description)_"]
        for param in command.parameters:
            required = "requis" if param.required else "optionnel"
            lines.append(f"- `{param.name}` ({required}) : {param.description}")
        blocks.append("\n".join(lines))
    return blocks


def _chunk_docs(blocks: list[str]) -> list[str]:
    """Regroupe les blocs de commande en messages ≤ _MESSAGE_LIMIT, sans jamais
    couper un bloc entre deux messages."""
    chunks: list[str] = []
    current = [_HEADER]
    current_len = len(_HEADER)

    for block in blocks:
        added_len = len(block) + 2  # + séparateur "\n\n"
        if current_len + added_len > _MESSAGE_LIMIT and len(current) > 1:
            chunks.append("\n\n".join(current))
            current = [_CONTINUATION_HEADER]
            current_len = len(_CONTINUATION_HEADER)
        current.append(block)
        current_len += added_len

    if len(current) > 1 or not chunks:
        chunks.append("\n\n".join(current))
    return chunks


async def _ensure_channel(guild: discord.Guild, config: GuildConfig) -> discord.TextChannel:
    if config.help_channel_id is not None:
        existing = guild.get_channel(config.help_channel_id)
        if isinstance(existing, discord.TextChannel):
            return existing

    category = await get_or_create_category(guild)
    channel = await guild.create_text_channel(
        HELP_CHANNEL_BASENAME,
        category=category,
        position=1,
        reason="Salon documentation des commandes CordeSortie",
    )
    config.help_channel_id = channel.id
    config.help_message_ids = []
    return channel


async def update_help_channel(
    guild: discord.Guild,
    config: GuildConfig,
    store: ConfigStore,
    guild_id: int,
    bot: commands.Bot,
) -> None:
    channel = await _ensure_channel(guild, config)
    chunks = _chunk_docs([_FILTER_SYNTAX_GUIDE, *_generate_command_blocks(bot)])
    existing_ids = list(config.help_message_ids)
    new_ids: list[int] = []

    for i, chunk_content in enumerate(chunks):
        message: discord.Message | None = None
        if i < len(existing_ids):
            try:
                message = await channel.fetch_message(existing_ids[i])
            except discord.NotFound:
                message = None

        if message is not None:
            if message.content != chunk_content:
                await message.edit(content=chunk_content)
            new_ids.append(message.id)
            continue

        message = await channel.send(chunk_content)
        try:
            await message.pin()
        except discord.HTTPException:
            logger.warning("Impossible d'épingler le message d'aide (permission manquante ?)")
        new_ids.append(message.id)

    # Le nombre de messages a diminué (commandes retirées) : nettoie les restes.
    for stale_id in existing_ids[len(chunks) :]:
        try:
            stale = await channel.fetch_message(stale_id)
            await stale.delete()
        except discord.NotFound:
            pass
        except discord.HTTPException:
            logger.warning("Impossible de supprimer l'ancien message d'aide %s", stale_id)

    config.help_message_ids = new_ids
    store.save(guild_id, config)
