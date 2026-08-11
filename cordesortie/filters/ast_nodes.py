from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Contains:
    text: str


@dataclass(frozen=True, slots=True)
class Not:
    child: Node


@dataclass(frozen=True, slots=True)
class And:
    children: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class Or:
    children: tuple[Node, ...]


Node = Contains | Not | And | Or
