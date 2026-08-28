import asyncio
from unittest.mock import AsyncMock, MagicMock

from cordesortie.commands.log_channel import (
    LOG_CHANNEL_BASENAME,
    cleanup_duplicate_log_channels,
    ensure_log_channel,
)
from cordesortie.config import GuildConfig


def run(coro):
    return asyncio.run(coro)


def _mock_channel(channel_id: int, name: str = LOG_CHANNEL_BASENAME):
    channel = MagicMock()
    channel.id = channel_id
    channel.name = name
    channel.delete = AsyncMock()
    return channel


def _mock_guild(text_channels, categories=None):
    category = MagicMock()
    category.name = "CordeSortie"
    category.text_channels = text_channels

    guild = MagicMock()
    guild.categories = categories if categories is not None else [category]
    guild.get_channel = lambda cid: next(
        (c for c in text_channels if c.id == cid), None
    )
    return guild


def test_no_cleanup_needed_with_a_single_log_channel():
    channel = _mock_channel(1)
    guild = _mock_guild([channel])
    config = GuildConfig(log_channel_id=1)
    store = MagicMock()

    deleted = run(cleanup_duplicate_log_channels(guild, config, store, guild_id=42))

    assert deleted == 0
    channel.delete.assert_not_called()
    store.save.assert_not_called()


def test_deletes_duplicate_log_channels_and_keeps_configured_one():
    kept = _mock_channel(2)
    duplicate = _mock_channel(3)
    guild = _mock_guild([kept, duplicate])
    config = GuildConfig(log_channel_id=2)
    store = MagicMock()

    deleted = run(cleanup_duplicate_log_channels(guild, config, store, guild_id=42))

    assert deleted == 1
    duplicate.delete.assert_awaited_once()


def test_ensure_log_channel_creates_one_when_missing():
    guild = _mock_guild([], categories=[])
    category = MagicMock()
    category.name = "CordeSortie"
    guild.categories = [category]
    new_channel = MagicMock()
    new_channel.id = 99
    guild.create_category = AsyncMock(return_value=category)
    guild.create_text_channel = AsyncMock(return_value=new_channel)
    guild.get_channel = lambda cid: None

    config = GuildConfig()
    store = MagicMock()

    channel = run(ensure_log_channel(guild, config, store, guild_id=42))

    assert channel is new_channel
    assert config.log_channel_id == 99
    store.save.assert_called_with(42, config)


def test_ensure_log_channel_reuses_existing_configured_channel():
    existing = _mock_channel(5)
    import discord

    existing.__class__ = discord.TextChannel  # satisfy isinstance check
    guild = _mock_guild([existing])
    guild.create_text_channel = AsyncMock()

    config = GuildConfig(log_channel_id=5)
    store = MagicMock()

    channel = run(ensure_log_channel(guild, config, store, guild_id=42))

    assert channel is existing
    guild.create_text_channel.assert_not_called()
