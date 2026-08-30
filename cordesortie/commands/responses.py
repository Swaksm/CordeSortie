"""Réponse Discord robuste face à une interaction déjà acquittée.

Discord peut redélivrer la même interaction de slash command deux fois (rare,
observé en particulier pendant un rate limit ou un hoquet de gateway côté
bot — voir docs/TASKS.md). Le deuxième appel à
`interaction.response.send_message()` échoue alors avec
`discord.errors.HTTPException: 400 ... Interaction has already been
acknowledged` et laisse l'utilisateur sans réponse du tout. `respond()`
détecte ce cas via `interaction.response.is_done()` et bascule automatiquement
sur `interaction.followup.send()`, qui reste valide après un premier ack.
"""

from __future__ import annotations

import discord


async def respond(
    interaction: discord.Interaction,
    content: str,
    *,
    ephemeral: bool = True,
    view: discord.ui.View | None = None,
) -> None:
    kwargs: dict[str, object] = {"ephemeral": ephemeral}
    if view is not None:
        kwargs["view"] = view

    if interaction.response.is_done():
        await interaction.followup.send(content, **kwargs)
    else:
        await interaction.response.send_message(content, **kwargs)
