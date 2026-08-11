"""Schéma de la configuration par serveur Discord.

Ce fichier JSON (un par serveur) est la source de vérité de la config — voir
docs/ARCHITECTURE.md.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from ..filters import FilterSyntaxError, parse_filter
from ..sites import SUPPORTED_SITES

# Plancher dur, non contournable via la config — voir docs/PRD.md §3.4 et
# docs/RISKS.md (anti-détection).
MIN_SCRAPE_INTERVAL_MINUTES = 1
DEFAULT_SCRAPE_INTERVAL_MINUTES = 5


class ChannelRole(str, Enum):
    CONFIG = "config"
    ALERTE = "alerte"
    LOG = "log"


class FilterProfile(BaseModel):
    name: str
    sites: list[str]
    filter_expression: str
    alert_channel_id: int
    scrape_interval_minutes: int = DEFAULT_SCRAPE_INTERVAL_MINUTES
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

    @field_validator("scrape_interval_minutes")
    @classmethod
    def _validate_interval(cls, value: int) -> int:
        if value < MIN_SCRAPE_INTERVAL_MINUTES:
            raise ValueError(
                f"Intervalle de scrape trop court ({value} min) : minimum "
                f"{MIN_SCRAPE_INTERVAL_MINUTES} min pour ne pas se faire bloquer "
                "par les antibots."
            )
        return value


class GuildConfig(BaseModel):
    channels: dict[ChannelRole, int] = Field(default_factory=dict)
    log_interval_minutes: int = 15
    profiles: list[FilterProfile] = Field(default_factory=list)
    info_channel_id: int | None = None
    info_message_id: int | None = None

    def channel_id(self, role: ChannelRole) -> int | None:
        return self.channels.get(role)

    def get_profile(self, name: str) -> FilterProfile | None:
        return next((p for p in self.profiles if p.name == name), None)
