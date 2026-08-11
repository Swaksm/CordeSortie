"""Tokenizer pour la grammaire de filtre : contient("..."), ET, OU, NON, ( )."""

from __future__ import annotations

import re

from .errors import FilterSyntaxError

Token = tuple[str, str]  # (kind, value)

_KEYWORDS = {
    "contient": "CONTAINS",
    "et": "AND",
    "ou": "OR",
    "non": "NOT",
}

_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<STRING>"[^"]*")
      | (?P<LPAREN>\()
      | (?P<RPAREN>\))
      | (?P<WORD>[^\s()"]+)
    )
    """,
    re.VERBOSE,
)


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    length = len(text)

    while pos < length:
        if text[pos].isspace():
            pos += 1
            continue

        match = _TOKEN_RE.match(text, pos)
        if match is None or match.end() == pos:
            raise FilterSyntaxError(
                f"Caractère inattendu à la position {pos} : {text[pos]!r}"
            )

        kind = match.lastgroup
        value = match.group(kind)
        pos = match.end()

        if kind == "STRING":
            tokens.append(("STRING", value[1:-1]))
        elif kind == "LPAREN":
            tokens.append(("LPAREN", value))
        elif kind == "RPAREN":
            tokens.append(("RPAREN", value))
        elif kind == "WORD":
            keyword = _KEYWORDS.get(value.lower())
            if keyword is None:
                raise FilterSyntaxError(
                    f"Mot-clé inconnu : {value!r} "
                    '(attendu : contient, ET, OU, NON, ou une expression entre parenthèses)'
                )
            tokens.append((keyword, value))

    return tokens
