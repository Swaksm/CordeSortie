from cordesortie.config import FilterProfile


def test_filter_profile_private_and_paused_default_false():
    profile = FilterProfile(
        name="n", sites=["auchan"], filter_expression='contient("a")', alert_channel_id=1
    )
    assert profile.private is False
    assert profile.paused is False


def test_filter_profile_can_set_private_and_paused():
    profile = FilterProfile(
        name="n",
        sites=["auchan"],
        filter_expression='contient("a")',
        alert_channel_id=1,
        private=True,
        paused=True,
    )
    assert profile.private is True
    assert profile.paused is True
