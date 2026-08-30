import asyncio
from unittest.mock import AsyncMock, MagicMock

from cordesortie.commands.responses import respond


def run(coro):
    return asyncio.run(coro)


def _mock_interaction(*, is_done: bool):
    interaction = MagicMock()
    interaction.response.is_done.return_value = is_done
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


def test_respond_uses_response_send_message_when_not_acknowledged():
    interaction = _mock_interaction(is_done=False)

    run(respond(interaction, "hello"))

    interaction.response.send_message.assert_awaited_once_with("hello", ephemeral=True)
    interaction.followup.send.assert_not_awaited()


def test_respond_falls_back_to_followup_when_already_acknowledged():
    # Regression : Discord peut redelivrer la meme interaction deux fois (rate
    # limit/hoquet gateway) -- le 2e appel a response.send_message() plante
    # avec "Interaction has already been acknowledged" (HTTP 400 40060).
    interaction = _mock_interaction(is_done=True)

    run(respond(interaction, "hello"))

    interaction.followup.send.assert_awaited_once_with("hello", ephemeral=True)
    interaction.response.send_message.assert_not_awaited()


def test_respond_passes_view_through():
    interaction = _mock_interaction(is_done=False)
    view = MagicMock()

    run(respond(interaction, "hello", view=view))

    interaction.response.send_message.assert_awaited_once_with(
        "hello", ephemeral=True, view=view
    )


def test_respond_respects_ephemeral_false():
    interaction = _mock_interaction(is_done=False)

    run(respond(interaction, "hello", ephemeral=False))

    interaction.response.send_message.assert_awaited_once_with("hello", ephemeral=False)
