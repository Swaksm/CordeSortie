# Architecture — CordeSortie

## 1. Vue d'ensemble

```
                         ┌───────────────────────┐
                         │        Discord         │
                         │  #config  #alerte  #log │
                         └───────────┬─────────────┘
                                     │ discord.py (slash commands + messages)
                          ┌──────────┴───────────┐
                          │      Bot process      │
                          │  (asyncio event loop)  │
                          └──────────┬───────────┘
              ┌───────────────┬──────┴───────┬───────────────┐
              │               │              │               │
        ┌─────▼─────┐  ┌──────▼──────┐ ┌─────▼─────┐  ┌──────▼──────┐
        │ Config     │  │ Scheduler   │ │ Filter     │  │ Notifier    │
        │ store      │  │ (jitter,    │ │ engine     │  │ (alerte +   │
        │ (JSON+DB)  │  │ rate limit) │ │            │  │  log)       │
        └─────┬──────┘  └──────┬──────┘ └─────▲──────┘  └─────────────┘
              │                │               │
              │         ┌──────▼──────┐        │
              │         │  Scraper    │────────┘
              │         │  engine     │  Items normalisés
              │         └──────┬──────┘
              │        ┌───────┴────────┐
              │  ┌──────▼─────┐  ┌───────▼──────┐
              │  │ adapters/  │  │ adapters/    │  ...
              │  │ auchan.py  │  │ leclerc.py   │
              │  └────────────┘  └──────────────┘
              │
        ┌─────▼──────┐
        │  SQLite     │  historique items vus, config persistée
        └────────────┘
```

## 2. Composants

### 2.1 Bot Discord (`bot/`)
- `discord.py`, slash commands uniquement (`/filtre add`, `/filtre list`,
  `/filtre remove`, `/site list`, `/config set-interval`, `/config set-channel`).
- Chaque commande lit/écrit le **config store**, jamais directement la DB brute.

### 2.2 Config store (`config/`)
- Fichier JSON lisible par serveur Discord (`data/<guild_id>/config.json`), c'est la
  **source de vérité** pour les profils de filtre, sites actifs, salons assignés,
  intervalle de scrape.
- Les commandes Discord sont une couche d'édition au-dessus ; un utilisateur avancé
  peut éditer le fichier à la main et redémarrer/recharger.
- Validation stricte au chargement (schéma) pour éviter qu'une édition manuelle casse
  le bot silencieusement.

### 2.3 Scheduler (`scheduler.py`)
- Une tâche asyncio par site actif (union de tous les sites utilisés par tous les
  profils).
- Calcule le prochain délai : `base_interval * random.uniform(0.9, 1.1)` (ou
  équivalent additif ± quelques secondes), avec un **plancher dur codé en dur à 60s**
  quel que soit ce que la config demande.
- Un site en erreur répétée (ex: 3 échecs consécutifs) passe en *backoff* et reporte
  dans le salon log au lieu de retry en boucle serrée.

### 2.4 Scraper engine (`scraper/`)
- Playwright (Chromium headless) pour **tous** les sites, sans exception ni fallback
  HTTP — priorité donnée à la robustesse anti-détection sur la légèreté (hébergement
  payant assumé, voir §6).
- Réutilisation d'un contexte de navigateur persistant (cookies, éventuel fingerprint
  stable) entre cycles plutôt que de relancer un navigateur à chaque scrape — ça reste
  la principale optimisation à ne pas sauter, indépendamment du budget disponible.
- Interface commune par adapter :
  ```python
  class SiteAdapter(Protocol):
      name: str
      async def fetch_items(self, page: playwright.Page) -> list[Item]: ...
  ```
- `Item` normalisé : `{site, title, description, price, currency, available, url, image_url}`.
- Chaque adapter encapsule : l'URL/la recherche à interroger, le parsing DOM, la
  détection "en stock"/"rupture" propre au site.

### 2.5 Filter engine (`filters/`)
- Ne connaît rien aux sites. Entrée : liste d'`Item` + expression de filtre.
- Grammaire minimale à supporter :
  `contient "texte"`, `ET`, `OU`, `NON`, parenthèses, `prix >= X`, `prix <= X`.
- Parser simple (récursif descendant) plutôt qu'une dépendance externe — reste dans
  l'esprit "léger".

### 2.6 Notifier (`notifier.py`)
- Alerte : un embed Discord par item matché (titre, prix, site, lien, image si dispo).
- Log périodique : agrégation des compteurs depuis le dernier envoi, à l'intervalle
  configuré (indépendant de l'intervalle de scrape).

### 2.7 Stockage (`storage/`, SQLite)
Tables minimales :
- `seen_items(site, item_key, title, price, available, first_seen_at, last_seen_at)`
  — `item_key` = hash stable (site + url ou id produit) pour la dédup.
- `filter_profiles(...)` — persistance miroir du config JSON si besoin de requêtage,
  ou simplement le JSON fait foi et la DB ne sert qu'à l'historique des items.
- `scrape_runs(site, started_at, finished_at, items_found, matched, error)` — alimente
  le salon log.

## 3. Anti-détection

Contraintes non négociables :
- **Jamais < 60s** entre deux scrapes d'un même site, imposé au niveau code (pas
  seulement documenté).
- **Jitter obligatoire** sur tous les délais (scrape ET log), jamais un cron figé.
- **User-Agent et headers réalistes**, réutilisation de contexte/cookies pour ne pas
  réapparaître comme "nouvelle session" à chaque cycle.
- **Rate limiting centralisé** : un seul point du code déclenche les requêtes réseau
  par site, pour garantir qu'aucun adapter ne peut accidentellement scraper plus vite
  que prévu.
- **Backoff exponentiel avec jitter** en cas d'erreur/blocage détecté (429, captcha,
  page de challenge) plutôt que retry immédiat.
- Voir aussi [RISKS.md](RISKS.md) pour les limites légales de cette approche.

## 4. Config (exemple simplifié)

```json
{
  "channels": { "config": "123", "alerte": "456", "log": "789" },
  "log_interval_minutes": 15,
  "profiles": [
    {
      "name": "coffrets-30ans",
      "sites": ["auchan", "leclerc"],
      "filter": "contient(\"30 ans\") ET contient(\"coffret\")",
      "price_max": 80,
      "only_available": true,
      "scrape_interval_minutes": 5
    }
  ]
}
```

## 5. Points ouverts à trancher en implémentation

- Faut-il un intervalle de scrape par site ou par profil ? (impacte le scheduler)
- Réutiliser un seul navigateur Playwright partagé entre sites, ou un par site pour
  isoler les cookies/fingerprints ?
- Format exact de la grammaire de filtre (texte libre à parser vs commandes Discord
  structurées type builder) — voir discussion UX dans [RISKS.md](RISKS.md).

## 6. Hébergement (Railway / Render)

- Déploiement prévu sur Railway ou Render, plan payant si nécessaire pour tenir la
  charge Playwright — voir [RISKS.md](RISKS.md) §2 pour les compromis CPU/RAM.
- **Dockerfile recommandé** plutôt qu'un buildpack natif, pour maîtriser précisément
  l'installation des dépendances système de Chromium
  (`playwright install --with-deps chromium`) — c'est le point de friction le plus
  courant sur ces plateformes.
- **Filesystem éphémère** : Railway/Render ne garantissent pas la persistance du disque
  entre redeploys sur les plans standards. La config JSON par serveur et la DB SQLite
  (dédup des items vus) doivent vivre sur un **volume persistant** explicitement monté
  (Railway Volumes / Render Disks), sinon un redeploy efface l'historique et la config.
- Variables sensibles (token Discord) via les variables d'environnement de la
  plateforme, jamais commitées — cohérent avec `.env` gitignoré en local.
