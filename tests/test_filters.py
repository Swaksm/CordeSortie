import pytest

from cordesortie.filters import FilterSyntaxError, matches_item, parse_filter


def test_simple_contains_match():
    node = parse_filter('contient("coffret")')
    assert matches_item(node, text="Coffret 30 ans", price=50, available=True)


def test_simple_contains_no_match():
    node = parse_filter('contient("booster")')
    assert not matches_item(node, text="Coffret 30 ans", price=50, available=True)


def test_contains_is_case_insensitive():
    node = parse_filter('contient("COFFRET")')
    assert matches_item(node, text="coffret 30 ans", price=50, available=True)


def test_contains_is_accent_insensitive():
    # Les sites marchands orthographient "pokemon"/"Pokémon" de façon
    # incohérente d'une fiche produit à l'autre — le filtre doit ignorer
    # l'accent dans les deux sens.
    node_no_accent = parse_filter('contient("pokemon")')
    assert matches_item(node_no_accent, text="Coffret Pokémon", price=50, available=True)

    node_with_accent = parse_filter('contient("pokémon")')
    assert matches_item(node_with_accent, text="Coffret Pokemon", price=50, available=True)


def test_and():
    node = parse_filter('contient("30") ET contient("ans")')
    assert matches_item(node, text="Coffret 30 ans", price=50, available=True)
    assert not matches_item(node, text="Coffret 25 ans", price=50, available=True)


def test_or():
    node = parse_filter('contient("30") OU contient("ans")')
    assert matches_item(node, text="Coffret 30", price=50, available=True)
    assert matches_item(node, text="Coffret ans", price=50, available=True)
    assert not matches_item(node, text="Coffret rien", price=50, available=True)


def test_not():
    node = parse_filter('NON contient("epuise")')
    assert matches_item(node, text="Coffret 30 ans", price=50, available=True)
    assert not matches_item(node, text="Coffret epuise", price=50, available=True)


def test_parentheses_and_nesting():
    node = parse_filter('(contient("30") OU contient("ans")) ET contient("coffret")')
    assert matches_item(node, text="Coffret 30", price=50, available=True)
    assert matches_item(node, text="Coffret ans", price=50, available=True)
    assert not matches_item(node, text="Booster 30", price=50, available=True)
    assert not matches_item(node, text="Coffret hors sujet", price=50, available=True)


def test_mixing_and_or_without_parens_is_rejected():
    with pytest.raises(FilterSyntaxError):
        parse_filter('contient("30") OU contient("ans") ET contient("coffret")')


def test_bare_string_is_shorthand_for_contains():
    node = parse_filter('"coffret"')
    assert matches_item(node, text="Coffret 30 ans", price=50, available=True)
    assert not matches_item(node, text="Booster 30 ans", price=50, available=True)


def test_bare_strings_combined_with_and_or_and_parens():
    node = parse_filter('("POKEMON" OU "Poke") ET ("30 ans" OU "30 years")')
    assert matches_item(node, text="Coffret Poke 30 years special", price=10, available=True)
    assert matches_item(node, text="Pokemon coffret 30 ans", price=10, available=True)
    assert not matches_item(node, text="Coffret 30 ans", price=10, available=True)
    assert not matches_item(node, text="Pokemon coffret", price=10, available=True)


def test_bare_string_and_contains_syntax_are_interchangeable():
    node = parse_filter('"pokemon" ET contient("coffret")')
    assert matches_item(node, text="Pokemon coffret", price=10, available=True)
    assert not matches_item(node, text="Pokemon booster", price=10, available=True)


def test_case_insensitive_keywords():
    node = parse_filter('contient("30") et contient("ans")')
    assert matches_item(node, text="Coffret 30 ans", price=50, available=True)


def test_unknown_keyword_raises():
    with pytest.raises(FilterSyntaxError):
        parse_filter('contient("30") XOR contient("ans")')


def test_unclosed_paren_raises():
    with pytest.raises(FilterSyntaxError):
        parse_filter('(contient("30")')


def test_empty_expression_raises():
    with pytest.raises(FilterSyntaxError):
        parse_filter("")


def test_matches_item_respects_only_available():
    node = parse_filter('contient("coffret")')
    assert not matches_item(node, text="Coffret", price=50, available=False)
    assert matches_item(
        node, text="Coffret", price=50, available=False, only_available=False
    )


def test_matches_item_respects_price_bounds():
    node = parse_filter('contient("coffret")')
    assert matches_item(node, text="Coffret", price=50, available=True, price_min=10, price_max=100)
    assert not matches_item(node, text="Coffret", price=5, available=True, price_min=10, price_max=100)
    assert not matches_item(node, text="Coffret", price=150, available=True, price_min=10, price_max=100)


def test_matches_item_price_bound_with_unknown_price_fails():
    node = parse_filter('contient("coffret")')
    assert not matches_item(node, text="Coffret", price=None, available=True, price_min=10)
