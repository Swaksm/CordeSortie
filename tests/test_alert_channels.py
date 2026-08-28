import asyncio
from unittest.mock import AsyncMock, MagicMock

from cordesortie.commands.alert_channels import create_alert_channel, slugify


def run(coro):
    return asyncio.run(coro)


def _mock_guild():
    guild = MagicMock()
    guild.categories = []
    guild.create_category = AsyncMock(return_value=MagicMock())
    guild.create_text_channel = AsyncMock(return_value=MagicMock())
    return guild


def test_slugify_stays_under_discord_channel_limit():
    long_name = "a" * 300
    result = slugify(long_name)
    assert len(result) <= 100


def test_slugify_lowercases_and_replaces_special_chars():
    assert slugify("Swaksm Test Filtre !") == "swaksm-test-filtre"


def test_slugify_falls_back_when_empty():
    assert slugify("!!!") == "filtre"


def test_slugify_combined_creator_and_profile_name_stays_under_limit():
    creator = "a" * 50
    profile = "b" * 50
    result = slugify(f"{creator}-{profile}")
    assert len(result) <= 100


def test_create_alert_channel_passes_dict_overwrites_when_public():
    # Regression : discord.py leve TypeError si overwrites=None (guild.py
    # "overwrites parameter expects a dict.") — decouvert en usage reel via
    # /filtre add sur un profil public, jamais teste avant faute de mock ici.
    guild = _mock_guild()
    creator = MagicMock(name="creator")
    creator.name = "swaks"

    run(create_alert_channel(guild, creator=creator, profile_name="test", private=False))

    _, kwargs = guild.create_text_channel.call_args
    assert isinstance(kwargs["overwrites"], dict)
    assert kwargs["overwrites"] == {}


def test_create_alert_channel_sets_overwrites_when_private():
    guild = _mock_guild()
    creator = MagicMock(name="creator")
    creator.name = "swaks"

    run(create_alert_channel(guild, creator=creator, profile_name="test", private=True))

    _, kwargs = guild.create_text_channel.call_args
    assert isinstance(kwargs["overwrites"], dict)
    assert guild.default_role in kwargs["overwrites"]
    assert creator in kwargs["overwrites"]
