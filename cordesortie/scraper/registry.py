from __future__ import annotations

from .adapter import SiteAdapter
from .adapters.auchan import AuchanAdapter
from .adapters.carrefour import CarrefourAdapter
from .adapters.joueclub import JoueClubAdapter
from .adapters.leclerc import LeclercAdapter

# Fnac n'a pas d'adapter : bloqué par un CAPTCHA Datadome dès la première requête,
# voir docs/SITES.md. Reste dans SUPPORTED_SITES (cordesortie/sites.py) mais ne
# renverra jamais d'item.
REGISTRY: dict[str, SiteAdapter] = {
    "carrefour": CarrefourAdapter(),
    "joueclub": JoueClubAdapter(),
    "leclerc": LeclercAdapter(),
    "auchan": AuchanAdapter(),
}
