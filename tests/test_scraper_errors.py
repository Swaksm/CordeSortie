from cordesortie.scraper.errors import short_error


def test_short_error_single_line_unchanged():
    assert short_error(ValueError("boom")) == "boom"


def test_short_error_keeps_only_first_line():
    # Regression : les erreurs Playwright ajoutent souvent un bloc "Call log:"
    # de plusieurs lignes (tentatives de retry internes), illisible dans le
    # salon log Discord.
    exc = Exception(
        "ElementHandle.get_attribute: Execution context was destroyed, "
        "most likely because of a navigation\n"
        "Call log:\n"
        "  - waiting for locator(\":scope\")\n"
    )
    result = short_error(exc)
    assert "\n" not in result
    assert result.startswith("ElementHandle.get_attribute")
    assert "Call log" not in result


def test_short_error_truncates_very_long_message():
    exc = Exception("x" * 500)
    result = short_error(exc)
    assert len(result) <= 200


def test_short_error_falls_back_to_class_name_when_message_empty():
    assert short_error(ValueError()) == "ValueError"
