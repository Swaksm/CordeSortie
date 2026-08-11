"""Schéma de la configuration par serveur Discord.

Ce fichier JSON (un par serveur) est la source de vérité de la config — voir
docs/ARCHITECTURE.md.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from ..filters import FilterSyntaxError, parse_filter
from ..sites import SUPPORTED_SITES


class ChannelRole(str, Enum):
    CONFIG = "config"
    ALERTE = "alerte"
    LOG = "log"


class FilterProfile(BaseModel):
    name: str
    sites: list[str]
    filter_expression: str
    alert_channel_id: int
    price_min: float | None = None
    price_max: float | None = None
    only_available: bool = True

    @field_validator("filter_expression")
    @classmethod
    def _validate_expression(cls, value: str) -> str:
        try:
            parse_filter(value)
        except FilterSyntaxError as exc:
            raise ValueError(f"Expression de filtre invalide : {exc}") from exc
        return value

    @field_validator("sites")
    @classmethod
    def _validate_sites(cls, value: list[str]) -> list[str]:
        unknown = [site for site in value if site not in SUPPORTED_SITES]
        if unknown:
            raise ValueError(
                f"Site(s) inconnu(s) : {', '.join(unknown)}. "
                f"Sites supportés : {', '.join(SUPPORTED_SITES)}."
            )
        if not value:
            raise ValueError("Un profil doit cibler au moins un site.")
        return value


class GuildConfig(BaseModel):
    channels: dict[ChannelRole, int] = Field(default_factory=dict)
    log_interval_minutes: int = 15
    profiles: list[FilterProfile] = Field(default_factory=list)

    def channel_id(self, role: ChannelRole) -> int | None:
        return self.channels.get(role)

    def get_profile(self, name: str) -> FilterProfile | None:
        return next((p for p in self.profiles if p.name == name), None)
