"""Parser récursif descendant pour la grammaire de filtre.

Grammaire :
    expr   := atom ((ET atom)* | (OU atom)*)      -- pas de mélange ET/OU sans parenthèses
    atom   := NON atom | "(" expr ")" | STRING | CONTAINS "(" STRING ")"

Une chaîne entre guillemets toute seule ("pokemon") est un raccourci pour
contient("pokemon") — les deux syntaxes sont équivalentes et interchangeables,
contient(...) reste supporté pour ne pas casser les profils existants. Ça permet
d'écrire des filtres bien plus courts, ex. ("30 ans" OU "30 years") ET "coffret"
au lieu de (contient("30 ans") OU contient("30 years")) ET contient("coffret").

Mélanger ET et OU au même niveau sans parenthèses est une erreur explicite plutôt
qu'une priorité devinée — voir docs/RISKS.md §3.
"""

from __future__ import annotations

from .ast_nodes import And, Contains, Node, Not, Or
from .errors import FilterSyntaxError
from .tokenizer import Token, tokenize


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _expect(self, kind: str) -> Token:
        token = self._peek()
        if token is None or token[0] != kind:
            got = f"{token[0]} {token[1]!r}" if token else "fin de l'expression"
            raise FilterSyntaxError(f"Attendu {kind}, obtenu {got}")
        return self._advance()

    def parse(self) -> Node:
        node = self._parse_expr()
        if self._peek() is not None:
            kind, value = self._peek()  # type: ignore[misc]
            raise FilterSyntaxError(f"Token inattendu après la fin de l'expression : {value!r}")
        return node

    def _parse_expr(self) -> Node:
        terms = [self._parse_atom()]
        op: str | None = None

        while True:
            token = self._peek()
            if token is None or token[0] not in ("AND", "OR"):
                break
            if op is None:
                op = token[0]
            elif token[0] != op:
                raise FilterSyntaxError(
                    "Mélange de ET et OU sans parenthèses : ajoute des parenthèses pour "
                    'lever l\'ambiguïté, ex. (contient("a") ET contient("b")) OU contient("c").'
                )
            self._advance()
            terms.append(self._parse_atom())

        if op is None:
            return terms[0]
        return And(tuple(terms)) if op == "AND" else Or(tuple(terms))

    def _parse_atom(self) -> Node:
        token = self._peek()
        if token is None:
            raise FilterSyntaxError("Expression incomplète")

        kind, value = token

        if kind == "NOT":
            self._advance()
            return Not(self._parse_atom())

        if kind == "LPAREN":
            self._advance()
            node = self._parse_expr()
            self._expect("RPAREN")
            return node

        if kind == "STRING":
            self._advance()
            return Contains(value)

        if kind == "CONTAINS":
            self._advance()
            self._expect("LPAREN")
            text_token = self._expect("STRING")
            self._expect("RPAREN")
            return Contains(text_token[1])

        raise FilterSyntaxError(f"Token inattendu : {value!r}")


def parse_filter(text: str) -> Node:
    tokens = tokenize(text)
    if not tokens:
        raise FilterSyntaxError("Expression de filtre vide")
    return _Parser(tokens).parse()
