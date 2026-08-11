from cordesortie.commands.alert_channels import slugify


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
