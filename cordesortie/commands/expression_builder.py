"""Construit une expression du moteur de filtres (cordesortie/filters/) à partir
de 3 listes de mots-clés en langage naturel.

Pont entre le formulaire interactif de `/filtre add` (modal Discord : 3 champs
texte, un mot par ligne, aucun guillemet/ET/OU/parenthèse à taper) et la
grammaire texte du moteur de filtres — voir cordesortie/filters/parser.py.
Ne couvre pas toute la grammaire (pas d'imbrication arbitraire) : c'est
volontaire, le formulaire vise le cas courant, pas l'expressivité complète
(toujours disponible via `/filtre test` et `/filtre edit` en texte libre).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..filters import And, Contains, FilterSyntaxError, Not, Or, parse_filter


class ExpressionBuilderError(Exception):
    """Aucun mot-clé exploitable fourni dans les champs du formulaire."""


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _quote(word: str) -> str:
    # Retire les guillemets éventuels plutôt que d'échapper : la grammaire ne
    # supporte pas les guillemets échappés à l'intérieur d'une chaîne, et un
    # mot-clé de recherche n'a de toute façon aucune raison d'en contenir.
    return f'"{word.replace(chr(34), "")}"'


def build_expression(*, must_all: str, any_of: str, exclude: str) -> str:
    """`must_all` : mots qui doivent TOUS apparaître (ET entre eux).
    `any_of` : au moins UN de ces mots doit apparaître (OU entre eux), optionnel.
    `exclude` : aucun de ces mots ne doit apparaître (NON ... ET), optionnel.

    Lève `ExpressionBuilderError` si ni `must_all` ni `any_of` ne fournissent de
    mot-clé (un filtre qui ne fait qu'exclure des mots matcherait tout, ce n'est
    presque sûrement pas l'intention).
    """
    must_terms = [_quote(w) for w in _lines(must_all)]
    any_terms = [_quote(w) for w in _lines(any_of)]
    exclude_terms = [_quote(w) for w in _lines(exclude)]

    if not must_terms and not any_terms:
        raise ExpressionBuilderError(
            "Renseigne au moins un mot dans « Doit contenir TOUS ces mots » ou "
            "« Au moins un de ces mots »."
        )

    parts = list(must_terms)
    if any_terms:
        any_group = any_terms[0] if len(any_terms) == 1 else "(" + " OU ".join(any_terms) + ")"
        parts.append(any_group)
    parts.extend(f"NON {term}" for term in exclude_terms)

    return " ET ".join(parts)


@dataclass(frozen=True, slots=True)
class DecomposedExpression:
    """Les 3 champs du formulaire, chacun prêt à être réaffiché tel quel (un
    mot par ligne) — voir `decompose_expression`."""

    must_all: str
    any_of: str
    exclude: str


def decompose_expression(expression: str) -> DecomposedExpression | None:
    """Tente de retrouver les 3 listes de mots-clés (must_all/any_of/exclude) à
    partir d'une expression texte, pour pré-remplir le formulaire de
    `/filtre edit` avec les conditions actuelles du profil plutôt que de
    partir d'un formulaire vide.

    Ne fonctionne que si l'expression a exactement la forme produite par
    `build_expression()` (un ET de mots simples, au plus un OU groupé de mots,
    des NON de mots simples) — une expression plus complexe (imbrication
    arbitraire) ne peut pas être redécomposée fidèlement dans ces 3 champs.
    Retourne `None` dans ce cas plutôt que de risquer de reconstruire un
    filtre différent de l'original ; le formulaire s'ouvre alors vide.
    """
    try:
        node = parse_filter(expression)
    except FilterSyntaxError:
        return None

    terms = node.children if isinstance(node, And) else (node,)

    must_all: list[str] = []
    any_of: list[str] = []
    exclude: list[str] = []
    any_of_seen = False

    for term in terms:
        if isinstance(term, Contains):
            must_all.append(term.text)
        elif isinstance(term, Not) and isinstance(term.child, Contains):
            exclude.append(term.child.text)
        elif isinstance(term, Or):
            if any_of_seen or not all(isinstance(child, Contains) for child in term.children):
                return None
            any_of_seen = True
            any_of.extend(child.text for child in term.children)
        else:
            return None

    return DecomposedExpression(
        must_all="\n".join(must_all),
        any_of="\n".join(any_of),
        exclude="\n".join(exclude),
    )
