from __future__ import annotations

from .adapter import SiteAdapter
from .adapters.carrefour import CarrefourAdapter
from .adapters.joueclub import JoueClubAdapter

REGISTRY: dict[str, SiteAdapter] = {
    "carrefour": CarrefourAdapter(),
    "joueclub": JoueClubAdapter(),
}
