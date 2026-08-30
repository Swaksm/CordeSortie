from __future__ import annotations

from .adapter import SiteAdapter
from .adapters.auchan import AuchanAdapter
from .adapters.carrefour import CarrefourAdapter
from .adapters.cultura import CulturaAdapter
from .adapters.dracaustore import DracaustoreAdapter
from .adapters.joueclub import JoueClubAdapter
from .adapters.latavernededream import LaTaverneDeDreamAdapter
from .adapters.leclerc import LeclercAdapter
from .adapters.ludifolie import LudifolieAdapter
from .adapters.micromania import MicromaniaAdapter

# Fnac, King Jouet et Outpost Brussels n'ont pas d'adapter : bloqués par un
# antibot (CAPTCHA Datadome / Cloudflare) dès la première requête, voir
# docs/SITES.md. Restent dans SUPPORTED_SITES (cordesortie/sites.py) mais ne
# renverront jamais d'item.
#
# Comptoir des Écoliers et Philibert ont un adapter écrit (adapters/) mais
# volontairement absents d'ici :
# - Comptoir des Écoliers recharge la page en plein milieu du scrape de façon
#   reproductible (2/2 essais), ce qui fait planter page.close() après coup.
# - Philibert : le moteur de recherche (widget Doofinder) se re-render de
#   façon imprévisible pendant la frappe automatisée, tronquant la requête
#   différemment à chaque essai (3/3 tentatives ratées, résultats jamais
#   filtrés sur la bonne requête).
# Ni l'un ni l'autre n'est un antibot dur, mais tous les deux trop instables
# pour mériter leur place dans les cycles de scrape réguliers. Voir
# docs/SITES.md.
REGISTRY: dict[str, SiteAdapter] = {
    "carrefour": CarrefourAdapter(),
    "joueclub": JoueClubAdapter(),
    "leclerc": LeclercAdapter(),
    "auchan": AuchanAdapter(),
    "cultura": CulturaAdapter(),
    "ludifolie": LudifolieAdapter(),
    "micromania": MicromaniaAdapter(),
    "latavernededream": LaTaverneDeDreamAdapter(),
    "dracaustore": DracaustoreAdapter(),
}
