import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord

from cordesortie.config import FilterProfile
from cordesortie.notifier import send_alert
from cordesortie.scraper import Item


def run(coro):
    return asyncio.run(coro)


def _mock_channel_guild(channel_id: int = 1):
    channel = MagicMock()
    channel.__class__ = discord.TextChannel  # satisfy isinstance check
    channel.id = channel_id
    channel.send = AsyncMock(return_value=MagicMock(delete=AsyncMock()))

    guild = MagicMock()
    guild.get_channel = lambda cid: channel if cid == channel_id else None
    return guild, channel


def _profile(**overrides):
    fields = dict(
        name="test",
        sites=["auchan"],
        filter_expression='contient("a")',
        alert_channel_id=1,
    )
    fields.update(overrides)
    return FilterProfile(**fields)


def _item():
    return Item(
        site="auchan",
        item_key="1",
        title="Coffret",
        price=10.0,
        available=True,
        url="https://example.test/item",
    )


def test_send_alert_ghost_pings_creator_five_times_when_set():
    guild, channel = _mock_channel_guild()
    profile = _profile(creator_id=999)

    run(send_alert(guild, profile, _item()))

    # 1 embed + 5 ghost pings = 6 envois.
    assert channel.send.await_count == 6
    ping_calls = [c for c in channel.send.await_args_list if not c.kwargs.get("embed")]
    assert len(ping_calls) == 5
    assert all(call.args[0] == "<@999>" for call in ping_calls)
    assert channel.send.return_value.delete.await_count == 5


def test_send_alert_skips_ghost_ping_when_creator_id_none():
    guild, channel = _mock_channel_guild()
    profile = _profile(creator_id=None)

    run(send_alert(guild, profile, _item()))

    assert channel.send.await_count == 1
    channel.send.return_value.delete.assert_not_awaited()


def test_send_alert_does_not_ghost_ping_when_embed_send_fails():
    guild, channel = _mock_channel_guild()
    channel.send = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "boom"))
    profile = _profile(creator_id=999)

    run(send_alert(guild, profile, _item()))

    channel.send.assert_awaited_once()


def test_ghost_ping_stops_early_on_http_exception():
    guild, channel = _mock_channel_guild()
    channel.send = AsyncMock(
        side_effect=[
            MagicMock(delete=AsyncMock()),  # embed
            MagicMock(delete=AsyncMock()),  # ping 1 OK
            discord.HTTPException(MagicMock(), "rate limited"),  # ping 2 fails
        ]
    )
    profile = _profile(creator_id=999)

    run(send_alert(guild, profile, _item()))

    # embed + 1 ping reussi + 1 ping qui echoue = 3 tentatives, pas 6.
    assert channel.send.await_count == 3
