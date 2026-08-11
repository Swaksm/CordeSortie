"""Combine le résultat de la grammaire de filtre avec les critères additionnels
(prix min/max, disponibilité) — voir docs/PRD.md §3.1."""

from __future__ import annotations

from .ast_nodes import Node
from .evaluator import evaluate


def matches_item(
    node: Node,
    *,
    text: str,
    price: float | None,
    available: bool,
    price_min: float | None = None,
    price_max: float | None = None,
    only_available: bool = True,
) -> bool:
    if only_available and not available:
        return False
    if price_min is not None and (price is None or price < price_min):
        return False
    if price_max is not None and (price is None or price > price_max):
        return False
    return evaluate(node, text=text)
