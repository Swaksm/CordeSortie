# Tâches — CordeSortie

Cocher au fur et à mesure. Garder ce fichier synchronisé avec l'état réel du code —
c'est la référence pour savoir où on en est, pas la conversation.

## Phase 0 — Setup projet

- [x] Cadrage (PRD, architecture, liste de sites) — `docs/`
- [x] Init git
- [x] Squelette Python (`requirements.txt`, structure de dossiers)
- [x] `.env.example` (token Discord, chemins config)
- [ ] CI minimale (lint + un test qui importe le package) — optionnel mais utile tôt

## Phase 1 — Bot Discord de base

- [x] Connexion bot, enregistrement des slash commands (squelette vide)
- [x] Commande `/config set-channel <role: config|alerte|log> <#salon>`
- [x] Persistance de la config de base (channels) dans `data/<guild_id>/config.json`
- [x] Commande `/config show` (affiche la config actuelle dans le salon config)

## Phase 2 — Stockage

- [x] Schéma SQLite (`seen_items`, `scrape_runs`)
- [x] Migration/init DB au démarrage
- [x] Fonctions de dédup (clé stable par item)

## Phase 3 — Moteur de filtres

- [x] Grammaire de filtre : `contient`, `ET`, `OU`, `NON`, parenthèses
- [x] Parser + évaluateur, avec tests unitaires sur des cas ambigus
- [x] Support `prix_min` / `prix_max` / `only_available`
- [x] Commandes `/filtre add`, `/filtre list`, `/filtre remove`, `/filtre test <texte>`
      (mode dry-run pour valider un filtre sur un item fictif)
- [x] Salon d'alerte dédié auto-créé par profil (`<pseudo>-<nom du filtre>`, regroupés
      dans une catégorie "Alertes" — séparée de "CordeSortie" qui ne contient que les
      salons de pilotage du bot), supprimé automatiquement avec le profil
- [x] Salon "cordesortie-aide" (hors plan initial) : documentation des commandes
      générée depuis les commandes réellement enregistrées (`bot.tree.walk_commands`),
      pas un texte maintenu à la main — régénérée à chaque connexion, découpée en
      plusieurs messages épinglés si ça dépasse la limite Discord (jamais tronquée)
- [x] Commande `/sites` (hors plan initial) : liste les sites supportés et leur statut
      réel (dérivé de `REGISTRY`, pas d'une doc à maintenir à part)

## Phase 4 — Scraper engine

- [x] Interface `SiteAdapter` + registre de sites disponibles
- [x] Setup Playwright (contexte navigateur partagé, gestion cookies)
- [x] Premier adapter (Carrefour) — testé en direct sur le site, 30 items, prix
      et titres corrects
- [x] Normalisation `Item` (titre, prix, dispo, url, image)
- [x] Adapter JouéClub (hors plan initial, ajouté car dispo web fiable) — testé en
      direct, 26 items dont 6 correctement détectés indisponibles
- [x] Commande `/filtre dry-run` (hors plan initial) : scrape en direct les sites
      d'un profil et applique le moteur de filtres dessus, sans alerter ni toucher
      à la dédup — pont manuel entre scraper et filtres en attendant le scheduler
      (Phase 5). Testé bout en bout : 30 matchs corrects sur carrefour + joueclub.
- [x] Adapter Leclerc — testé en direct, 42 items, prix corrects (pas de vraie
      détection de rupture, comme Carrefour)
- [x] Adapter Auchan — testé en direct, 30 items, 17 dispo/13 rupture correctement
      détectés via microdonnées schema.org (`meta[itemprop=availability]`)
- [x] ~~Adapter Fnac~~ **abandonné** : bloqué par un CAPTCHA Datadome dès la
      première requête (voir docs/SITES.md) — pas d'adapter, contourner un CAPTCHA
      n'est pas fait ici

## Phase 5 — Scheduler & anti-détection

- [x] Boucle asyncio par (serveur, site) — `SchedulerManager`, une tâche par site
      actif, recalculées à chaque `/filtre add|remove` (pas de polling périodique)
- [x] Plancher dur 60s codé en dur (`_HARD_FLOOR_SECONDS`, indépendant de la config)
- [x] Jitter sur l'intervalle de scrape (±15%) et sur le log
- [x] Backoff exponentiel + jitter sur erreurs/blocages détectés (jusqu'à 60 min max)
- [x] Intervalle configurable par profil via `/filtre add interval_minutes` (pas de
      commande séparée `/config set-interval` — le profil suffit, cf. décision
      ARCHITECTURE.md §5)
- [x] Détection explicite de page de challenge/captcha (`BlockedError`, domaines
      Datadome/hCaptcha/Cloudflare connus) → log + backoff du site concerné
- [x] Testé en direct : scheduler tourne, scrape 4 sites/minute, `scrape_runs`
      correctement peuplée

## Phase 6 — Alertes & log

- [x] Notifier : embed Discord pour chaque item matché, envoyé dans le salon d'alerte
      dédié du profil (`profile.alert_channel_id`)
- [x] Anti-doublon scopé par profil (`alert_channel_id`), pas juste par site — deux
      profils qui matchent le même item sont notifiés indépendamment (voir
      `tests/test_storage.py`)
- [x] Notification si prix change ou item redevient disponible
- [x] Flux d'évènements en direct dans le salon log (hors plan initial, demandé en
      plus du résumé périodique) : création/suppression de filtre, résultat concis
      de chaque cycle de scrape (`log_event()` dans `notifier.py`)
- [x] Log périodique (salon log), intervalle configurable indépendamment du scrape
      (`config.log_interval_minutes`)
- [x] Gestion des erreurs remontées dans le log (site down, adapter cassé, blocage)
- [x] Commande `/pause` + `/resume` : coupe/reprend immédiatement tout scraping
- [x] Testé en direct sur Discord : alerte reçue pour un filtre large
      (`contient("pokemon")`), confirmée que la dédup empêche le spam au cycle
      suivant

## Phase 7 — Durcissement / qualité

- [ ] Tests sur le moteur de filtres (cas AND/OR/NOT imbriqués)
- [ ] Tests sur le scheduler (jitter respecte le plancher, backoff fonctionne)
- [ ] Gestion propre de l'arrêt (SIGINT/SIGTERM) — fermer proprement Playwright
- [ ] Revue anti-détection avant mise en prod longue durée (voir RISKS.md)
- [ ] Documentation utilisateur finale (README : comment inviter le bot, premiers pas)

## Phase 8 — Déploiement Render

- [x] `Dockerfile` (build + import testés en local avec Docker)
- [x] Repo GitHub créé et code poussé (nécessaire pour connecter Render)
- [x] `playwright install --with-deps chromium` dans le Dockerfile, scraper Carrefour
      testé et fonctionnel à l'intérieur du conteneur
- [ ] Service Render "Background Worker" créé, connecté au repo
- [ ] `DISCORD_TOKEN` configuré en variable d'environnement Render (jamais commité)
- [ ] Render Disk monté sur `/data` (doit matcher `DATA_DIR=/data` du Dockerfile)

## Backlog / v2 (hors MVP)

- [ ] Multi-serveur Discord avec configs isolées
- [ ] Intervalle de scrape par site (plutôt que global)
- [ ] Interface web de configuration
- [ ] Historique/statistiques consultables via commande (`/stats`)
- [ ] Salon d'alerte par profil en privé (visible uniquement par le créateur du
      filtre + les admins) au lieu de visible par tout le serveur
