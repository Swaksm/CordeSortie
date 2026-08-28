import pytest

from cordesortie.commands.expression_builder import (
    ExpressionBuilderError,
    build_expression,
    decompose_expression,
)
from cordesortie.filters import matches_item, parse_filter


def test_must_all_only():
    expr = build_expression(must_all="pokemon", any_of="", exclude="")
    assert expr == '"pokemon"'


def test_must_all_multiple_lines_joined_with_and():
    expr = build_expression(must_all="pokemon\ncoffret", any_of="", exclude="")
    assert expr == '"pokemon" ET "coffret"'


def test_any_of_grouped_with_or_and_parens():
    expr = build_expression(must_all="", any_of="30 ans\n30 years", exclude="")
    assert expr == '("30 ans" OU "30 years")'


def test_single_any_of_not_wrapped_in_parens():
    expr = build_expression(must_all="", any_of="30 ans", exclude="")
    assert expr == '"30 ans"'


def test_exclude_becomes_not_anded_in():
    expr = build_expression(must_all="pokemon", any_of="", exclude="peluche")
    assert expr == '"pokemon" ET NON "peluche"'


def test_full_combination_matches_expected_grammar():
    expr = build_expression(must_all="pokemon", any_of="30 ans\n30 years", exclude="peluche")
    assert expr == '"pokemon" ET ("30 ans" OU "30 years") ET NON "peluche"'

    node = parse_filter(expr)
    assert matches_item(node, text="Pokemon coffret 30 ans", price=10, available=True)
    assert matches_item(node, text="Pokemon coffret 30 years", price=10, available=True)
    assert not matches_item(node, text="Pokemon coffret", price=10, available=True)
    assert not matches_item(
        node, text="Pokemon peluche 30 ans", price=10, available=True
    )


def test_blank_lines_and_surrounding_whitespace_ignored():
    expr = build_expression(must_all="  pokemon  \n\n  ", any_of="", exclude="")
    assert expr == '"pokemon"'


def test_quotes_in_input_are_stripped_not_escaped():
    expr = build_expression(must_all='po"kemon', any_of="", exclude="")
    assert expr == '"pokemon"'


def test_raises_when_no_required_keyword_given():
    with pytest.raises(ExpressionBuilderError):
        build_expression(must_all="", any_of="", exclude="peluche")

    with pytest.raises(ExpressionBuilderError):
        build_expression(must_all="", any_of="", exclude="")


def test_decompose_is_the_inverse_of_build_for_full_combination():
    expr = build_expression(must_all="pokemon", any_of="30 ans\n30 years", exclude="peluche")

    result = decompose_expression(expr)

    assert result is not None
    assert result.must_all == "pokemon"
    assert result.any_of == "30 ans\n30 years"
    assert result.exclude == "peluche"


def test_decompose_must_all_only():
    result = decompose_expression('"pokemon" ET "coffret"')
    assert result is not None
    assert result.must_all == "pokemon\ncoffret"
    assert result.any_of == ""
    assert result.exclude == ""


def test_decompose_any_of_only_single_term():
    result = decompose_expression('"pokemon"')
    assert result is not None
    assert result.must_all == "pokemon"


def test_decompose_bare_or_group():
    result = decompose_expression('("30 ans" OU "30 years")')
    assert result is not None
    assert result.must_all == ""
    assert result.any_of == "30 ans\n30 years"


def test_decompose_round_trips_through_build_expression_again():
    original = build_expression(
        must_all="pokemon\ncoffret",
        any_of="30 ans\n30 years",
        exclude="peluche\nfigurine",
    )
    decomposed = decompose_expression(original)
    assert decomposed is not None

    rebuilt = build_expression(
        must_all=decomposed.must_all, any_of=decomposed.any_of, exclude=decomposed.exclude
    )
    assert rebuilt == original


def test_decompose_returns_none_for_expressions_it_cannot_represent():
    # Melange ET/OU imbrique que le formulaire ne sait pas representer.
    assert decompose_expression('("pokemon" ET "coffret") OU "promo"') is None
    # Grammaire invalide.
    assert decompose_expression('contient(') is None
