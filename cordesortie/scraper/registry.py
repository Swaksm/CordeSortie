from __future__ import annotations

from .adapter import SiteAdapter
from .adapters.auchan import AuchanAdapter
from .adapters.carrefour import CarrefourAdapter
from .adapters.cultura import CulturaAdapter
from .adapters.joueclub import JoueClubAdapter
from .adapters.leclerc import LeclercAdapter

# Fnac et King Jouet n'ont pas d'adapter : bloqués par un CAPTCHA Datadome dès
# la première requête, voir docs/SITES.md. Restent dans SUPPORTED_SITES
# (cordesortie/sites.py) mais ne renverront jamais d'item.
REGISTRY: dict[str, SiteAdapter] = {
    "carrefour": CarrefourAdapter(),
    "joueclub": JoueClubAdapter(),
    "leclerc": LeclercAdapter(),
    "auchan": AuchanAdapter(),
    "cultura": CulturaAdapter(),
}
