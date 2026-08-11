from __future__ import annotations

from .ast_nodes import And, Contains, Node, Not, Or


def evaluate(node: Node, *, text: str) -> bool:
    """Évalue un AST de filtre contre un texte (titre + description, non normalisé)."""
    haystack = text.lower()

    if isinstance(node, Contains):
        return node.text.lower() in haystack
    if isinstance(node, Not):
        return not evaluate(node.child, text=text)
    if isinstance(node, And):
        return all(evaluate(child, text=text) for child in node.children)
    if isinstance(node, Or):
        return any(evaluate(child, text=text) for child in node.children)

    raise TypeError(f"Type de nœud AST inconnu : {node!r}")
