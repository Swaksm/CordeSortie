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
