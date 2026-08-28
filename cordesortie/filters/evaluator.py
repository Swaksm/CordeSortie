from __future__ import annotations

import unicodedata

from .ast_nodes import And, Contains, Node, Not, Or


def _normalize(text: str) -> str:
    """Minuscules + accents retirés, pour que "pokemon" matche "Pokémon" et
    inversement — les sites marchands orthographient ça de façon incohérente."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def evaluate(node: Node, *, text: str) -> bool:
    """Évalue un AST de filtre contre un texte (titre + description, non normalisé)."""
    haystack = _normalize(text)

    if isinstance(node, Contains):
        return _normalize(node.text) in haystack
    if isinstance(node, Not):
        return not evaluate(node.child, text=text)
    if isinstance(node, And):
        return all(evaluate(child, text=text) for child in node.children)
    if isinstance(node, Or):
        return any(evaluate(child, text=text) for child in node.children)

    raise TypeError(f"Type de nœud AST inconnu : {node!r}")
