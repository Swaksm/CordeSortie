import asyncio
from unittest.mock import AsyncMock, MagicMock

from cordesortie.commands.info_channel import cleanup_duplicate_info_channels
from cordesortie.config import GuildConfig


def run(coro):
    return asyncio.run(coro)


def _mock_channel(channel_id: int, name: str = "📊-info-1-filtres"):
    channel = MagicMock()
    channel.id = channel_id
    channel.name = name
    channel.delete = AsyncMock()
    return channel


def _mock_guild(text_channels):
    category = MagicMock()
    category.name = "CordeSortie"
    category.text_channels = text_channels

    guild = MagicMock()
    guild.categories = [category]
    return guild


def test_no_cleanup_needed_with_a_single_info_channel():
    channel = _mock_channel(1)
    guild = _mock_guild([channel])
    config = GuildConfig(info_channel_id=1)
    store = MagicMock()

    deleted = run(cleanup_duplicate_info_channels(guild, config, store, guild_id=42))

    assert deleted == 0
    channel.delete.assert_not_called()
    store.save.assert_not_called()


def test_deletes_duplicates_and_keeps_the_one_referenced_by_config():
    kept = _mock_channel(2, "📊-info-0-filtres")
    duplicate = _mock_channel(3, "📊-info-1-filtres")
    guild = _mock_guild([kept, duplicate])
    config = GuildConfig(info_channel_id=2)
    store = MagicMock()

    deleted = run(cleanup_duplicate_info_channels(guild, config, store, guild_id=42))

    assert deleted == 1
    kept.delete.assert_not_called()
    duplicate.delete.assert_awaited_once()
    store.save.assert_not_called()  # config.info_channel_id already correct


def test_falls_back_to_oldest_channel_when_config_points_nowhere():
    older = _mock_channel(2)
    newer = _mock_channel(3)
    guild = _mock_guild([newer, older])  # ordre arbitraire, pas trié
    config = GuildConfig(info_channel_id=999)  # pointe vers un salon deja supprime
    store = MagicMock()

    deleted = run(cleanup_duplicate_info_channels(guild, config, store, guild_id=42))

    assert deleted == 1
    older.delete.assert_not_called()
    newer.delete.assert_awaited_once()
    assert config.info_channel_id == older.id
    store.save.assert_called_once_with(42, config)
